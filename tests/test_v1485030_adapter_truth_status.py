from latka_jazn.model_adapters.lmstudio_runtime_adapter import LmStudioRuntimeAdapter
from latka_jazn.model_adapters.openai_responses_adapter import OpenaiResponsesAdapter


def test_configured_without_probe_can_attempt_but_cannot_generate() -> None:
    status = LmStudioRuntimeAdapter(model="local-model").describe()
    assert status["configured"] is True
    assert status["can_attempt_model_guided_speech"] is True
    assert status["can_generate_model_guided_speech"] is False
    assert status["probe_state"] == "not_probed"
    assert "available" in status


def test_openai_key_is_configuration_not_generation_proof() -> None:
    status = OpenaiResponsesAdapter(api_key="test-key", model="test-model").describe()
    assert status["configured"] is True
    assert status["can_attempt_model_guided_speech"] is True
    assert status["can_generate_model_guided_speech"] is False
