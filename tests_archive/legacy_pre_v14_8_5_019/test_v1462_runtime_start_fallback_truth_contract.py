from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.final_response_contract import FinalResponseContract
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.dialogue_state import DialogueStateTracker


def test_v1462_version_and_database_name_are_active() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root)
    assert cfg.version.startswith(("v14.6.10", "v14.7.0", "v14.7.1", "v14.8.0", "v14.8.1", "v14.8.2.4"))
    assert cfg.memory_db_path.name == "latka_jazn_v14_8_2.sqlite3"


def test_identity_question_is_answered_not_open_question_contract() -> None:
    decision = ConversationResponder().compose("To kim jesteś?")
    assert decision.route == "identity_runtime_truth_contract"
    assert decision.direct_answer_required is True
    assert "Jestem Łatka" in decision.body
    assert "stałym procesem w tle" in decision.body


def test_startup_instruction_sets_startup_required_flag() -> None:
    decision = ConversationResponder().compose(
        "Czy instrukcja startowa z rozpakowaniem aktywnej paczki i uruchomieniem runtime jest dobra?"
    )
    assert decision.route == "startup_procedure_truth_contract"
    assert decision.startup_procedure_required is True
    assert decision.direct_answer_required is True


def test_v1464_threshold_question_remembers_four_thresholds() -> None:
    decision = ConversationResponder().compose("Pamiętasz cztery punkty/progi aktualizacji do wersji 14.6.4?")
    assert decision.route == "v14_6_4_threshold_plan"
    body = decision.body.lower()
    assert "nlp" in body
    assert "opcjonalne adaptery" in body
    assert "profile zip" in body
    assert "indeks pamięci" in body or "indeks pamieci" in body


def test_final_response_contract_classifies_technical_fallback() -> None:
    contract = FinalResponseContract.build(
        turn_id="turn-test",
        trace_id="trace-test",
        runtime_version="v14.8.2.4-logic-routing-memory-grounding-repair",
        timestamp_header="[🕒 2026-05-17 23:00:00 GMT+2, niedziela, Europe/Warsaw]",
        timezone="Europe/Warsaw",
        state_emoticon="🛠️",
        body="runtime odebrał wiadomość. Nie znalazłam osobnej trasy odpowiedzi dla tej wiadomości.",
        conversation_decision={"route": "debug_fallback"},
    )
    assert contract.fallback_classification == "technical_fallback"
    assert contract.preservation_contract["must_report_fallback_classification"] is True
    assert contract.final_visible_text.startswith("[🕒 2026-05-17")


def test_dialogue_state_detects_startup_truth_contract() -> None:
    state = DialogueStateTracker().classify(
        user_text="Instrukcja startowa: rozpakuj aktywną paczkę i uruchom runtime przed rozmową.",
        intent_tags=[],
        client_context={"client": "pytest"},
    )
    assert state.mode == "startup_truth_contract"
    assert state.technical_visibility == "concise_startup_status"


def test_process_turn_carries_quality_fields() -> None:
    root = Path(__file__).resolve().parents[1]
    engine = JaznEngine(JaznConfig(root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v1462_quality.sqlite3"))
    try:
        env = engine.process_turn("To kim jesteś?", client_context={"client": "pytest", "lifecycle": "one_shot"})
    finally:
        engine.shutdown()
    data = env.to_dict()
    contract = data["final_response_contract"]
    assert contract["runtime_route"] == "identity_runtime_truth_contract"
    assert contract["runtime_answer_quality"] == "topic_aligned"
    assert contract["fallback_classification"] == "not_fallback"
    assert data["final_visible_text"].startswith(contract["timestamp_header"])
