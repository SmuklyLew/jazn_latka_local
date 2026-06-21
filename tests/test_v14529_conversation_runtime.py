from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.engine import JaznEngine


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def test_conversation_responder_turns_runtime_complaint_into_dialogue() -> None:
    decision = ConversationResponder().compose(
        "Odpowiedź runtime to debugowy fallback. Jaźń runtime jeszcze nie rozmawia.",
        intent_tags=["architecture", "correction", "dialogue_repair"],
    )
    assert decision.debug_fallback_used is False
    assert decision.route == "runtime_conversation_repair"
    assert "normalna ścieżka odpowiada rozmownie" in decision.body
    assert "--cognitive-frame" in decision.body


def test_direct_runtime_ordinary_positive_message_is_not_quiet_or_debug_fallback(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        engine.last_turn_at = time.time() - 700
        reply = engine.handle_user_message("O. To super.", client_context={"client": "unit_test"})
    finally:
        engine.shutdown()

    assert "runtime odebrał wiadomość" not in reply
    assert "Nie znalazłam osobnej trasy" not in reply
    assert "Po tej ciszy" not in reply
    assert "Też się cieszę" in reply


def test_debug_direct_still_exposes_diagnostics_when_requested(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        reply = engine.handle_user_message("O. To super.", client_context={"client": "unit_test", "debug_direct": True})
    finally:
        engine.shutdown()

    assert "runtime odebrał wiadomość" in reply
    assert "--debug-direct" in reply


def test_main_parser_makes_debug_direct_explicit() -> None:
    from main import _build_parser

    parser = _build_parser()
    normal = parser.parse_args(["O. To super."])
    debug = parser.parse_args(["--debug-direct", "O. To super."])

    assert normal.debug_direct is False
    assert debug.debug_direct is True
    assert " ".join(normal.message) == "O. To super."
    assert " ".join(debug.message) == "O. To super."


def test_cognitive_frame_declares_direct_conversation_runtime(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame("Runtime ma rozmawiać, nie fallbackować.", client_context={"client": "unit_test"})
    finally:
        engine.shutdown()

    assert packet["runtime_version"] == "v14.8.2.4-logic-routing-memory-grounding-repair"
    assert packet["direct_conversation_runtime"]["default_mode"] == "conversation_not_debug"
    assert packet["direct_conversation_runtime"]["debug_mode"] == "--debug-direct"
    assert packet["direct_conversation_runtime"]["empty_fallback_policy"] == "forbidden_in_normal_conversation"
