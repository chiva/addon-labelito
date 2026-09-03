"""Fixtures for the add-on entrypoint tests.

addon_init reads OPTIONS_PATH / ENV_FILE / SUPERVISOR_URL from the environment at import time,
so every test redirects them by patching the module attributes rather than the environment: the
module is imported once per session and re-importing it to pick up new env would be fragile.
"""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path
from typing import Any

import addon_init
import pytest

# Mirrors labelito/config.yaml's `options:` block — the defaults the Supervisor hands over when
# the user has changed nothing. Tests override single keys so a failure names the option at fault.
DEFAULT_OPTIONS: dict[str, Any] = {
    "model": "QL-810W",
    "printer_uri": "tcp://192.168.1.100:9100",
    "editor_enabled": False,
    "editor_default_mode": "visual",
    "inline_templates_enabled": False,
    "mcp_enabled": False,
    "mcp_writable": False,
    "default_language": "en",
    "log_level": "info",
    "history_keep_entries": 1000,
    "history_prune_at_entries": 1500,
}

HOSTNAME = "homeassistant"
SELF_INFO_PATH = "/addons/self/info"
DISCOVERY_PATH = "/discovery"


class FakeSupervisor:
    """Stands in for urllib at the socket boundary, so the real supervisor_call is exercised.

    Patching supervisor_call itself would be simpler and would test less: the Authorization
    header, the JSON body and the fact that no request is made without a token all live in the
    function being replaced.
    """

    def __init__(
        self,
        *,
        network: dict[str, Any] | None = None,
        connect_error: BaseException | None = None,
        read_error: BaseException | None = None,
        raw_body: bytes | None = None,
    ) -> None:
        self.network = network or {}
        # Raised from urlopen: the connection never completed.
        self.connect_error = connect_error
        # Raised from response.read(): the connection opened and the body went wrong. This is
        # where http.client.IncompleteRead actually comes from, so a fake that raised it from
        # urlopen instead would pass while proving nothing about the real failure position.
        self.read_error = read_error
        # A body that is not JSON, for the JSONDecodeError arm.
        self.raw_body = raw_body
        self.requests: list[Any] = []

    def __call__(self, request: Any, timeout: float | None = None) -> Any:
        self.requests.append(request)
        if self.connect_error is not None:
            raise self.connect_error
        if self.read_error is not None:
            return _failing_response(self.read_error)
        if self.raw_body is not None:
            return _raw_response(self.raw_body)
        path = request.full_url.removeprefix(addon_init.SUPERVISOR_URL)
        if path == SELF_INFO_PATH:
            body = {"data": {"hostname": HOSTNAME, "network": self.network}}
        else:
            body = {"result": "ok"}
        return _response(body)

    def request_to(self, path: str) -> Any:
        matches = [r for r in self.requests if r.full_url.endswith(path)]
        assert matches, f"no request was made to {path}"
        return matches[-1]

    def payload_to(self, path: str) -> dict[str, Any]:
        return json.loads(self.request_to(path).data.decode())


class _Ctx(io.BytesIO):
    """A urlopen return value: a file-like object usable as a context manager."""

    def __enter__(self) -> io.BytesIO:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _response(body: dict[str, Any]) -> Any:
    return _Ctx(json.dumps(body).encode())


def _raw_response(body: bytes) -> Any:
    return _Ctx(body)


def _failing_response(error: BaseException) -> Any:
    class _Broken(_Ctx):
        def read(self, *args: object) -> bytes:
            raise error

    return _Broken(b"")


@pytest.fixture
def options_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Write an options.json and point addon_init at it. Returns a writer taking overrides."""

    def write(**overrides: Any) -> Path:
        path = tmp_path / "options.json"
        merged = {**DEFAULT_OPTIONS, **overrides}
        # An explicit None removes the key, so a test can model an option the Supervisor omits.
        path.write_text(json.dumps({k: v for k, v in merged.items() if v is not None}))
        monkeypatch.setattr(addon_init, "OPTIONS_PATH", path)
        return path

    return write


@pytest.fixture
def env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "labelito.env"
    monkeypatch.setattr(addon_init, "ENV_FILE", path)
    return path


@pytest.fixture
def supervisor(monkeypatch: pytest.MonkeyPatch):
    """Install a FakeSupervisor with a Supervisor token present. Returns a factory."""

    def install(**kwargs: Any) -> FakeSupervisor:
        monkeypatch.setenv("SUPERVISOR_TOKEN", "supervisor-token")
        fake = FakeSupervisor(**kwargs)
        monkeypatch.setattr(addon_init.urllib.request, "urlopen", fake)
        return fake

    return install


@pytest.fixture
def no_supervisor(monkeypatch: pytest.MonkeyPatch) -> None:
    """No Supervisor token at all: supervisor_call must short-circuit before any request."""
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)

    def explode(*args: object, **kwargs: object) -> None:
        raise AssertionError("a request was made without a Supervisor token")

    monkeypatch.setattr(addon_init.urllib.request, "urlopen", explode)


# Variables bash sets for itself, which are not part of what the file exported.
_SHELL_OWN = {"PATH", "PWD", "OLDPWD", "SHLVL", "_"}


def parse_env(path: Path) -> dict[str, str]:
    """Read the generated file the way run.sh does — through bash, not a regex.

    run.sh does `set -a; source /tmp/labelito.env`, so the only authority on what a value means
    is bash. Parsing it in Python would be testing our own parser against itself.

    The subprocess starts from an EMPTY environment on purpose. Inheriting the caller's would
    make every `assert "API_TOKEN" not in env` a statement about the developer's shell instead of
    about the generated file — it passed or failed depending on who ran it.
    """
    import subprocess

    script = f'set -a; source "{path}"; env'
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": "/usr/bin:/bin"},
    )
    return {
        key: value
        for key, value in (
            line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
        )
        if key not in _SHELL_OWN
    }
