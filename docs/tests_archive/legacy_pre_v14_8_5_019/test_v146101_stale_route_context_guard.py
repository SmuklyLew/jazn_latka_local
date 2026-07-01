from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.core.runtime_response_synthesizer import RuntimeResponseSynthesizer
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier


def test_contextual_do_it_now_inherits_only_safe_system_context() -> None:
    previous = "warstwa rozmownej odpowiedzi runtime ma jeszcze błąd stale-route/starego kontekstu. Co z tym zrobić?"
    report = DialogueIntentClassifier().classify("Możesz to teraz zrobić?", previous_text=previous)
    assert report.primary_intent == "system_update_execution_request"
    assert report.update_request is True
    assert report.diagnostic_request is True
    assert any("poprzednia tura" in item for item in report.evidence)


def test_contextual_do_it_now_without_safe_previous_context_is_not_update() -> None:
    report = DialogueIntentClassifier().classify("Możesz to teraz zrobić?", previous_text="Może pójdziemy na spacer?")
    assert report.primary_intent != "system_update_execution_request"


def test_stale_route_diagnostic_synthesizer_mentions_current_bug_and_files() -> None:
    result = RuntimeResponseSynthesizer().synthesize(
        user_text="warstwa rozmownej odpowiedzi runtime ma jeszcze błąd stale-route/starego kontekstu. Co z tym zrobić?",
        detected_intent="system_diagnostic_question",
        original_body="Przyjmuję tę korektę.",
        route="correction_acknowledged",
        template_origin={},
        validation={"must_regenerate": True},
    )
    assert result.should_override is True
    assert "stale-route" in result.body
    assert "engine.py" in result.body
    assert "runtime_answer_validator.py" in result.body
    assert "regres" in result.body.lower()


def test_validator_repairs_stale_route_diagnostic_that_loses_current_bug() -> None:
    validation = RuntimeAnswerValidator().validate(
        user_text="warstwa rozmownej odpowiedzi runtime ma jeszcze błąd stale-route/starego kontekstu. Co z tym zrobić?",
        body="Diagnoza runtime: problem dotyczy ścieżki rozpoznanie-intencja-trasa-szablon-walidacja.",
        route="runtime_diagnostic",
        detected_intent="system_diagnostic_question",
    )
    assert validation.must_regenerate is True
    assert validation.required_repair_route == "stale_route_context_guard_repair"
    assert "stale-route" in (validation.repair_body or "")


def test_process_turn_carries_context_for_immediate_execution_request(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v146101_context.sqlite3")
    engine = JaznEngine(cfg)
    try:
        first = engine.process_turn(
            "warstwa rozmownej odpowiedzi runtime ma jeszcze błąd stale-route/starego kontekstu. Co z tym zrobić?",
            client_context={"client": "pytest", "lifecycle": "chat_loop"},
        ).to_dict()
        second = engine.process_turn(
            "Możesz to teraz zrobić?",
            client_context={"client": "pytest", "lifecycle": "chat_loop"},
        ).to_dict()
        assert first["final_response_contract"]["runtime_route"] == "runtime_diagnostic"
        assert second["cognitive_frame"]["dialogue_intent_classifier"]["primary_intent"] == "system_update_execution_request"
        assert second["final_response_contract"]["runtime_route"] == "system_update"
        assert second["cognitive_frame"]["turn_context_carryover"]["previous_user_text_used"] is True
    finally:
        engine.shutdown()
