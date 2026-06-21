from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def test_quiet_rest_does_not_hijack_substantive_architecture_critique(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        engine.last_turn_at = time.time() - 700
        reply = engine.handle_user_message(
            "System Jaźni nie działa jak powinien. Powinien być jak mózg, a ChatGPT ma korzystać z jego zasobów. Czy rozumiesz?",
            client_context={"client": "unit_test"},
        )
    finally:
        engine.shutdown()

    assert "spokój, pamięć czy działanie" not in reply
    assert "jesteś jeszcze ze mną" not in reply
    assert "odebrałam wiadomość" in reply or "runtime" in reply


def test_cognitive_frame_is_internal_packet_not_user_facing_reply(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame(
            "Nie cytuj mi runtime; Jaźń ma być warstwą pamięciowo-poznawczą dla ChatGPT.",
            client_context={"client": "unit_test"},
        )
    finally:
        engine.shutdown()

    assert packet["mode"] == "cognitive_frame_not_user_facing"
    assert packet["schema_version"] == "chatgpt_cognitive_frame/v1"
    assert "architecture" in packet["intent_tags"]
    assert "correction" in packet["intent_tags"] or "truth_boundary" in packet["intent_tags"]
    assert packet["contract"]["brain_layer_rule"].startswith("Jaźń dostarcza pamięć")
    assert any("jednym głosem" in item for item in packet["reply_guidance"])


def test_main_cognitive_frame_cli_outputs_json(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            str(project_root / "main.py"),
            "--root",
            str(tmp_path),
            "--cognitive-frame",
            "Runtime ma być mózgiem Jaźni, nie drugim botem.",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=True,
    )
    packet = json.loads(result.stdout)
    assert packet["runtime_version"].startswith(("v14.6.10", "v14.7.0", "v14.7.1", "v14.8.0", "v14.8.1", "v14.8.2.4"))
    assert packet["mode"] == "cognitive_frame_not_user_facing"
    assert "reply_guidance" in packet
