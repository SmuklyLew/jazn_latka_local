from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol
SCHEMA_VERSION = "model_adapter_contract/v14.8.5.030"


@dataclass(slots=True)
class AdapterStatusSnapshot:
    adapter_id: str
    provider: str
    configured: bool
    endpoint_reachable: bool | None
    probe_state: str
    last_probe_error: str | None = None
    can_attempt_model_guided_speech: bool = False
    can_generate_model_guided_speech: bool = False
    validated: bool = False
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ModelAdapterRequest:
    prompt: str
    system_context: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    instructions: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    truth_boundary: str = (
        "Request jest zbudowany przez runtime. Adapter nie jest źródłem tożsamości, "
        "pamięci, czasu ani prawdy Jaźni."
    )
    schema_version: str = SCHEMA_VERSION

    @property
    def input_text(self) -> str:
        return self.prompt

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ModelAdapterResponse:
    text: str
    provider: str
    model: str
    status: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    adapter_id: str = ""
    candidate_kind: str = "model_generated"
    source_origin: str = "model_adapter"
    endpoint_used: str | None = None
    status_snapshot: AdapterStatusSnapshot | None = None
    transport: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] | None = None
    generated: bool = False
    validated: bool = False
    truth_boundary: str = "Model adapter jest kanałem generowania języka. Nie jest Jaźnią ani pamięcią źródłową."
    schema_version: str = SCHEMA_VERSION
    def __post_init__(self) -> None:
        self.text = str(self.text or "").strip()
        self.generated = bool(self.generated or (self.status == "completed" and self.text))
        if not self.adapter_id:
            self.adapter_id = self.provider

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
class ModelAdapter(Protocol):
    name: str
    def generate(self, request: ModelAdapterRequest) -> ModelAdapterResponse: ...
