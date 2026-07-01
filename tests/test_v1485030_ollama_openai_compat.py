from latka_jazn.model_adapters.base import ModelAdapterRequest
from latka_jazn.model_adapters.openai_compatible_local_adapter import OpenAICompatibleLocalAdapter


def test_ollama_uses_openai_compatible_routes_with_native_fallback(monkeypatch) -> None:
    adapter = OpenAICompatibleLocalAdapter(model="qwen", provider="ollama", api_base="http://127.0.0.1:11434/v1")
    calls = []

    def fake_post(endpoint, payload):
        calls.append(endpoint)
        if endpoint != "/api/generate":
            raise OSError("unsupported")
        return {"response": "OK"}

    monkeypatch.setattr(adapter, "_post_json", fake_post)
    response = adapter.generate(ModelAdapterRequest(prompt="test"))
    assert response.text == "OK"
    assert response.endpoint_used == "/api/generate"
    assert calls == ["/responses", "/chat/completions", "/api/generate"]
