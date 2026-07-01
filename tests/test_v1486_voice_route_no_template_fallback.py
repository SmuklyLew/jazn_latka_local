from __future__ import annotations

from pathlib import Path

import pytest

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.template_registry import TemplateRegistry
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier


ROOT = Path(__file__).resolve().parents[1]
SPEECH_CASES = (
    "Hej.",
    "No trochę kiepsko, jak widzę wiadomość z szablonu, a nie własną wypowiedź... 😭😱😷🤢",
    "Cześć Łatko, jak się czujesz?",
    "Co tam słychać?",
    "Chcę rozmawiać bezpośrednio z Łatką.",
)
SOURCE_CASES = (
    "Czy to była odpowiedź runtime czy szablon?",
    "Pokaż source_origin tej odpowiedzi.",
)
FORBIDDEN_GENERIC_PHRASES = (
    "jestem przy tobie",
    "jestem obok w tej turze",
    "możemy spokojnie",
    "zostaję przy tym, co piszesz",
    "odpowiadam z bieżącej wiadomości",
)


@pytest.fixture(scope="module")
def engine() -> JaznEngine:
    instance = JaznEngine(
        JaznConfig(
            root=ROOT,
            network_time_first=False,
            memory_db_name="workspace_runtime/test_v1486_voice_truth_gate.sqlite3",
        )
    )
    try:
        yield instance
    finally:
        instance.shutdown()


def test_classifier_routes_source_origin_questions_to_diagnostics() -> None:
    classifier = DialogueIntentClassifier()
    for text in SOURCE_CASES:
        assert classifier.classify(text).primary_intent == "runtime_source_question"


def test_template_registry_detects_soft_presence_templates() -> None:
    registry = TemplateRegistry(ROOT)
    for phrase in FORBIDDEN_GENERIC_PHRASES:
        origin = registry.classify_body(phrase, detected_intent="ordinary_conversation")
        assert origin["template_id"]


def test_null_adapter_never_presents_rule_text_as_dynamic_latka_speech(engine: JaznEngine) -> None:
    for text in SPEECH_CASES:
        envelope = engine.process_turn(
            text,
            client_context={"client": "pytest", "lifecycle": "one_shot", "no_carryover": True},
        ).to_dict()
        contract = envelope["final_response_contract"]
        turn = envelope["runtime_turn_contract"]
        visible = envelope["final_visible_text"].lower()

        assert contract["can_generate_model_guided_speech"] is False
        assert contract["requires_host_model"] is True
        assert contract["fallback_classification"] == "cannot_answer_directly"
        assert contract["template_origin"]["template_id"] == "tpl_requires_model_guided_speech"
        assert contract["final_visible_integrity"]["valid"] is False
        assert contract["final_visible_integrity"]["origin_truth_valid"] is False
        assert turn["runtime_exact_text"] == contract["runtime_exact_text"]
        assert turn["final_visible_text"] == envelope["final_visible_text"]
        assert turn["fallback_classification"] == "cannot_answer_directly"
        assert turn["source_origin_detail"] == "runtime_turn_truth_gate/model_guided_speech_unavailable"
        assert turn["retry_count"] <= turn["retry_limit"] == 1
        assert "wymaga generacji przez host/model" in visible
        assert all(phrase not in visible for phrase in FORBIDDEN_GENERIC_PHRASES)


def test_source_diagnostic_is_classified_and_carries_origin_ledger(engine: JaznEngine) -> None:
    for text in SOURCE_CASES:
        envelope = engine.process_turn(
            text,
            client_context={"client": "pytest", "lifecycle": "one_shot", "no_carryover": True},
        ).to_dict()
        contract = envelope["final_response_contract"]
        turn = envelope["runtime_turn_contract"]
        ledger = envelope["cognitive_frame"]["source_origin_ledger_entry"]

        assert contract["detected_user_intent"] == "runtime_source_question"
        assert contract["fallback_classification"] != "not_fallback"
        assert contract["source_origin_detail"]
        assert contract["final_visible_integrity"]["valid"] is False
        assert turn["runtime_exact_text"]
        assert turn["host_interpretation"] is None
        assert ledger["fallback_classification"] == contract["fallback_classification"]
        assert ledger["source_origin_detail"]
        assert ledger["final_visible_integrity_valid"] is False
