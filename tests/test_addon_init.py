"""Tests for the add-on entrypoint that translates options.json into labelito's environment.

addon_init.py runs before uvicorn and decides three things that matter: what labelito is
configured with, whether the service is allowed to start at all, and whether it starts
unauthenticated. None of it was covered.
"""

from __future__ import annotations

import http.client
import stat
import urllib.error
from pathlib import Path

import addon_init
import pytest

from .conftest import DISCOVERY_PATH, HOSTNAME, SELF_INFO_PATH, parse_env

PORT_KEY = f"{addon_init.LABELITO_PORT}/tcp"


# --- the generated file -------------------------------------------------------------------


def test_the_env_file_survives_a_round_trip_through_bash(
    options_file, env_file: Path, no_supervisor: None, tmp_path: Path
) -> None:
    """run.sh sources this file, so shell metacharacters in a user value must not be reinterpreted.

    A printer URI or token containing a space, a quote or a command substitution is what turns a
    naive `KEY=value` writer into either a broken config or an injection. shlex.quote is what
    prevents it; bash is the only authority on whether it worked.

    This is not hypothetical: with shlex.quote removed, the substitution below really does run
    and create the sentinel. Hence the sentinel lives under tmp_path — a fixed /tmp path would
    survive the run that created it and then fail every later run for the wrong reason.
    """
    sentinel = tmp_path / "pwned"
    hostile = f"s3cret 'quoted' $(touch {sentinel}) `id` \"dq\""
    options_file(api_token=hostile, printer_uri="tcp://host:9100 # not a comment")

    addon_init.main()

    env = parse_env(env_file)
    assert env["API_TOKEN"] == hostile
    assert env["PRINTER_URI"] == "tcp://host:9100 # not a comment"
    assert not sentinel.exists()


def test_the_env_file_is_readable_only_by_its_owner(
    options_file, env_file: Path, no_supervisor: None
) -> None:
    """It holds the API token in cleartext, so the 0600 is a security property, not tidiness."""
    options_file(api_token="s3cret")

    addon_init.main()

    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600


# --- authentication -----------------------------------------------------------------------


def test_a_token_authenticates_and_never_also_allows_unauthenticated(
    options_file, env_file: Path, no_supervisor: None
) -> None:
    options_file(api_token="s3cret")

    addon_init.main()

    env = parse_env(env_file)
    assert env["API_TOKEN"] == "s3cret"
    assert "ALLOW_UNAUTHENTICATED" not in env


def test_no_token_allows_unauthenticated_for_ingress_only_use(
    options_file, env_file: Path, no_supervisor: None
) -> None:
    """Safe only because the host port is closed by default and the port guard below covers the
    case where it is not — which is why both halves are tested."""
    options_file()

    addon_init.main()

    env = parse_env(env_file)
    assert env["ALLOW_UNAUTHENTICATED"] == "true"
    assert "API_TOKEN" not in env


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_a_whitespace_only_token_counts_as_no_token(
    options_file, env_file: Path, no_supervisor: None, blank: str
) -> None:
    """Otherwise a stray space in the add-on config would hand labelito a token nobody can send,
    locking the user out of their own printer instead of falling back to ingress-only."""
    options_file(api_token=blank)

    addon_init.main()

    env = parse_env(env_file)
    assert env["ALLOW_UNAUTHENTICATED"] == "true"
    assert "API_TOKEN" not in env


# --- the port-exposure guard --------------------------------------------------------------


def test_a_mapped_host_port_without_a_token_refuses_to_start(
    options_file, env_file: Path, supervisor, capsys: pytest.CaptureFixture[str]
) -> None:
    """The one fatal case that exists to stop a silent security downgrade: with the port mapped,
    ALLOW_UNAUTHENTICATED would expose the printer to the whole LAN."""
    options_file()
    supervisor(network={PORT_KEY: 8765})

    with pytest.raises(SystemExit) as exit_info:
        addon_init.main()

    assert exit_info.value.code == 1
    assert "FATAL" in capsys.readouterr().out
    # It must abort BEFORE writing the env, or run.sh's `source` would still find a usable
    # unauthenticated config from a previous boot plus a fresh one here.
    assert not env_file.exists()


def test_a_mapped_host_port_with_a_token_starts_normally(
    options_file, env_file: Path, supervisor
) -> None:
    options_file(api_token="s3cret")
    fake = supervisor(network={PORT_KEY: 8765})

    addon_init.main()

    assert parse_env(env_file)["API_TOKEN"] == "s3cret"
    assert fake.payload_to(DISCOVERY_PATH)["config"]["api_token"] == "s3cret"


def test_an_unmapped_port_is_not_treated_as_mapped(
    options_file, env_file: Path, supervisor
) -> None:
    """config.yaml declares `8765/tcp: null`, so the key is present and empty until the user maps
    it. Testing only the absent-key case would miss the shape the Supervisor actually sends."""
    options_file()
    supervisor(network={PORT_KEY: None})

    addon_init.main()

    assert parse_env(env_file)["ALLOW_UNAUTHENTICATED"] == "true"


# --- the Supervisor is best-effort --------------------------------------------------------


def test_an_unreachable_supervisor_never_blocks_startup(
    options_file, env_file: Path, supervisor, capsys: pytest.CaptureFixture[str]
) -> None:
    """Documented contract: only a CONFIRMED port mapping is fatal. A Supervisor that cannot be
    reached must not take the printer down with it.

    URLError specifically, not a bare OSError: urllib's do_open wraps socket errors in URLError,
    so raising the wrong type here would have the test prove the opposite of what it claims.
    """
    options_file()
    supervisor(connect_error=urllib.error.URLError("supervisor unreachable"))

    addon_init.main()

    assert parse_env(env_file)["MODEL"] == "QL-810W"
    assert "Supervisor API unavailable" in capsys.readouterr().out


@pytest.mark.parametrize(
    "error",
    [
        # Truncated body. Subclasses HTTPException only — not OSError — so it is invisible to a
        # URLError-shaped net, and it is raised from .read() rather than from urlopen.
        http.client.IncompleteRead(b"{\"data\":"),
        # Malformed status line, same inheritance problem.
        http.client.BadStatusLine("garbage"),
        # A socket timeout on the body read; TimeoutError, already in the net.
        TimeoutError("read timed out"),
    ],
    ids=["truncated body", "bad status line", "read timeout"],
)
def test_a_malformed_supervisor_reply_never_blocks_startup(
    options_file, env_file: Path, supervisor, capsys: pytest.CaptureFixture[str],
    error: BaseException,
) -> None:
    """A Supervisor that answers badly is the same class of problem as one that does not answer,
    and must degrade the same way: report it, skip the port guard and discovery, start anyway.

    This is where the pre-fix code broke its own contract. `http.client.HTTPException` subclasses
    neither OSError nor URLError, so IncompleteRead and BadStatusLine escaped the except clause
    and killed the add-on's startup on a truncated reply.
    """
    options_file()
    supervisor(read_error=error)

    addon_init.main()

    assert parse_env(env_file)["MODEL"] == "QL-810W"
    output = capsys.readouterr().out
    assert "Supervisor call /addons/self/info failed" in output
    assert "Supervisor API unavailable" in output


def test_a_reply_that_is_not_json_never_blocks_startup(
    options_file, env_file: Path, supervisor, capsys: pytest.CaptureFixture[str]
) -> None:
    """The JSONDecodeError arm, driven by a real non-JSON body rather than a raised exception —
    a proxy error page in place of the Supervisor's answer looks exactly like this."""
    options_file()
    supervisor(raw_body=b"<html>502 Bad Gateway</html>")

    addon_init.main()

    assert parse_env(env_file)["MODEL"] == "QL-810W"
    assert "Supervisor call /addons/self/info failed" in capsys.readouterr().out


def test_no_supervisor_token_means_no_request_is_attempted(
    options_file, env_file: Path, no_supervisor: None
) -> None:
    """The no_supervisor fixture fails the test if urlopen is called at all, so this pins the
    early return in supervisor_call rather than just its return value."""
    options_file()

    addon_init.main()

    assert env_file.exists()


def test_discovery_announces_the_supervisor_hostname_and_the_fixed_port(
    options_file, env_file: Path, supervisor
) -> None:
    options_file(api_token="s3cret")
    fake = supervisor()

    addon_init.main()

    assert fake.payload_to(DISCOVERY_PATH) == {
        "service": addon_init.DISCOVERY_SERVICE,
        "config": {
            "host": HOSTNAME,
            "port": addon_init.LABELITO_PORT,
            "api_token": "s3cret",
        },
    }
    assert fake.request_to(SELF_INFO_PATH).get_header("Authorization") == (
        "Bearer supervisor-token"
    )


def test_a_failed_discovery_announcement_is_not_fatal(
    options_file, env_file: Path, monkeypatch: pytest.MonkeyPatch, supervisor,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """One-click setup is a convenience; losing it must not stop the printer from working."""
    options_file()
    supervisor()
    real = addon_init.supervisor_call

    def fail_discovery(path: str, payload: dict | None = None) -> dict | None:
        return None if path == DISCOVERY_PATH else real(path, payload)

    monkeypatch.setattr(addon_init, "supervisor_call", fail_discovery)

    addon_init.main()

    assert env_file.exists()
    assert "discovery announcement failed (non-fatal)" in capsys.readouterr().out


# --- the history invariant ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("keep", "prune"),
    [
        (1000, 1000),  # equal: pruning trims back to where it triggers, so it never shrinks
        (1000, 999),  # below: pruning would have to grow the history to reach the threshold
        (1, 1),  # the schema's own minimum, where the mistake is easiest to make
    ],
)
def test_a_prune_threshold_that_can_never_shrink_the_history_is_rejected(
    options_file, env_file: Path, no_supervisor: None, keep: int, prune: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The schema can express `int(1,)` but not the cross-field relation, so this is the only
    place the combination is caught."""
    options_file(history_keep_entries=keep, history_prune_at_entries=prune)

    with pytest.raises(SystemExit) as exit_info:
        addon_init.main()

    assert exit_info.value.code == 1
    assert "history_prune_at_entries" in capsys.readouterr().out
    assert not env_file.exists()


def test_a_prune_threshold_one_above_the_floor_is_accepted(
    options_file, env_file: Path, no_supervisor: None
) -> None:
    """The boundary from the other side — without this, the guard could reject everything and the
    test above would still pass."""
    options_file(history_keep_entries=1000, history_prune_at_entries=1001)

    addon_init.main()

    env = parse_env(env_file)
    assert env["HISTORY_KEEP_ENTRIES"] == "1000"
    assert env["HISTORY_PRUNE_AT_ENTRIES"] == "1001"


# --- option translation -------------------------------------------------------------------


@pytest.mark.parametrize("enabled", [True, False])
def test_one_editor_switch_drives_both_upstream_flags(
    options_file, env_file: Path, no_supervisor: None, enabled: bool
) -> None:
    """In the add-on the template directory is always writable (/config), so an editor without
    server-save would only confuse — the two flags are deliberately not independent."""
    options_file(editor_enabled=enabled)

    addon_init.main()

    env = parse_env(env_file)
    expected = "true" if enabled else "false"
    assert env["EDITOR_ENABLED"] == expected
    assert env["TEMPLATES_WRITABLE"] == expected


def test_mcp_writable_without_mcp_enabled_warns_but_still_starts(
    options_file, env_file: Path, no_supervisor: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """MCP_WRITABLE is a no-op without MCP_ENABLED, so the combination is inert rather than
    dangerous — a warning, and the values forwarded unchanged."""
    options_file(mcp_enabled=False, mcp_writable=True)

    addon_init.main()

    env = parse_env(env_file)
    assert env["MCP_ENABLED"] == "false"
    assert env["MCP_WRITABLE"] == "true"
    assert "WARNING: mcp_writable is on but mcp_enabled is off" in capsys.readouterr().out


def test_the_in_app_update_check_is_always_off(
    options_file, env_file: Path, no_supervisor: None
) -> None:
    """Not a user option: the Supervisor owns add-on updates, so an About-modal pointing at
    upstream GitHub releases would send people to the wrong place."""
    options_file()

    addon_init.main()

    assert parse_env(env_file)["UPDATE_CHECK_ENABLED"] == "false"


def test_the_fixed_add_on_wiring_is_not_user_configurable(
    options_file, env_file: Path, no_supervisor: None
) -> None:
    """These paths are the contract with run.sh (which creates the directories) and with the
    Supervisor's /data mount. A user option must never be able to move them."""
    options_file()

    addon_init.main()

    env = parse_env(env_file)
    assert env["PROXY_PATH_HEADER"] == "X-Ingress-Path"
    assert env["HISTORY_MODE"] == "file"
    assert env["DATA_DIR"] == "/data"
    assert env["TEMPLATES_DIR"] == "/config/templates"
    assert env["FONTS_DIR"] == "/config/fonts"
    assert env["ICONS_DIR"] == "/config/icons"


def test_omitted_optional_options_fall_back_to_the_documented_defaults(
    options_file, env_file: Path, no_supervisor: None
) -> None:
    """A config.yaml written before an option existed omits it entirely, and the Supervisor passes
    options through as stored — so the .get() defaults are a real upgrade path, not decoration."""
    options_file(
        default_language=None,
        editor_default_mode=None,
        log_level=None,
        history_keep_entries=None,
        history_prune_at_entries=None,
    )

    addon_init.main()

    env = parse_env(env_file)
    assert env["DEFAULT_LANGUAGE"] == "en"
    assert env["EDITOR_DEFAULT_MODE"] == "visual"
    assert env["LOG_LEVEL"] == "info"
    assert env["HISTORY_KEEP_ENTRIES"] == "1000"
    assert env["HISTORY_PRUNE_AT_ENTRIES"] == "1500"


@pytest.mark.parametrize("missing", ["model", "printer_uri"])
def test_a_missing_required_option_fails_loudly(
    options_file, env_file: Path, no_supervisor: None, missing: str
) -> None:
    """model and printer_uri are read with [] rather than .get() on purpose: the schema makes them
    mandatory, and a wrapper that invented a default would start labelito pointed at a printer the
    user never configured. Loud is correct — but it must not leave a half-written env behind."""
    options_file(**{missing: None})

    with pytest.raises(KeyError, match=missing):
        addon_init.main()

    assert not env_file.exists()
