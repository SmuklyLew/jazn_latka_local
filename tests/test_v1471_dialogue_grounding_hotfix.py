from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.free_dialogue_synthesizer import FreeDialogueSynthesizer
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier


def test_self_plan_question_has_own_intent_not_generic_memory() -> None:
    report = DialogueIntentClassifier().classify("Pomijając mnie, to jakie plany masz?")
    assert report.primary_intent == "self_plan_question"
    assert report.question_object == "self_plan"


def test_free_dialogue_does_not_use_random_memory_for_neutral_open_question() -> None:
    memory_context = {
        "episodes": [
            {
                "scene": "Krzysztof mówił o montażu dziewięciu sztuk drzwi i zleceniu.",
                "source": "test_memory",
                "confidence": 0.9,
                "relevance": 0.9,
            }
        ],
        "counts": {"episodes": 1},
    }
    synthesis = FreeDialogueSynthesizer().synthesize_open_question(memory_context, user_text="Jakie plany masz na dzisiaj?")
    body = synthesis.body.lower()
    assert synthesis.detected_user_intent == "self_plan_question"
    assert "drzwi" not in body
    assert "zlecen" not in body
    assert "operacyjne" in body


def test_validator_repairs_self_plan_stale_workday_injection() -> None:
    validation = RuntimeAnswerValidator().validate(
        user_text="Jakie plany masz na dzisiaj?",
        body="Przy dziewięciu sztukach drzwi najważniejsze będzie tempo i narzędzia.",
        route="ordinary_workday_dialogue",
        detected_intent="self_plan_question",
    )
    assert validation.must_regenerate is True
    assert validation.required_repair_route == "self_plan_current_turn_repair"
    assert "drzwi" not in (validation.repair_body or "").lower()
    assert "operacyjne" in (validation.repair_body or "").lower()


def test_engine_process_turn_self_plan_no_stale_workday_context() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v1471_self_plan.sqlite3")
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn(
            "Pomijając mnie, to jakie plany masz?",
            client_context={"client": "pytest", "lifecycle": "one_shot"},
        ).to_dict()
        final_text = envelope["final_visible_text"] or ""
        contract = envelope["final_response_contract"]
        assert envelope["cognitive_frame"]["dialogue_intent_classifier"]["primary_intent"] == "self_plan_question"
        assert contract["runtime_route"] in {"self_plan_dialogue", "self_plan"}
        assert "drzwi" not in final_text.lower()
        assert "zlecen" not in final_text.lower()
        assert "operacyjne" in final_text.lower() or "systemowe" in final_text.lower()
    finally:
        engine.shutdown()


def test_engine_process_turn_update_request_names_v1471_scope() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v1471_update.sqlite3")
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn(
            "Przygotuj teraz pełną wersję systemu Jaźni.",
            client_context={"client": "pytest", "lifecycle": "one_shot"},
        ).to_dict()
        body = envelope["final_visible_text"] or ""
        assert "v14.8.2.4" in body
        assert "test_v1471_dialogue_grounding_hotfix.py" in body
        assert "v14.6.2" not in body
    finally:
        engine.shutdown()
