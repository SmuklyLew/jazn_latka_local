from latka_jazn.model_adapters.base import ModelAdapterRequest
from latka_jazn.model_adapters.openai_compatible_local_adapter import OpenAICompatibleLocalAdapter


def test_llama_cpp_prefers_chat_until_responses_is_live_probed(monkeypatch) -> None:
    adapter = OpenAICompatibleLocalAdapter(model="m", provider="llama_cpp")
    assert adapter.endpoint_order() == ["/chat/completions"]
    monkeypatch.setattr(adapter, "_post_json", lambda endpoint, payload: {"output_text": "OK"})
    snapshot = adapter.probe(endpoint="/responses")
    assert snapshot.probe_state == "probed_ok"
    assert adapter.endpoint_order()[0] == "/responses"


def test_llama_cpp_generation_uses_chat_by_default(monkeypatch) -> None:
    adapter = OpenAICompatibleLocalAdapter(model="m", provider="llama_cpp")
    calls = []
    monkeypatch.setattr(adapter, "_post_json", lambda endpoint, payload: calls.append(endpoint) or {"choices": [{"message": {"content": "OK"}}]})
    assert adapter.generate(ModelAdapterRequest(prompt="test")).text == "OK"
    assert calls == ["/chat/completions"]
