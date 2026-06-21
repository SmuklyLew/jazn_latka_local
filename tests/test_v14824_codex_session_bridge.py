import json
import os
from pathlib import Path
from types import SimpleNamespace

import latka_jazn.adapters.codex_session_bridge as bridge_module
from latka_jazn.adapters.codex_session_bridge import CodexSessionBridge, _sanitize_runtime_environment


def test_codex_session_bridge_reads_utf8_bom_and_tracks_queues(tmp_path: Path):
    bridge = CodexSessionBridge(tmp_path / "bridge")
    request = bridge.root / "requests" / "bom.json"
    request.write_text(json.dumps({"id": "bom", "text": "Super"}), encoding="utf-8-sig")
    assert bridge._read_json(request)["text"] == "Super"
    status = bridge.status()
    assert status["queues"]["requests"] == 1


def test_codex_session_bridge_stop_is_explicit_file(tmp_path: Path):
    bridge = CodexSessionBridge(tmp_path / "bridge")
    bridge.request_stop()
    assert bridge.stop_path.exists()


def test_codex_session_bridge_sanitizes_ssl_keylog_environment():
    previous = os.environ.get("SSLKEYLOGFILE")
    try:
        os.environ["SSLKEYLOGFILE"] = "unsafe-keylog-path"
        _sanitize_runtime_environment()
        assert "SSLKEYLOGFILE" not in os.environ
    finally:
        if previous is not None:
            os.environ["SSLKEYLOGFILE"] = previous


def test_codex_session_bridge_marks_dead_recorded_process_as_stale(tmp_path: Path):
    bridge = CodexSessionBridge(tmp_path / "bridge")
    bridge._write_json(bridge.runtime_status_path, {"state": "active", "pid": 2147483647})
    status = bridge.status()
    assert status["state"] == "stale"


def test_codex_session_bridge_marks_foreign_bridge_root_as_stale(tmp_path: Path):
    bridge = CodexSessionBridge(tmp_path / "bridge")
    bridge._write_json(
        bridge.runtime_status_path,
        {"state": "active", "pid": os.getpid(), "bridge_root": str(tmp_path / "other_bridge")},
    )
    status = bridge.status()
    assert status["state"] == "stale"
    assert status["stale_reason"] == "recorded_bridge_root_mismatch"
    assert status["expected_bridge_root"] == str(bridge.root.resolve())


def test_codex_session_bridge_send_processes_direct_when_server_missing(tmp_path: Path, monkeypatch):
    class FakeRuntime:
        def __init__(self, *, session_id: str):
            self.config = SimpleNamespace(
                version="test-runtime",
                conversation_archive_manifest_path=tmp_path / "archive.sqlite3",
                memory_db_path=tmp_path / "runtime.sqlite3",
                conversation_fts_dir=tmp_path / "fts",
                conversation_staging_dir=tmp_path / "staging",
            )
            self.state = SimpleNamespace(session_id=session_id)
            self.closed = False

        def process_user_text(self, text: str, *, client: str):
            return {
                "schema_version": "fake",
                "final_visible_text": f"echo:{text}",
                "client": client,
            }

        def close(self):
            self.closed = True

    monkeypatch.setattr(bridge_module, "JaznRuntimeSession", FakeRuntime)
    bridge = CodexSessionBridge(tmp_path / "bridge")

    response = bridge.send("Cześć", session_id="test-session", timeout_seconds=0.01)

    assert response["final_visible_text"] == "echo:Cześć"
    assert bridge.status()["state"] == "one_shot_complete"
    assert bridge.status()["queues"]["requests"] == 0
    assert bridge.status()["queues"]["processed"] == 1


def test_codex_session_bridge_send_keeps_direct_voice_text_clean(tmp_path: Path):
    bridge = CodexSessionBridge(tmp_path / "bridge")

    response = bridge.send(
        "Chcę rozmawiać z Łatką, a nie z Codex botem",
        session_id="direct-voice-clean-regression",
        timeout_seconds=30,
    )

    decision = response["conversation_decision"]
    handler_result = decision["handler_result"]
    runtime_provenance = decision["runtime_provenance"]
    final_visible_text = response["final_visible_text"]

    assert decision["route"] == "direct_latka_voice"
    assert decision["handler_name"] == "DirectLatkaVoiceHandler"
    assert handler_result["body"] == runtime_provenance["exact_runtime_text"]
    assert runtime_provenance["exact_runtime_text"] != runtime_provenance["visible_answer_text"]
    assert runtime_provenance["visible_answer_text"] == final_visible_text
    assert "Może esz" not in final_visible_text
    assert "diagnoostyka" not in final_visible_text
    assert "\\ \n" not in final_visible_text
    assert "Możesz teraz rozmawiać bezpośrednio z Łatką" in final_visible_text
