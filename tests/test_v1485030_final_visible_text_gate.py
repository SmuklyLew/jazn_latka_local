from latka_jazn.core.final_response_contract import FinalResponseContract
from latka_jazn.model_adapters.base import ModelAdapterResponse


def test_candidate_never_becomes_visible_without_acceptance() -> None:
    response = ModelAdapterResponse(text="Kandydat", provider="test", model="m", status="completed")
    assert FinalResponseContract.accepted_model_candidate_text(response, {"accepted": False}) == ""
    assert FinalResponseContract.accepted_model_candidate_text(response, {"accepted": True}) == "Kandydat"


def test_empty_candidate_never_becomes_visible() -> None:
    response = ModelAdapterResponse(text="", provider="test", model="m", status="completed")
    assert FinalResponseContract.accepted_model_candidate_text(response, {"accepted": True}) == ""
