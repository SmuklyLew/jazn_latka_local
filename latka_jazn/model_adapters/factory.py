from __future__ import annotations

from typing import Any
import copy

from .null_model_adapter import NullModelAdapter
from .chatgpt_runtime_adapter import ChatgptRuntimeAdapter
from .terminal_runtime_adapter import TerminalRuntimeAdapter
from .openai_responses_adapter import OpenaiResponsesAdapter
from .local_llm_adapter import LocalLlmAdapter
from .adapter_contract import ContractOnlyModelAdapter, backend_config_skeletons
from latka_jazn.core.runtime_environment import apply_effective_runtime_adapter, detect_runtime_environment


def build_model_adapter(config: Any):
    name = str(getattr(config, "model_adapter", "null") or "null").strip().lower()
    if name in {"chatgpt", "chatgpt_runtime", "chatgpt_runtime_adapter", "chat_gpt", "chat-gpt"}:
        return ChatgptRuntimeAdapter(
            model=str(getattr(config, "model_name", "chatgpt_host_model") or "chatgpt_host_model"),
            root=getattr(config, "root", None),
        )
    if name in {"chat", "terminal", "terminal_runtime", "terminal_runtime_adapter", "local_terminal", "chat_loop"}:
        return TerminalRuntimeAdapter(
            model=str(getattr(config, "terminal_model_name", "terminal_visible_layer") or "terminal_visible_layer"),
            root=getattr(config, "root", None),
        )
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



def _environment_availability_basis(environment: Any) -> str | None:
    if not getattr(environment, "visible_channel_adapter", None):
        return None
    basis = list(getattr(environment, "detection_basis", []) or [])
    first = str(basis[0] if basis else "").strip()
    if first == "explicit_command:--chat-gpt":
        return "explicit_chat_gpt_bridge_command"
    if first == "explicit_command:--chat-gpt-final-only":
        return "explicit_chat_gpt_final_only_command"
    if first == "explicit_command:--chat":
        return "explicit_chat_terminal_command"
    if first == "explicit_command:--chat-open-ai":
        return "explicit_openai_api_bridge_command"
    if first == "detected_openai_chatgpt_tool_container":
        return "detected_openai_chatgpt_tool_container"
    if first.startswith("env:"):
        return "environment_visible_channel_marker"
    if first == "config.model_adapter":
        return "configured_model_adapter"
    return first or None


def _apply_environment_basis(payload: dict[str, Any], environment: Any) -> dict[str, Any]:
    availability_basis = _environment_availability_basis(environment)
    if not availability_basis:
        return payload
    payload = dict(payload)
    payload["availability_basis"] = availability_basis
    contract = payload.get("adapter_contract")
    if isinstance(contract, dict):
        contract = dict(contract)
        contract["availability_basis"] = availability_basis
        payload["adapter_contract"] = contract
    return payload

def build_model_adapter_status(
    config: Any,
    *,
    command: str | None = None,
    infer_host_environment: bool = False,
) -> dict[str, Any]:
    environment = detect_runtime_environment(
        config,
        command=command,
        infer_host_environment=infer_host_environment,
    )
    base_status = build_model_adapter(config).describe()
    effective_config = apply_effective_runtime_adapter(copy.copy(config), environment)
    active = _apply_environment_basis(build_model_adapter(effective_config).describe(), environment)
    payload = {
        **active,
        "selected_adapter": environment.effective_runtime_adapter,
        "selected_backend_adapter": environment.selected_backend_adapter,
        "visible_channel_adapter": environment.visible_channel_adapter,
        "effective_runtime_adapter": environment.effective_runtime_adapter,
        "runtime_environment": environment.to_dict(),
        "backend_config_skeletons": backend_config_skeletons(config),
        "normal_runtime_requires_openai_api_key": False,
        "truth_boundary_summary": (
            "Adapter jest backendem językowym, nie tożsamością Jaźni. OPENAI_API_KEY jest wymagany wyłącznie "
            "dla jawnie wybranego backendu OpenAI, nie dla null adaptera, --chat-gpt ani --runtime-preview. "
            "selected_backend_adapter pokazuje bazową konfigurację, a effective_runtime_adapter widzialny kanał tej komendy/środowiska."
        ),
    }
    if environment.effective_runtime_adapter != environment.selected_backend_adapter:
        payload["base_backend_adapter_status"] = base_status
    return payload
