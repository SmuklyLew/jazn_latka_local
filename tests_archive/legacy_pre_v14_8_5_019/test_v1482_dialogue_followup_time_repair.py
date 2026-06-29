from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler


@dataclass(slots=True)
class _Sample:
    source: str = "unit_test_clock"
    trusted: bool = False


class _Clock:
    def now(self, network_first: bool = True):
        return _Sample()

    def header(self, sample) -> str:
        return "[🕒 2026-06-04 22:45:07 GMT+2, czwartek, Europe/Warsaw]"


def test_time_question_has_own_intent_even_with_typo_or_correction():
    clf = DialogueIntentClassifier()
    assert clf.classify("która jest godzina?").primary_intent == "current_time_question"
    assert clf.classify("Która jest godzina? Poprawiłem się.").primary_intent == "current_time_question"


def test_memory_followup_and_2025_scope_do_not_become_ordinary_dialogue():
    clf = DialogueIntentClassifier()
    assert clf.classify("A jakieś przeżycia?", previous_text="Ok. To co pamiętasz z 2025 roku?").primary_intent == "memory_experience_question"
    assert clf.classify("Ale z całego 2025 roku.", previous_text="Czy masz jakieś mocne/ważne wspomnienie?").primary_intent == "memory_experience_question"


def test_time_handler_answers_clock_not_template():
    result = OrdinaryDialogueHandler().handle(
        "Która jest godzina? Poprawiłem się.",
        {"intent": "current_time_question", "clock": _Clock(), "route_entry": {"route": "current_time"}},
    )
    assert "2026-06-04 22:45:07" in result.body
    assert "Słyszę. Spróbuję" not in result.body
    assert "Źródło czasu" in result.body
