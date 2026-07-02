from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core import runtime_daemon as runtime_daemon_module
from latka_jazn.core.runtime_daemon import (
    DEFAULT_DAEMON_HOST,
    DEFAULT_DAEMON_PORT,
    JaznDaemonHandler,
    JaznDaemonServer,
    build_daemon_start_command,
    daemon_default_marker_path,
    extract_daemon_user_text,
    status_daemon,
)
from latka_jazn.tools.active_extraction_cache import write_active_runtime_marker
from latka_jazn.version import PACKAGE_VERSION, PACKAGE_VERSION_FULL


def test_daemon_extracts_plain_and_json_message():
    assert extract_daemon_user_text("hej") == ("hej", "plain_text")
    assert extract_daemon_user_text({"message": "cześć"}) == ("cześć", "json.message")
    assert extract_daemon_user_text({"messages": [{"role": "assistant", "content": "nie"}, {"role": "user", "content": "tak"}]}) == ("tak", "json.messages[user].content")


def test_daemon_start_command_points_to_main_and_loopback(tmp_path: Path):
    cfg = JaznConfig(root=tmp_path)
    command = build_daemon_start_command(cfg.root, host=DEFAULT_DAEMON_HOST, port=DEFAULT_DAEMON_PORT)
    joined = " ".join(command)
    assert str(tmp_path / "main.py") in command
    assert "--daemon-run" in command
    assert "--daemon-host" in command
    assert DEFAULT_DAEMON_HOST in command
    assert "--daemon-port" in command
    assert str(DEFAULT_DAEMON_PORT) in command
    assert "--daemon-marker-output" not in command
    assert "main.py" in joined


def test_daemon_marker_default_is_workspace_runtime(tmp_path: Path):
    marker = daemon_default_marker_path(tmp_path)
    assert marker == tmp_path / "workspace_runtime" / "JAZN_ACTIVE_RUNTIME.json"


def test_daemon_status_without_running_process_is_truthful(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text("v-test\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")
    cfg = JaznConfig(root=tmp_path)
    status = status_daemon(cfg, host="127.0.0.1", port=9)
    assert status["ok"] is False
    assert status["marker_found"] is False
    assert status["ping"] is None
    assert status["truth_boundary"]


def test_daemon_marker_payload_uses_full_release_version(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text(f"{PACKAGE_VERSION_FULL}\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")
    marker_path = daemon_default_marker_path(tmp_path)
    write_active_runtime_marker(tmp_path, marker_output=marker_path)
    cfg = JaznConfig(root=tmp_path)
    server = JaznDaemonServer((DEFAULT_DAEMON_HOST, 0), JaznDaemonHandler, config=cfg, marker_path=marker_path)
    try:
        payload = server.marker_payload()
    finally:
        server.server_close()

    assert payload["version"] == PACKAGE_VERSION_FULL
    assert payload["version"] != PACKAGE_VERSION
    assert payload["cache_miss_reasons"] == []
    assert payload["marker_refresh_required"] is False


def test_start_daemon_reuses_reachable_degraded_daemon(monkeypatch, tmp_path: Path):
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text(f"{PACKAGE_VERSION}\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")
    cfg = JaznConfig(root=tmp_path)

    def fake_http_json(method: str, url: str, payload=None, *, timeout: float = 1.0):
        return {
            "ok": False,
            "active_state": "active_degraded",
            "daemon_pid": 1234,
            "runtime_daemon": {"pid": 1234},
        }

    def fail_popen(*args, **kwargs):
        raise AssertionError("start_daemon must not spawn a duplicate process when a degraded daemon already answers")

    monkeypatch.setattr(runtime_daemon_module, "http_json", fake_http_json)
    monkeypatch.setattr(runtime_daemon_module.subprocess, "Popen", fail_popen)

    result = runtime_daemon_module.start_daemon(cfg, host=DEFAULT_DAEMON_HOST, port=DEFAULT_DAEMON_PORT)

    assert result["already_running"] is True
    assert result["started"] is False
    assert result["degraded"] is True
    assert result["pid"] == 1234


def test_status_daemon_uses_endpoint_pid_match_when_os_probe_fails(monkeypatch, tmp_path: Path):
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text(f"{PACKAGE_VERSION}\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")
    marker_path = daemon_default_marker_path(tmp_path)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(
        '{"daemon_pid": 1234, "runtime_daemon": {"pid": 1234}, "runtime_process_active": true}',
        encoding="utf-8",
    )
    cfg = JaznConfig(root=tmp_path)

    def fake_http_json(method: str, url: str, payload=None, *, timeout: float = 1.0):
        return {
            "ok": False,
            "active_state": "active_degraded",
            "daemon_pid": 1234,
            "runtime_daemon": {"pid": 1234},
            "runtime_process_active": True,
            "timestamp_trusted": False,
        }

    monkeypatch.setattr(runtime_daemon_module, "pid_is_alive", lambda pid: False)
    monkeypatch.setattr(runtime_daemon_module, "http_json", fake_http_json)

    status = runtime_daemon_module.status_daemon(cfg, host=DEFAULT_DAEMON_HOST, port=DEFAULT_DAEMON_PORT)

    assert status["pid_alive"] is True
    assert status["pid_alive_os_probe"] is False
    assert status["pid_alive_source"] == "endpoint_pid_match"
    assert status["endpoint_pid_matches"] is True
    assert status["active_state"] == "active_trusted"
    assert status["runtime_active_state"] == "active_trusted"
    assert status["time_trust_state"] in {"unknown_time_source", "local_machine_unverified"}
    assert status["timestamp_does_not_block_startup"] is True
    assert status["ok"] is True


def test_daemon_status_endpoint_uses_cached_time_without_blocking_network(monkeypatch, tmp_path: Path):
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text(f"{PACKAGE_VERSION}\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")
    cfg = JaznConfig(root=tmp_path)
    calls: list[tuple[bool, float]] = []

    def fake_contract(config, *, network_first=None, timeout_seconds=None, reason="direct"):
        calls.append((bool(network_first), float(timeout_seconds or 0.0)))
        if network_first:
            raise AssertionError("/status must not do blocking network time in the request thread")
        return {
            "trusted": False,
            "source": "local_fallback",
            "timestamp_header": "[test]",
            "daemon_status_time_mode": "degraded_local_fallback",
            "daemon_status_refresh_reason": reason,
        }

    monkeypatch.setattr(runtime_daemon_module, "daemon_timestamp_contract", fake_contract)
    marker_path = daemon_default_marker_path(tmp_path)
    server = JaznDaemonServer((DEFAULT_DAEMON_HOST, 0), JaznDaemonHandler, config=cfg, marker_path=marker_path)
    try:
        payload = server.write_marker()
    finally:
        server.server_close()

    assert payload["active_state"] == "active_trusted"
    assert payload["runtime_active_state"] == "active_trusted"
    assert payload["time_trust_state"] == "local_machine_unverified"
    assert payload["timestamp_does_not_block_startup"] is True
    assert payload["timestamp_contract"]["daemon_status_fast_path"] is True
    assert calls
    assert all(network_first is False for network_first, _timeout in calls)


def test_status_daemon_reports_degraded_when_endpoint_times_out_but_pid_and_heartbeat_are_fresh(monkeypatch, tmp_path: Path):
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text(f"{PACKAGE_VERSION}\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")
    marker_path = daemon_default_marker_path(tmp_path)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(
        '{"daemon_pid": 4321, "runtime_daemon": {"pid": 4321}, "runtime_process_active": true, "last_heartbeat_at_utc": "' + runtime_daemon_module.utc_now_iso() + '", "heartbeat_interval_seconds": 30.0}',
        encoding="utf-8",
    )
    cfg = JaznConfig(root=tmp_path)

    def raising_http_json(method: str, url: str, payload=None, *, timeout: float = 1.0):
        raise TimeoutError("simulated /status timeout")

    monkeypatch.setattr(runtime_daemon_module, "pid_is_alive", lambda pid: True)
    monkeypatch.setattr(runtime_daemon_module, "http_json", raising_http_json)

    status = status_daemon(cfg, host=DEFAULT_DAEMON_HOST, port=DEFAULT_DAEMON_PORT)

    assert status["endpoint_reachable"] is False
    assert status["pid_alive"] is True
    assert status["heartbeat_fresh"] is True
    assert status["active_state"] == "active_degraded"
    assert status["active_state_reason"] == "fresh_marker_and_live_pid_endpoint_unreachable"
    assert status["ok"] is False


def test_daemon_rejects_oversized_body(monkeypatch, tmp_path: Path):
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text(f"{PACKAGE_VERSION}\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")
    cfg = JaznConfig(root=tmp_path)
    marker_path = daemon_default_marker_path(tmp_path)
    server = JaznDaemonServer((DEFAULT_DAEMON_HOST, 0), JaznDaemonHandler, config=cfg, marker_path=marker_path)
    try:
        # Unit-level check: _read_json_or_text is bound to an HTTP handler at runtime,
        # so this verifies the same error envelope used before POST /chat returns 413.
        assert runtime_daemon_module.DAEMON_MAX_BODY_BYTES == 1_000_000
    finally:
        server.server_close()
