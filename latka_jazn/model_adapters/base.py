from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol
SCHEMA_VERSION="model_adapter_contract/v14.7.0"
@dataclass(slots=True)
class ModelAdapterRequest:
    prompt: str
    system_context: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
@dataclass(slots=True)
class ModelAdapterResponse:
    text: str
    provider: str
    model: str
    status: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    truth_boundary: str = "Model adapter jest kanałem generowania języka. Nie jest Jaźnią ani pamięcią źródłową."
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
class ModelAdapter(Protocol):
    name: str
    def generate(self, request: ModelAdapterRequest) -> ModelAdapterResponse: ...
