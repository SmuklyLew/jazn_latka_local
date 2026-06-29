from __future__ import annotations

import json
import os

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


def test_chatgpt_runtime_adapter_status_is_not_null_and_does_not_claim_local_generation(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("JAZN_MODEL_ADAPTER", "chatgpt_runtime_adapter")
    monkeypatch.setenv("JAZN_MODEL_NAME", "chatgpt-host-test")

    status = build_model_adapter_status(JaznConfig())
    response = build_model_adapter(JaznConfig()).generate(ModelAdapterRequest(prompt="test"))

    assert status["adapter_id"] == "chatgpt_runtime_adapter"
    assert status["provider"] == "chatgpt_host"
    assert status["kind"] == "hosted_chatgpt_bridge"
    assert status["status"] == "host_bridge_available"
    assert status["available"] is True
    assert status["model"] == "chatgpt-host-test"
    assert status["can_generate_model_guided_speech"] is False
    assert status["requires_api_key"] is False
    assert response.status == "requires_host_chatgpt_visible_response"
    assert response.text == ""


def test_model_adapter_status_cli_respects_chat_gpt_bridge(monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("JAZN_MODEL_ADAPTER", raising=False)
    monkeypatch.delenv("JAZN_MODEL_NAME", raising=False)

    assert main.main(["--chat-gpt", "--model-adapter-status"]) == 0
    payload = json.loads(capsys.readouterr().out)

    status = payload["model_adapter_status"]
    assert status["adapter_id"] == "chatgpt_runtime_adapter"
    assert status["provider"] == "chatgpt_host"
    assert status["status"] == "host_bridge_available"
    assert status["selected_adapter"] == "chatgpt_runtime_adapter"
    assert status["model"] == "chatgpt_host_model"
    assert status["requires_api_key"] is False
    assert status["can_generate_model_guided_speech"] is False


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

    assert set(skeletons) == {"openai", "ollama", "llama_cpp", "lmstudio", "codex"}
    assert skeletons["openai"]["normal_runtime_requires_credential"] is False
    assert skeletons["ollama"]["implemented"] is True
    assert skeletons["llama_cpp"]["implemented"] is False
    assert skeletons["lmstudio"]["implemented"] is False
    assert skeletons["lmstudio"]["credential_env"] is None
    assert skeletons["codex"]["kind"] == "development_tooling_status"


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


def test_lmstudio_selection_is_contract_only_and_never_uses_ollama(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("JAZN_MODEL_ADAPTER", "lmstudio")
    monkeypatch.setenv("JAZN_LM_STUDIO_MODEL", "local-lmstudio-test")

    adapter = build_model_adapter(JaznConfig())
    status = adapter.describe()
    response = adapter.generate(ModelAdapterRequest(prompt="test"))

    assert status["adapter_id"] == "lmstudio_runtime_adapter"
    assert status["provider"] == "lmstudio"
    assert status["status"] == "contract_only_not_implemented"
    assert status["available"] is False
    assert status["can_generate_model_guided_speech"] is False
    assert status["requires_api_key"] is False
    assert status["failure_reason"] == "lmstudio_adapter_not_implemented"
    assert response.status == "lmstudio_adapter_not_implemented"
    assert response.text == ""


def test_codex_development_adapter_is_not_speech_adapter(monkeypatch) -> None:
    monkeypatch.setenv("JAZN_MODEL_ADAPTER", "codex_development_adapter")

    status = build_model_adapter_status(JaznConfig())

    assert status["adapter_id"] == "codex_development_adapter"
    assert status["provider"] == "codex"
    assert status["kind"] == "development_tooling_status"
    assert status["can_generate_model_guided_speech"] is False
    assert status["failure_reason"] == "codex_not_speech_adapter"


def test_model_adapter_status_cli_does_not_require_openai_key(monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("JAZN_MODEL_ADAPTER", raising=False)
    monkeypatch.delenv("JAZN_VISIBLE_CHANNEL", raising=False)
    monkeypatch.delenv("JAZN_HOST_RUNTIME", raising=False)
    monkeypatch.delenv("JUPYTER_SERVER_OAI_PATH", raising=False)
    monkeypatch.delenv("JAZN_ASSUME_CHATGPT_HOST", raising=False)
    for key in list(os.environ):
        if key.startswith("CUA_DD_"):
            monkeypatch.delenv(key, raising=False)

    assert main.main(["--model-adapter-status"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["runtime_version"] == "v14.8.5.021a"
    assert payload["model_adapter_status"]["provider"] == "none"
    assert payload["model_adapter_status"]["selected_backend_adapter"] == "null_model_adapter"
    assert payload["model_adapter_status"]["effective_runtime_adapter"] == "null_model_adapter"
    assert payload["model_adapter_status"]["normal_runtime_requires_openai_api_key"] is False
