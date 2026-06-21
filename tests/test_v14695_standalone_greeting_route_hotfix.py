from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.lexical_semantics import LexicalSemanticUnderstanding
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator


def test_standalone_dzien_dobry_routes_to_greeting_not_workday() -> None:
    decision = ConversationResponder().compose("Dzień dobry!")
    data = decision.to_dict()
    assert data["route"] == "greeting"
    assert data["detected_user_intent"] == "standalone_greeting"
    assert "drzwi" not in data["body"].lower()
    assert "dziewię" not in data["body"].lower()


def test_lexical_semantics_dzien_dobry_not_daily_observation() -> None:
    root = Path(__file__).resolve().parents[1]
    report = LexicalSemanticUnderstanding(root).analyse("Dzień dobry!").to_dict()
    assert report["route_hint"] != "ordinary_daily_conversation"
    assert "ordinary_day" not in report["intent_tags"]


def test_runtime_validator_blocks_stale_workday_details_in_greeting() -> None:
    validation = RuntimeAnswerValidator().validate(
        user_text="Dzień dobry!",
        body=(
            "To brzmi jak konkretny, ciężki dzień pracy. Przy dziewięciu sztukach drzwi "
            "najważniejsze jest tempo, ręce i głowa."
        ),
        route="ordinary_workday_dialogue",
        detected_intent="ordinary_conversation",
    )
    assert validation.must_regenerate is True
    assert validation.can_show_to_user is False
    assert validation.required_repair_route == "standalone_greeting_repair"
    assert "drzwi" not in (validation.repair_body or "").lower()


def test_engine_process_turn_dzien_dobry_no_stale_door_context() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v14695_greeting.sqlite3")
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn("Dzień dobry!", client_context={"client": "pytest", "lifecycle": "one_shot"})
        data = envelope.to_dict()
        contract = data["final_response_contract"]
        final_text = data["final_visible_text"] or ""
        assert contract["runtime_route"] == "greeting"
        assert contract["fallback_classification"] == "not_fallback"
        assert "drzwi" not in final_text.lower()
        assert "dziewię" not in final_text.lower()
        assert data["cognitive_frame"]["lexical_semantic_understanding"]["route_hint"] != "ordinary_daily_conversation"
    finally:
        engine.shutdown()
