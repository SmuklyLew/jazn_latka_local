from latka_jazn.model_adapters.openai_compatible_local_adapter import OpenAICompatibleLocalAdapter


def test_probe_fail_never_claims_generation(monkeypatch) -> None:
    adapter = OpenAICompatibleLocalAdapter(model="m", api_base="http://127.0.0.1:9/v1")
    monkeypatch.setattr(adapter, "_post_json", lambda endpoint, payload: (_ for _ in ()).throw(OSError("offline")))
    snapshot = adapter.probe()
    assert snapshot.probe_state == "probed_fail"
    assert snapshot.endpoint_reachable is False
    assert snapshot.can_generate_model_guided_speech is False


def test_probe_success_confirms_generation_capability(monkeypatch) -> None:
    adapter = OpenAICompatibleLocalAdapter(model="m")
    monkeypatch.setattr(adapter, "_post_json", lambda endpoint, payload: {"output_text": "OK"})
    snapshot = adapter.probe()
    assert snapshot.probe_state == "probed_ok"
    assert snapshot.can_generate_model_guided_speech is True
