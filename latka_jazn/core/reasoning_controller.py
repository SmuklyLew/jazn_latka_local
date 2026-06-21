from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "reasoning_controller/v14.8.2.4"

@dataclass(slots=True)
class ReasoningDecision:
    decision: str
    reason: str
    repair_hint: str | None = None
    blocks_final: bool = False
    schema_version: str = SCHEMA_VERSION
    details: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]: return asdict(self)

class ReasoningController:
    def assess_turn(self, *, user_text: str, intent: str, route: str, handler_name: str, body: str, policy: dict[str, Any] | None = None, logic_audit: dict[str, Any] | None = None, validation: dict[str, Any] | None = None) -> ReasoningDecision:
        policy = policy or {}
        logic_audit = logic_audit or {}
        validation = validation or {}
        if logic_audit.get("must_regenerate"):
            return ReasoningDecision("regenerate", "turn_logic_audit_failed", logic_audit.get("repair_hint"), False, details={"logic_errors": logic_audit.get("logic_errors")})
        if validation.get("must_regenerate"):
            return ReasoningDecision("regenerate", "runtime_answer_validator_failed", validation.get("mismatch_reason"), False, details={"validation": validation})
        required = set(policy.get("required_components") or [])
        if required and validation.get("missing_required_components"):
            return ReasoningDecision("regenerate", "missing_required_components", ", ".join(validation.get("missing_required_components") or []), False)
        if policy.get("source_boundary_required") and not any(x in (body or "").lower() for x in ("runtime", "chatgpt", "aktywn", "model", "granica")):
            return ReasoningDecision("regenerate", "source_boundary_required_but_missing", "Add runtime/model/source boundary.", False)
        return ReasoningDecision("accept", "policy_validation_and_logic_audit_passed")
