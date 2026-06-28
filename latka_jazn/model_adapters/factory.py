from __future__ import annotations

from typing import Any

from .null_model_adapter import NullModelAdapter
from .openai_responses_adapter import OpenaiResponsesAdapter
from .local_llm_adapter import LocalLlmAdapter
from .adapter_contract import ContractOnlyModelAdapter, backend_config_skeletons


def build_model_adapter(config: Any):
    name = str(getattr(config, "model_adapter", "null") or "null").strip().lower()
    if name in {"openai", "openai_responses", "openai_responses_adapter"} and bool(getattr(config, "allow_network", True)):
        return OpenaiResponsesAdapter(
            model=str(getattr(config, "model_name", "gpt-5.2")),
            api_base=str(getattr(config, "model_api_base", "https://api.openai.com/v1")),
            timeout_seconds=float(getattr(config, "model_timeout_seconds", 45.0)),
            max_output_tokens=int(getattr(config, "model_max_output_tokens", 800)),
            root=getattr(config, "root", None),
        )
    if name in {"local", "ollama", "local_llm", "local_llm_adapter"}:
        return LocalLlmAdapter(
            model=str(getattr(config, "local_model_name", "")),
            api_base=str(getattr(config, "local_model_api_base", "http://127.0.0.1:11434")),
            timeout_seconds=float(getattr(config, "model_timeout_seconds", 45.0)),
            max_output_tokens=int(getattr(config, "model_max_output_tokens", 800)),
            root=getattr(config, "root", None),
        )
    if name in {"llama_cpp", "llamacpp", "llama.cpp"}:
        return ContractOnlyModelAdapter(
            provider="llama_cpp",
            model=str(getattr(config, "llama_cpp_model_name", "")),
            endpoint=str(getattr(config, "llama_cpp_model_api_base", "http://127.0.0.1:8080/v1")),
        )
    return NullModelAdapter()


def build_model_adapter_status(config: Any) -> dict[str, Any]:
    active = build_model_adapter(config).describe()
    return {
        **active,
        "selected_adapter": str(getattr(config, "model_adapter", "null") or "null"),
        "backend_config_skeletons": backend_config_skeletons(config),
        "normal_runtime_requires_openai_api_key": False,
        "truth_boundary_summary": (
            "Adapter jest backendem językowym, nie tożsamością Jaźni. OPENAI_API_KEY jest wymagany wyłącznie "
            "dla jawnie wybranego backendu OpenAI, nie dla null adaptera, --chat-gpt ani --runtime-preview."
        ),
    }
