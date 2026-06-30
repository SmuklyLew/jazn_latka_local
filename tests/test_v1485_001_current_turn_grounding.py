from __future__ import annotations

from latka_jazn.core.current_turn_grounding import assess_current_turn_grounding
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.core.turn_context_resolver import TurnContextResolver


def test_turn_context_resolver_blocks_update_carryover_for_greeting() -> None:
    report = TurnContextResolver().resolve(
        current_user_text="Dzień dobry",
        previous_user_text="Przygotuj patch aktualizacji",
        previous_intent="system_update_execution_request",
        previous_route="system_update",
        time_gap_seconds=30,
    )
    assert not report.carryover_allowed
    assert report.forced_current_turn_only
    assert "previous_system_or_update_route" in report.risk_flags


def test_turn_context_resolver_allows_explicit_short_continuation() -> None:
    report = TurnContextResolver().resolve(
        current_user_text="zrób to",
        previous_user_text="Przygotuj audyt wersji",
        previous_intent="system_repair_plan_request",
        previous_route="system_repair_plan",
        explicit_previous_user_text=True,
        time_gap_seconds=5,
    )
    assert report.carryover_allowed
    assert report.previous_context_used


def test_current_turn_grounding_rejects_legacy_version_output_without_user_grounding() -> None:
    report = assess_current_turn_grounding(
        user_text="Co tam?",
        response_body="Aktualizacja v14.8.2.4 ma trzy rdzenie i pełny ZIP.",
        detected_intent="ordinary_conversation",
        route="ordinary_dialogue",
    )
    assert not report.valid
    assert "stale_version_output" in report.issues


def test_runtime_answer_validator_blocks_stale_update_template_in_ordinary_dialogue() -> None:
    validation = RuntimeAnswerValidator().validate(
        user_text="Co tam?",
        body="Ta aktualizacja ma trzy rdzenie i manifest i eksport.",
        route="ordinary_dialogue",
        detected_intent="ordinary_conversation",
    )
    assert validation.must_regenerate
    assert validation.current_turn_grounding
    assert validation.current_turn_grounding["valid"] is False


def test_current_turn_grounding_accepts_plain_greeting_reply() -> None:
    report = assess_current_turn_grounding(
        user_text="Cześć",
        response_body="Cześć, jestem tutaj. Jak Ci leci?",
        detected_intent="standalone_greeting",
        route="greeting",
    )
    assert report.valid
    assert report.quality == "topic_aligned"


def test_wake_after_reload_is_health_check_not_system_update() -> None:
    from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier

    report = DialogueIntentClassifier().classify(
        "Czas żebyś przeładowała Jaźń i się obudziła Łatko."
    )

    assert report.primary_intent == "runtime_health_check_after_update"
    assert report.update_request is False
    assert report.diagnostic_request is True


def test_current_turn_grounding_rejects_stale_v1485000_update_body() -> None:
    report = assess_current_turn_grounding(
        user_text="Przeładuj Jaźń i obudź się Łatko.",
        response_body="To jest zadanie wykonania aktualizacji v14.8.5.000 na pełnej paczce Jaźni.",
        detected_intent="runtime_health_check_after_update",
        route="runtime_health_check_after_update",
    )

    assert not report.valid
    assert "stale_version_output" in report.issues


def test_runtime_response_synthesizer_update_body_has_no_historical_v1485000() -> None:
    from latka_jazn.core.runtime_response_synthesizer import RuntimeResponseSynthesizer

    synthesis = RuntimeResponseSynthesizer().synthesize(
        user_text="Patch do wersji v14.8.5.026B.adapter-gpt-hotfix-v2",
        detected_intent="system_update_execution_request",
        original_body="",
        route="system_update",
        validation={"must_regenerate": True},
    )

    assert synthesis.should_override
    assert "v14.8.5.000" not in synthesis.body
    assert "JaznRuntimeSession.process_turn" in synthesis.body
