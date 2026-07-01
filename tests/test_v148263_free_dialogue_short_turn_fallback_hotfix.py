from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier


BAD_SHORT_FALLBACK = "Zatrzymuję się przy tym zdaniu"


def intent(text: str) -> str:
    return DialogueIntentClassifier().classify(text).primary_intent


def assert_no_generic_short_fallback(text: str) -> None:
    assert BAD_SHORT_FALLBACK not in text
    assert "Doprecyzuj tylko kierunek" not in text
    assert "Powiedz mi, w którą stronę" not in text


def test_short_turn_intents_are_specific_enough_for_natural_chat():
    assert intent("Siemka.") == "casual_greeting"
    assert intent("Kiepska odpowiedź.") == "casual_feedback"
    assert intent("Ojoj!") == "expressive_reaction"


def test_ordinary_handler_does_not_repeat_generic_short_turn_fallbacks():
    handler = OrdinaryDialogueHandler()
    cases = [
        ("Siemka.", "casual_greeting", "Siemka"),
        ("Kiepska odpowiedź.", "casual_feedback", "kiepska odpowiedź"),
        ("Ojoj!", "expressive_reaction", "zgrzytnęło"),
    ]
    for user_text, detected_intent, expected in cases:
        result = handler.handle(user_text, {"intent": detected_intent, "route_entry": {"route": "ordinary_dialogue"}})
        assert expected.lower() in result.body.lower()
        assert_no_generic_short_fallback(result.body)


def test_validator_rejects_generic_short_turn_fallback_for_free_dialogue():
    validator = RuntimeAnswerValidator()
    for detected_intent in ("casual_greeting", "casual_feedback", "expressive_reaction", "short_free_dialogue"):
        validation = validator.validate(
            user_text="Siemka.",
            body="Jestem tutaj. Zatrzymuję się przy tym zdaniu i zostawiam mu chwilę miejsca. Powiedz mi, w którą stronę chcesz pójść dalej.",
            route="ordinary_dialogue",
            detected_intent=detected_intent,
        )
        assert validation.must_regenerate
        assert validation.mismatch_reason in {"ordinary_dialogue_meta_report_or_template", "generic_template_on_specific_request"}


def test_process_turn_short_chat_cases_disclose_missing_model_guided_speech():
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v148263_short_turn.sqlite3")
    engine = JaznEngine(cfg)
    try:
        for user_text in ("Siemka.", "Kiepska odpowiedź.", "Ojoj!"):
            envelope = engine.process_turn(user_text, client_context={"client": "pytest", "lifecycle": "one_shot"}).to_dict()
            final_text = envelope["final_visible_text"] or ""
            contract = envelope["final_response_contract"]
            assert contract["runtime_answer_quality"] == "fallback_or_debug"
            assert contract["fallback_classification"] == "cannot_answer_directly"
            assert contract["requires_host_model"] is True
            assert contract["can_generate_model_guided_speech"] is False
            assert contract["final_visible_integrity"]["valid"] is False
            assert "wymaga generacji przez host/model" in final_text
            assert_no_generic_short_fallback(final_text)
    finally:
        engine.shutdown()
