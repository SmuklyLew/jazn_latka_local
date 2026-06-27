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
from latka_jazn.version import PACKAGE_VERSION


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


def test_daemon_marker_payload_uses_clean_package_version(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text(f"{PACKAGE_VERSION}\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")
    marker_path = daemon_default_marker_path(tmp_path)
    write_active_runtime_marker(tmp_path, marker_output=marker_path)
    cfg = JaznConfig(root=tmp_path)
    server = JaznDaemonServer((DEFAULT_DAEMON_HOST, 0), JaznDaemonHandler, config=cfg, marker_path=marker_path)
    try:
        payload = server.marker_payload()
    finally:
        server.server_close()

    assert payload["version"] == PACKAGE_VERSION
    assert payload["version"] == (tmp_path / "VERSION.txt").read_text(encoding="utf-8").strip()
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
