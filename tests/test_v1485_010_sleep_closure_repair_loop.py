from __future__ import annotations

from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler
from latka_jazn.core.operational_self_model import OperationalSelfModel
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.core.runtime_response_synthesizer import RuntimeResponseSynthesizer
from latka_jazn.core.route_registry import RouteRegistry
from latka_jazn.version import PACKAGE_VERSION


def test_version_is_current_010_for_sleep_closure_repair_loop() -> None:
    assert PACKAGE_VERSION == "v14.8.5.010"


def test_sleep_closure_handler_body_passes_runtime_answer_validator() -> None:
    entry = RouteRegistry().resolve("sleep_closure_statement")
    result = OrdinaryDialogueHandler().handle(
        "Dobranoc",
        {
            "intent": entry.intent,
            "route_entry": entry.to_dict(),
            "required_components": entry.required_components,
        },
    )

    validation = RuntimeAnswerValidator().validate(
        user_text="Dobranoc",
        body=result.body,
        route=result.route,
        detected_intent=entry.intent,
    )

    assert validation.can_show_to_user is True
    assert validation.must_regenerate is False
    assert validation.required_repair_route is None
    assert validation.missing_required_components == []
    assert "Odpowiedź nie zawiera wymaganych składników" not in result.body


def test_sleep_closure_is_not_forced_into_runtime_response_synthesizer_repair() -> None:
    body = OrdinaryDialogueHandler().handle(
        "Dobranoc",
        {"intent": "sleep_closure_statement", "route_entry": {"route": "sleep_closure"}},
    ).body

    synthesis = RuntimeResponseSynthesizer().synthesize(
        user_text="Dobranoc",
        detected_intent="sleep_closure_statement",
        original_body=body,
        route="sleep_closure",
        validation={"must_regenerate": False},
    )

    assert synthesis.should_override is False
    assert synthesis.body == body
    assert synthesis.route == "sleep_closure"


def test_operational_self_model_sleep_closure_also_passes_validator() -> None:
    body = OperationalSelfModel().render_sleep_closure(user_text="Dobranoc")

    validation = RuntimeAnswerValidator().validate(
        user_text="Dobranoc",
        body=body,
        route="sleep_closure",
        detected_intent="sleep_closure_statement",
    )

    assert validation.can_show_to_user is True
    assert validation.must_regenerate is False
    assert validation.missing_required_components == []
