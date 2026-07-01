from latka_jazn.model_adapters.base import ModelAdapterRequest
from latka_jazn.model_adapters.lmstudio_runtime_adapter import LmStudioRuntimeAdapter


def test_lmstudio_prefers_responses_and_confirms_after_success(monkeypatch) -> None:
    adapter = LmStudioRuntimeAdapter(model="m")
    calls = []
    monkeypatch.setattr(adapter, "_post_json", lambda endpoint, payload: calls.append(endpoint) or {"output_text": "OK"})
    before = adapter.describe()
    response = adapter.generate(ModelAdapterRequest(prompt="test"))
    after = adapter.describe()
    assert before["can_generate_model_guided_speech"] is False
    assert response.endpoint_used == "/responses"
    assert calls == ["/responses"]
    assert after["can_generate_model_guided_speech"] is True
