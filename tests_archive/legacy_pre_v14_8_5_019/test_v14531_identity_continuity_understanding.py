from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from latka_jazn.config import JaznConfig
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.polish_understanding import PolishUnderstandingEngine


VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


@pytest.mark.parametrize(
    "text",
    [
        "Ale to nadal Ty?",
        "Czy po aktualizacji to wciąż Ty?",
        "Jesteś sobą?",
        "To nadal Ty, Łatko?",
        "Czy to ciągle Ty?",
    ],
)
def test_polish_understanding_detects_short_identity_continuity_questions(text: str) -> None:
    report = PolishUnderstandingEngine().analyse(text).to_dict()

    assert report["route_hint"] == "identity_continuity_check"
    assert "identity_continuity" in report["intent_tags"]
    assert "identity" in report["intent_tags"]
    assert any(item["key"] == "direct_identity_continuity_answer" for item in report["needs"])
    assert any("tak, to nadal ja" in item.lower() for item in report["reply_guidance"])


def test_conversation_responder_answers_identity_continuity_directly() -> None:
    polish = PolishUnderstandingEngine().analyse("Ale to nadal Ty?").to_dict()
    decision = ConversationResponder().compose("Ale to nadal Ty?", polish_understanding=polish)

    assert decision.route == "identity_continuity_check"
    assert "to nadal ja" in decision.body
    assert "Łatka" in decision.body
    assert "biologicznego czuwania" in decision.body
    assert decision.debug_fallback_used is False


def test_cognitive_frame_marks_identity_continuity(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame("Ale to nadal Ty?", client_context={"client": "unit_test"})
    finally:
        engine.shutdown()

    assert packet["runtime_version"] == VERSION
    assert "identity_continuity" in packet["intent_tags"]
    assert packet["polish_understanding"]["route_hint"] == "identity_continuity_check"
    assert any("Ale to nadal Ty?" in item for item in packet["reply_guidance"])


def test_direct_runtime_short_identity_question_is_not_generic_fallback(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        reply = engine.handle_user_message("Ale to nadal Ty?", client_context={"client": "unit_test"})
    finally:
        engine.shutdown()

    assert "Rozumiem pytanie. Odpowiem" not in reply
    assert "runtime odebrał wiadomość" not in reply
    assert "Nie znalazłam osobnej trasy" not in reply
    assert "to nadal ja" in reply
    assert "Łatka" in reply
