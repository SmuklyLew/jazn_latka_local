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
    ]


class ContractOnlyModelAdapter:
    def __init__(self, *, provider: str, model: str, endpoint: str) -> None:
        self.provider = provider
        self.model = model
        self.endpoint = endpoint
        self.name = f"{provider}_contract_only"

    def describe(self) -> dict[str, Any]:
        contract = AdapterContract(
            adapter_id=self.name,
            provider=self.provider,
            kind="openai_compatible_local_api_skeleton",
            available=False,
            model_name=self.model or None,
            endpoint=self.endpoint or None,
            can_generate_model_guided_speech=False,
            failure_reason="backend_adapter_not_implemented",
            truth_boundary=(
                "To jest wyłącznie szkielet konfiguracji backendu. Runtime nie wykonuje żądań do tego endpointu "
                "i nie przedstawia backendu jako tożsamości ani pamięci Jaźni."
            ),
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
            status="backend_contract_only_not_implemented",
        )
