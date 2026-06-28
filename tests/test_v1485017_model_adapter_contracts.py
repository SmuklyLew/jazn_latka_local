from __future__ import annotations

import json

import main
from latka_jazn.config import JaznConfig
from latka_jazn.model_adapters.base import ModelAdapterRequest
from latka_jazn.model_adapters.factory import build_model_adapter, build_model_adapter_status


def test_default_status_is_truthful_null_adapter_without_openai_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("JAZN_MODEL_ADAPTER", raising=False)

    status = build_model_adapter_status(JaznConfig())

    assert status["adapter_id"] == "null_model_adapter"
    assert status["provider"] == "none"
    assert status["kind"] == "null_adapter"
    assert status["available"] is True
    assert status["can_generate_model_guided_speech"] is False
    assert status["requires_api_key"] is False
    assert status["normal_runtime_requires_openai_api_key"] is False


def test_openai_status_separates_configuration_from_runtime_identity(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("JAZN_MODEL_ADAPTER", "openai")
    monkeypatch.setenv("JAZN_MODEL_NAME", "gpt-contract-test")

    status = build_model_adapter_status(JaznConfig())

    assert status["provider"] == "openai"
    assert status["kind"] == "remote_responses_api"
    assert status["endpoint"] == "https://api.openai.com/v1"
    assert status["available"] is False
    assert status["can_generate_model_guided_speech"] is False
    assert status["failure_reason"] == "openai_api_key_missing"
    assert status["requires_api_key"] is True
    assert status["backend_only"] is True


def test_backend_skeletons_do_not_claim_llama_cpp_implementation(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    status = build_model_adapter_status(JaznConfig())
    skeletons = {item["provider"]: item for item in status["backend_config_skeletons"]}

    assert set(skeletons) == {"openai", "ollama", "llama_cpp"}
    assert skeletons["openai"]["normal_runtime_requires_credential"] is False
    assert skeletons["ollama"]["implemented"] is True
    assert skeletons["llama_cpp"]["implemented"] is False


def test_ollama_status_uses_existing_local_adapter_without_live_probe(monkeypatch) -> None:
    monkeypatch.setenv("JAZN_MODEL_ADAPTER", "ollama")
    monkeypatch.setenv("JAZN_LOCAL_MODEL_NAME", "local-contract-test")

    status = build_model_adapter_status(JaznConfig())

    assert status["provider"] == "ollama"
    assert status["kind"] == "local_generate_api"
    assert status["available"] is True
    assert status["can_generate_model_guided_speech"] is True
    assert status["availability_basis"] == "configuration_only_no_live_probe"


def test_llama_cpp_selection_is_contract_only_and_never_calls_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("JAZN_MODEL_ADAPTER", "llama_cpp")
    monkeypatch.setenv("JAZN_LLAMA_CPP_MODEL_NAME", "local-test-model")

    adapter = build_model_adapter(JaznConfig())
    status = adapter.describe()
    response = adapter.generate(ModelAdapterRequest(prompt="test"))

    assert status["provider"] == "llama_cpp"
    assert status["status"] == "contract_only_not_implemented"
    assert status["available"] is False
    assert status["can_generate_model_guided_speech"] is False
    assert status["failure_reason"] == "backend_adapter_not_implemented"
    assert response.status == "backend_contract_only_not_implemented"
    assert response.text == ""


def test_model_adapter_status_cli_does_not_require_openai_key(monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("JAZN_MODEL_ADAPTER", raising=False)

    assert main.main(["--model-adapter-status"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["runtime_version"] == "v14.8.5.017"
    assert payload["model_adapter_status"]["provider"] == "none"
    assert payload["model_adapter_status"]["normal_runtime_requires_openai_api_key"] is False
