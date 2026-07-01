from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from latka_jazn.version import schema_version


@dataclass(slots=True)
class RuntimeTurnContract:
    """One truth-bearing contract shared by every visible turn entry point."""

    turn_id: str
    trace_id: str
    detected_intent: str
    route: str
    handler_name: str
    runtime_exact_text: str
    final_visible_text: str
    host_interpretation: str | None
    template_origin: dict[str, Any]
    source_origin_detail: str
    fallback_classification: str
    final_visible_integrity: dict[str, Any]
    can_generate_model_guided_speech: bool
    requires_host_model: bool
    response_generation_mode: str
    validation: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    retry_limit: int = 1
    schema_version: str = schema_version("runtime_turn_contract")
    truth_boundary: str = (
        "Kontrakt rozdziela tekst runtime, tekst widoczny i ewentualną interpretację hosta. "
        "Szablon, handler regułowy, repair i degraded fallback nie są dynamiczną wypowiedzią model-guided."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
