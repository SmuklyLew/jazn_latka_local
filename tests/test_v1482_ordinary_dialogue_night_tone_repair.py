from __future__ import annotations

from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.core.runtime_response_synthesizer import RuntimeResponseSynthesizer
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier


_BAD_META_BODY = "Jestem przy tej wiadomości. Nie będę dopowiadała diagnostyki ani starej pamięci bez powodu; odpowiadam z bieżącego sensu rozmowy."


def test_atmospheric_night_greeting_gets_conversational_body_not_meta_template():
    result = OrdinaryDialogueHandler().handle(
        "Witaj w tej mrocznej nocy.",
        {"intent": "ordinary_conversation", "route_entry": {"route": "ordinary_dialogue"}},
    )
    assert "mroczna noc" in result.body.lower()
    assert "Co dziś niesie ta noc" in result.body
    assert "Jestem przy tej wiadomości" not in result.body
    assert "bieżącego sensu rozmowy" not in result.body


def test_validator_rejects_current_turn_meta_template_for_ordinary_dialogue():
    validation = RuntimeAnswerValidator().validate(
        user_text="Witaj w tej mrocznej nocy.",
        body=_BAD_META_BODY,
        route="ordinary_dialogue",
        detected_intent="ordinary_conversation",
    )
    assert validation.must_regenerate
    assert validation.repair_body is None
    assert validation.mismatch_reason == "ordinary_dialogue_meta_report_or_template"


def test_runtime_synthesizer_replaces_meta_template_with_night_reply():
    validation = RuntimeAnswerValidator().validate(
        user_text="Witaj w tej mrocznej nocy.",
        body=_BAD_META_BODY,
        route="ordinary_dialogue",
        detected_intent="ordinary_conversation",
    )
    synthesis = RuntimeResponseSynthesizer().synthesize(
        user_text="Witaj w tej mrocznej nocy.",
        detected_intent="ordinary_conversation",
        original_body=_BAD_META_BODY,
        route="ordinary_dialogue",
        validation=validation.to_dict(),
    )
    assert synthesis.should_override
    assert "mroczna noc" in synthesis.body.lower()
    assert "Jestem przy tej wiadomości" not in synthesis.body


def test_night_greeting_may_remain_ordinary_but_must_not_be_lost():
    report = DialogueIntentClassifier().classify("Witaj w tej mrocznej nocy.")
    assert report.primary_intent in {"ordinary_conversation", "standalone_greeting"}
    assert report.normalized_text == "witaj w tej mrocznej nocy."
