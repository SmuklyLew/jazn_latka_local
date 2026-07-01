from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.model_adapters.base import ModelAdapterResponse


def _response(text: str) -> ModelAdapterResponse:
    return ModelAdapterResponse(text=text, provider="test", model="m", status="completed")


def test_empty_model_output_is_rejected() -> None:
    result = RuntimeAnswerValidator().validate_model_candidate(
        user_text="Hej", response=_response(""), route="ordinary_dialogue", detected_intent="casual_greeting"
    )
    assert result.accepted is False
    assert result.mismatch_reason == "empty_model_candidate"


def test_template_like_model_output_is_rejected() -> None:
    result = RuntimeAnswerValidator().validate_model_candidate(
        user_text="Hej",
        response=_response("Jestem przy Tobie."),
        route="ordinary_dialogue",
        detected_intent="casual_greeting",
        template_origin={"template_id": "tpl_presence"},
    )
    assert result.accepted is False
    assert result.mismatch_reason == "template_like_model_candidate"
