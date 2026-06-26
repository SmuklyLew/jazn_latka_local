from __future__ import annotations

from typing import Any

from .null_model_adapter import NullModelAdapter
from .openai_responses_adapter import OpenaiResponsesAdapter
from .local_llm_adapter import LocalLlmAdapter


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
    return NullModelAdapter()
