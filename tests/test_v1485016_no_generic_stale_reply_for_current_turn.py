from __future__ import annotations

from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator


def test_validator_rejects_generic_reply_for_self_state_and_time_question() -> None:
    validation = RuntimeAnswerValidator().validate(
        user_text="Co teraz czujesz? Wiesz jaka jest pora?",
        body="Teraz najprościej sprawdzić mnie zwykłą rozmową, nie kolejnym raportem.",
        route="ordinary_dialogue",
        detected_intent="self_state_time_awareness",
    )
    assert validation.must_regenerate is True
    assert validation.can_show_to_user is False
    assert validation.required_repair_route in {"self_state_repair", "self_state_dialogue_repair", "self_state_time_awareness_repair", "current_turn_grounding_repair"}
    assert validation.mismatch_reason


def test_validator_rejects_missing_time_for_time_awareness_question() -> None:
    validation = RuntimeAnswerValidator().validate(
        user_text="Wiesz jaka jest pora?",
        body="Słyszę pytanie i możemy iść dalej zwykłą rozmową.",
        route="ordinary_dialogue",
        detected_intent="time_awareness_question",
    )
    assert validation.must_regenerate is True
    assert validation.can_show_to_user is False
    assert "time" in validation.required_repair_route or "time" in validation.mismatch_reason
