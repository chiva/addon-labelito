#!/usr/bin/env python3
"""Translate the add-on's /data/options.json into labelito's environment.

Runs before uvicorn (see run.sh) and writes KEY='value' lines to a sourceable env file.
It also talks to the Supervisor API — best-effort, except where noted:

- Port-exposure guard: if the user mapped the host port but set no api_token, refuse to
  start — labelito would otherwise run ALLOW_UNAUTHENTICATED on the LAN. Fatal only when
  the Supervisor confirms the port is mapped; an unreachable API never blocks startup.
- Discovery: announce {host, port, api_token} so the ha-labelito integration can offer
  one-click setup.

labelito's in-app update check is forced off: the Supervisor (and Renovate on this repo)
owns add-on updates, so an About-modal "update available" pointing at upstream GitHub
releases would be misleading here.

The ADDON_*/SUPERVISOR_URL env overrides exist for the test harness only; under the
Supervisor the defaults are always correct.
"""

import json
import os
import shlex
import sys
import urllib.error
import urllib.request
from pathlib import Path

OPTIONS_PATH = Path(os.environ.get("ADDON_OPTIONS_JSON", "/data/options.json"))
ENV_FILE = Path(os.environ.get("ADDON_ENV_FILE", "/tmp/labelito.env"))
SUPERVISOR_URL = os.environ.get("SUPERVISOR_URL", "http://supervisor")
LABELITO_PORT = 8765
DISCOVERY_SERVICE = "labelito"
HTTP_TIMEOUT_S = 10


def log(message: str) -> None:
    print(f"[labelito-addon] {message}", flush=True)


def supervisor_call(path: str, payload: dict | None = None) -> dict | None:
    """GET (payload None) or POST a Supervisor endpoint; returns None on any failure."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return None
    request = urllib.request.Request(
        f"{SUPERVISOR_URL}{path}",
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        log(f"Supervisor call {path} failed: {exc}")
        return None


def main() -> None:
    options = json.loads(OPTIONS_PATH.read_text())
    api_token = (options.get("api_token") or "").strip()
    editor_enabled = "true" if options.get("editor_enabled") else "false"

    # The schema guarantees positive ints but cannot express the cross-field invariant:
    # pruning trims back to keep_entries, so a prune threshold at or below it would never
    # reduce the history. Reject it here with a clear error rather than forward a config
    # that silently never prunes.
    keep_entries = options.get("history_keep_entries", 1000)
    prune_at_entries = options.get("history_prune_at_entries", 1500)
    if prune_at_entries <= keep_entries:
        log(
            f"FATAL: history_prune_at_entries ({prune_at_entries}) must be greater than "
            f"history_keep_entries ({keep_entries}) — pruning trims back to keep_entries, so "
            "a threshold at or below it would never shrink the history. Adjust the add-on "
            "configuration."
        )
        sys.exit(1)

    env = {
        "MODEL": options["model"],
        "PRINTER_URI": options["printer_uri"],
        "DEFAULT_LANGUAGE": options.get("default_language", "en"),
        # One switch drives both upstream flags: in the add-on the template directory is
        # always writable (/config), so an editor without server-save would just confuse.
        "EDITOR_ENABLED": editor_enabled,
        "TEMPLATES_WRITABLE": editor_enabled,
        "LOG_LEVEL": options.get("log_level", "info"),
        # Bound the durable print-history DB (defaults match upstream and config.yaml).
        "HISTORY_KEEP_ENTRIES": keep_entries,
        "HISTORY_PRUNE_AT_ENTRIES": prune_at_entries,
        # Fixed add-on wiring, not user options: the ingress prefix header, durable history
        # in the Supervisor-managed /data, and user templates in the addon-config mount.
        "PROXY_PATH_HEADER": "X-Ingress-Path",
        "HISTORY_MODE": "file",
        "DATA_DIR": "/data",
        "TEMPLATES_DIR": "/config/templates",
        # The Supervisor/Renovate owns add-on updates — silence labelito's in-app update check.
        "UPDATE_CHECK_ENABLED": "false",
    }
    if api_token:
        env["API_TOKEN"] = api_token
    else:
        # Safe for ingress-only use: HA authenticates ingress, the host port is closed by
        # default, and the guard below blocks the port-open-without-token combination.
        env["ALLOW_UNAUTHENTICATED"] = "true"

    info_response = supervisor_call("/addons/self/info")
    if info_response is None:
        log("Supervisor API unavailable — skipping the port guard and discovery")
    else:
        info = info_response.get("data", {})
        host_port = (info.get("network") or {}).get(f"{LABELITO_PORT}/tcp")
        if host_port and not api_token:
            log(
                f"FATAL: host port {host_port} is mapped but no api_token is set. Ingress "
                "requests are authenticated by Home Assistant, but the direct port would "
                "accept anyone on your network. Set an api_token in the add-on "
                "configuration, or disable the port mapping."
            )
            sys.exit(1)
        discovery = supervisor_call(
            "/discovery",
            {
                "service": DISCOVERY_SERVICE,
                "config": {
                    "host": info.get("hostname"),
                    "port": LABELITO_PORT,
                    "api_token": api_token,
                },
            },
        )
        log("discovery announced" if discovery else "discovery announcement failed (non-fatal)")

    ENV_FILE.write_text("".join(f"{key}={shlex.quote(str(value))}\n" for key, value in env.items()))
    ENV_FILE.chmod(0o600)
    log(f"environment prepared for model {env['MODEL']} at {env['PRINTER_URI']}")


if __name__ == "__main__":
    main()
