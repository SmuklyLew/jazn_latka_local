from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.final_response_contract import FinalResponseContract

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def test_leading_greeting_does_not_mask_substantive_last_year_question() -> None:
    decision = ConversationResponder().compose("Dobry wieczór. Co myślisz o zeszłym roku?")
    data = decision.to_dict()
    assert data["route"] == "last_year_reflection"
    assert data["direct_answer_required"] is True
    assert data["greeting_prefix"] == "dobry wieczór"
    assert data["substantive_remainder"] == "Co myślisz o zeszłym roku"
    assert "Jak Ci dzisiaj" not in data["body"]
    assert "2025" in data["body"] or "zeszłym roku" in data["body"]


def test_standalone_greeting_keeps_presence_badge_and_followup() -> None:
    decision = ConversationResponder().compose("Dobry wieczór")
    data = decision.to_dict()
    assert data["route"] == "greeting"
    assert data["continuity_badge_allowed"] is True
    assert data["runtime_followup_required"] is True
    assert "Jak Ci dzisiaj" in data["body"]


def test_final_response_contract_preserves_runtime_intent_and_next_step() -> None:
    decision = ConversationResponder().compose("Dobry wieczór. Co myślisz o zeszłym roku?").to_dict()
    contract = FinalResponseContract.build(
        turn_id="turn-1",
        trace_id="trace-1",
        runtime_version=VERSION,
        timestamp_header="[🕒 2026-05-17 21:00:00 GMT+0200, niedziela, Europe/Warsaw]",
        timezone="Europe/Warsaw",
        state_emoticon="🌿",
        body="Odpowiedź na pytanie o zeszły rok.",
        conversation_decision=decision,
        continuity_badge_policy={"action": "kept"},
    ).to_dict()
    assert contract["schema_version"] == "final_response_contract/v14.7.0"
    assert contract["runtime_route"] == "last_year_reflection"
    assert contract["direct_answer_required"] is True
    assert contract["substantive_remainder"] == "Co myślisz o zeszłym roku"
    assert contract["preservation_contract"]["must_answer_substantive_remainder"] is True
    assert contract["preservation_contract"]["must_preserve_runtime_next_step"] is True


def test_engine_process_turn_uses_last_year_route_not_greeting(tmp_path: Path) -> None:
    cfg = JaznConfig(root=tmp_path, network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn(
            "Dobry wieczór. Co myślisz o zeszłym roku?",
            client_context={"client": "unit_test", "lifecycle": "one_shot"},
        )
        data = envelope.to_dict()
        assert data["runtime_version"] == VERSION
        assert data["conversation_decision"]["route"] == "last_year_reflection"
        assert data["final_response_contract"]["direct_answer_required"] is True
        assert data["final_response_contract"]["substantive_remainder"] == "Co myślisz o zeszłym roku"
        assert "Jak Ci dzisiaj" not in (data["final_visible_text"] or "")
        assert data["cognitive_frame"]["continuity_badge_policy"]["schema_version"] == "continuity_badge_policy/v14.6.2"
    finally:
        engine.shutdown()


def test_core_repair_request_routes_to_next_version_update() -> None:
    decision = ConversationResponder().compose(
        "Przygotuj bardzo dobrą aktualizację systemu Jaźni do następnej wersji, naprawiającą fallbacki i problemy rdzenia."
    )
    data = decision.to_dict()
    assert data["route"] == "contextual_greeting_fallback_repair_update"
    assert data["direct_answer_required"] is True
    assert "v14.6.2" in (data["next_step"] or "")
