from latka_jazn.core.handlers.runtime_source_handler import RuntimeSourceHandler
from latka_jazn.core.handlers.system_repair_plan_handler import SystemRepairPlanHandler
from latka_jazn.core.route_registry import RouteRegistry
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.core.runtime_response_synthesizer import RuntimeResponseSynthesizer


def test_literal_required_component_names_satisfy_validator():
    entry = RouteRegistry().resolve("system_repair_plan_request")
    result = SystemRepairPlanHandler().handle(
        "Sprawdź wszystko i napraw system.",
        {"intent": "system_repair_plan_request", "required_components": entry.required_components},
    )
    validation = RuntimeAnswerValidator().validate(
        user_text="Sprawdź wszystko i napraw system.",
        body=result.body,
        route=result.route,
        detected_intent="system_repair_plan_request",
    )
    assert validation.must_regenerate is False
    assert validation.missing_required_components == []


def test_runtime_exact_quote_uses_previous_checkpoint_and_survives_synthesis():
    entry = RouteRegistry().resolve("runtime_exact_quote_request")
    previous_runtime_text = "[czas]\nTo mnie cieszy. Ten krok zadziałał."
    result = RuntimeSourceHandler().handle(
        "Co dokładnie odpowiedział runtime?",
        {
            "intent": "runtime_exact_quote_request",
            "required_components": entry.required_components,
            "last_turn": {
                "runtime_text": previous_runtime_text,
                "visible_text": previous_runtime_text,
                "template_origin": {"template_id": "positive_feedback"},
                "source_origin": {
                    "handler_name": "OrdinaryDialogueHandler",
                    "route": "ordinary_dialogue",
                    "forbidden_legacy_routes": ["correction_acknowledged", "positive_continuation"],
                },
            },
        },
    )
    validation = RuntimeAnswerValidator().validate(
        user_text="Co dokładnie odpowiedział runtime?",
        body=result.body,
        route=result.route,
        detected_intent="runtime_exact_quote_request",
    )
    synthesis = RuntimeResponseSynthesizer().synthesize(
        user_text="Co dokładnie odpowiedział runtime?",
        detected_intent="runtime_exact_quote_request",
        original_body=result.body,
        route=result.route,
        validation=validation.to_dict(),
    )
    assert previous_runtime_text in result.body
    assert validation.must_regenerate is False
    assert synthesis.should_override is False
    assert synthesis.body == result.body
