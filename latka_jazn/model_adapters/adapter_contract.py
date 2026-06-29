from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from latka_jazn.version import schema_version

from .base import ModelAdapterRequest, ModelAdapterResponse


@dataclass(slots=True)
class AdapterContract:
    adapter_id: str
    provider: str
    kind: str
    available: bool
    model_name: str | None
    endpoint: str | None
    can_generate_model_guided_speech: bool
    truth_boundary: str
    failure_reason: str | None = None
    requires_api_key: bool = False
    availability_basis: str = "configuration_only_no_live_probe"
    backend_only: bool = True
    schema_version: str = schema_version("model_adapter_contract")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def describe_with_contract(*, contract: AdapterContract, legacy: dict[str, Any]) -> dict[str, Any]:
    payload = dict(legacy)
    contract_payload = contract.to_dict()
    payload.update(contract_payload)
    payload["adapter_contract"] = contract_payload
    return payload


def backend_config_skeletons(config: Any) -> list[dict[str, Any]]:
    return [
        {
            "adapter_id": "openai_responses_adapter",
            "provider": "openai",
            "kind": "remote_responses_api",
            "implemented": True,
            "selection": "JAZN_MODEL_ADAPTER=openai",
            "model_env": "JAZN_MODEL_NAME",
            "endpoint_env": "JAZN_MODEL_API_BASE",
            "credential_env": "OPENAI_API_KEY",
            "model_name": str(getattr(config, "model_name", "") or "") or None,
            "endpoint": str(getattr(config, "model_api_base", "") or "") or None,
            "normal_runtime_requires_credential": False,
        },
        {
            "adapter_id": "ollama_adapter",
            "provider": "ollama",
            "kind": "local_generate_api",
            "implemented": True,
            "selection": "JAZN_MODEL_ADAPTER=ollama",
            "model_env": "JAZN_LOCAL_MODEL_NAME",
            "endpoint_env": "JAZN_LOCAL_MODEL_API_BASE",
            "credential_env": None,
            "model_name": str(getattr(config, "local_model_name", "") or "") or None,
            "endpoint": str(getattr(config, "local_model_api_base", "") or "") or None,
            "normal_runtime_requires_credential": False,
        },
        {
            "adapter_id": "llama_cpp_contract_only",
            "provider": "llama_cpp",
            "kind": "openai_compatible_local_api_skeleton",
            "implemented": False,
            "selection": "JAZN_MODEL_ADAPTER=llama_cpp",
            "model_env": "JAZN_LLAMA_CPP_MODEL_NAME",
            "endpoint_env": "JAZN_LLAMA_CPP_API_BASE",
            "credential_env": None,
            "model_name": str(getattr(config, "llama_cpp_model_name", "") or "") or None,
            "endpoint": str(getattr(config, "llama_cpp_model_api_base", "") or "") or None,
            "normal_runtime_requires_credential": False,
        },
        {
            "adapter_id": "lmstudio_runtime_adapter",
            "provider": "lmstudio",
            "kind": "openai_compatible_local_api",
            "implemented": True,
            "selection": "JAZN_MODEL_ADAPTER=lmstudio",
            "model_env": "JAZN_LM_STUDIO_MODEL",
            "endpoint_env": "JAZN_LM_STUDIO_API_BASE",
            "credential_env": None,
            "model_name": str(getattr(config, "lm_studio_model_name", "") or "") or None,
            "endpoint": str(getattr(config, "lm_studio_api_base", "") or "") or None,
            "normal_runtime_requires_credential": False,
        },
        {
            "adapter_id": "codex_development_adapter",
            "provider": "codex",
            "kind": "development_tooling_status",
            "implemented": False,
            "selection": "JAZN_MODEL_ADAPTER=codex_development_adapter",
            "model_env": None,
            "endpoint_env": None,
            "credential_env": None,
            "model_name": None,
            "endpoint": None,
            "normal_runtime_requires_credential": False,
        },
    ]


class ContractOnlyModelAdapter:
    def __init__(
        self,
        *,
        provider: str,
        model: str,
        endpoint: str,
        adapter_id: str | None = None,
        kind: str = "openai_compatible_local_api_skeleton",
        failure_reason: str = "backend_adapter_not_implemented",
        response_status: str = "backend_contract_only_not_implemented",
        truth_boundary: str | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.endpoint = endpoint
        self.name = adapter_id or f"{provider}_contract_only"
        self.kind = kind
        self.failure_reason = failure_reason
        self.response_status = response_status
        self.truth_boundary = truth_boundary or (
            "This is only a backend configuration skeleton. Runtime does not call this endpoint "
            "and does not present the backend as Jazn identity or memory."
        )

    def describe(self) -> dict[str, Any]:
        contract = AdapterContract(
            adapter_id=self.name,
            provider=self.provider,
            kind=self.kind,
            available=False,
            model_name=self.model or None,
            endpoint=self.endpoint or None,
            can_generate_model_guided_speech=False,
            failure_reason=self.failure_reason,
            truth_boundary=self.truth_boundary,
        )
        return describe_with_contract(
            contract=contract,
            legacy={
                "name": self.name,
                "status": "contract_only_not_implemented",
                "model": self.model or "not_configured",
                "api_base": self.endpoint,
            },
        )

    def generate(self, request: ModelAdapterRequest) -> ModelAdapterResponse:
        return ModelAdapterResponse(
            text="",
            provider=self.provider,
            model=self.model or "not_configured",
            status=self.response_status,
        )
