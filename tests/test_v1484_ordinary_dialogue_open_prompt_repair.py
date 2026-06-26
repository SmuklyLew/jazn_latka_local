from __future__ import annotations

from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator


OVERUSED_REPAIR_BODY = "Jestem przy tym — bez dokładania raportu i bez losowej pamięci. Możemy pójść dalej zwykłą rozmową."


def assert_not_overused_repair(text: str) -> None:
    low = (text or "").lower()
    assert "jestem przy tym — bez dokładania raportu" not in low
    assert "bez losowej pamięci" not in low
    assert "możemy pójść dalej zwykłą rozmową" not in low


def test_open_ended_talk_request_gets_actual_micro_story():
    result = OrdinaryDialogueHandler().handle(
        "Opowiedz coś.",
        {"intent": "short_free_dialogue", "body": "", "route_entry": {"route": "ordinary_dialogue"}},
    )
    assert_not_overused_repair(result.body)
    assert "opowiem" in result.body.lower()
    assert "wyobraź" in result.body.lower() or "wyobraz" in result.body.lower()


def test_short_disappointment_does_not_repeat_overused_repair():
    result = OrdinaryDialogueHandler().handle(
        "I tyle.",
        {"intent": "short_free_dialogue", "body": "", "route_entry": {"route": "ordinary_dialogue"}},
    )
    assert_not_overused_repair(result.body)
    assert "za mało" in result.body.lower() or "za malo" in result.body.lower()
    assert "poprawiam" in result.body.lower()


def test_validator_rejects_overused_repair_for_short_free_dialogue():
    validation = RuntimeAnswerValidator().validate(
        user_text="Opowiedz coś.",
        body=OVERUSED_REPAIR_BODY,
        route="ordinary_dialogue",
        detected_intent="short_free_dialogue",
    )
    assert validation.must_regenerate
    assert validation.mismatch_reason == "generic_template_on_specific_request"
