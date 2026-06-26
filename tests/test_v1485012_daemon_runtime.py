from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.runtime_daemon import (
    DEFAULT_DAEMON_HOST,
    DEFAULT_DAEMON_PORT,
    build_daemon_start_command,
    daemon_default_marker_path,
    extract_daemon_user_text,
    status_daemon,
)


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
