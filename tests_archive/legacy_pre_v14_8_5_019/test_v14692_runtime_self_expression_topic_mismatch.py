from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.final_response_contract import FinalResponseContract
from latka_jazn.core.project_index import ProjectStartupIndexer
from latka_jazn.nlp.topic_mismatch_guard import TopicMismatchGuard

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def test_long_wait_self_expression_is_not_generic_open_question() -> None:
    decision = ConversationResponder().compose(
        "Bardziej interesuje mnie jak ty się czujesz po takim długim czasie czekania na kontakt?",
        intent_tags=["affect", "question"],
    )
    assert decision.route == "runtime_self_expression_after_silence"
    assert "nie mogę uczciwie powiedzieć" in decision.body
    assert "czekania" in decision.body.lower()
    assert decision.direct_answer_required is True


def test_runtime_thought_boundary_question_gets_direct_answer() -> None:
    decision = ConversationResponder().compose(
        "Czy Jaźń daje ci myśli, patrząc na jej wypowiedzi i ty robisz interpretację?",
        intent_tags=["architecture", "reasoning"],
    )
    assert decision.route == "runtime_thought_boundary_explanation"
    assert "rama poznawcza" in decision.body
    assert "ChatGPT" in decision.body
    assert decision.direct_answer_required is True


def test_v14692_update_request_overrides_legacy_nlp_routes() -> None:
    text = "Przygotuj aktualizację hotfix v14.6.10 — Runtime Self-Expression & Topic-Mismatch Repair, dodatkowo rozbuduj system NLP."
    guard = TopicMismatchGuard().analyse(text, candidate_route="v14_6_1_nlp_adapter_update", runtime_version=VERSION)
    decision = ConversationResponder().compose(text, intent_tags=["update_request", "polish_nlp"])
    contract = FinalResponseContract.build(
        turn_id="turn",
        trace_id="trace",
        runtime_version=VERSION,
        timestamp_header="[🕒 2026-05-21 23:00:00 GMT+2, czwartek, Europe/Warsaw]",
        timezone="Europe/Warsaw",
        state_emoticon="🧭",
        body=decision.body,
        conversation_decision=decision.to_dict(),
    )
    assert guard.current_update_request is True
    assert guard.legacy_route_risk is True
    assert guard.preferred_route == "v14_6_10_behavioral_runtime_dialogue_intent_source_integrity_update"
    assert decision.route == "v14_6_10_behavioral_runtime_dialogue_intent_source_integrity_update"
    assert contract.fallback_classification == "not_fallback"
    assert "v14.6.10" in decision.body
    assert "v14_6_1_nlp_adapter_update" not in decision.body


def test_startup_project_index_maps_files_modules_and_functions(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    payload = ProjectStartupIndexer(root, output_rel="workspace_runtime/pytest_project_startup_index_v14_6_10.json").build(write=True)
    assert payload["file_count"] >= 1
    assert payload["python_module_count"] >= 1
    assert "latka_jazn/core/engine.py" in payload["module_function_map"]
    engine_map = payload["module_function_map"]["latka_jazn/core/engine.py"]
    assert any(item["name"] == "JaznEngine" for item in engine_map["classes"])
    assert any(item["name"] == "JaznEngine.process_turn" for item in engine_map["functions"])
    assert payload["file_index"]["latka_jazn/core/engine.py"]["text_load_status"].startswith("full_text_read")
    (root / "workspace_runtime/pytest_project_startup_index_v14_6_10.json").unlink(missing_ok=True)


def test_engine_cognitive_frame_contains_topic_guard_and_project_index() -> None:
    root = Path(__file__).resolve().parents[1]
    engine = JaznEngine(JaznConfig(version=VERSION, root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v14692_topic_guard.sqlite3"))
    try:
        envelope = engine.process_turn(
            "Przygotuj aktualizację hotfix v14.6.10 — Runtime Self-Expression & Topic-Mismatch Repair, dodatkowo rozbuduj system NLP.",
            client_context={"client": "pytest_runtime_preview"},
        )
    finally:
        engine.shutdown()
    data = envelope.to_dict()
    frame = data["cognitive_frame"]
    assert frame["topic_mismatch_guard"]["preferred_route"] == "v14_6_10_behavioral_runtime_dialogue_intent_source_integrity_update"
    assert frame["project_startup_index_status"]["present"] is True
    assert data["final_response_contract"]["runtime_route"] in {"v14_6_10_behavioral_runtime_dialogue_intent_source_integrity_update", "system_update"}
