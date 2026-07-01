from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from latka_jazn.version import PACKAGE_VERSION_FULL, schema_version

STRICT_RUNTIME_TRUTH_SCHEMA = schema_version("strict_runtime_truth_gate", version=PACKAGE_VERSION_FULL)
TIMESTAMP_DEGRADED_ERRORS = {
    "timestamp_untrusted",
    "timestamp_source_not_network",
}
TIMESTAMP_BLOCKING_ERRORS = {
    "timestamp_missing",
    "timestamp_stale_or_missing_freshness",
    "final_visible_integrity_invalid",
    "final_response_contract_missing",
}
NETWORK_SOURCE_PREFIXES = (
    "https://",
    "http://",
    "network_",
    "ntp_",
    "test_network",
)
TRUSTED_EXTERNAL_TIME_SOURCE_PREFIXES = (
    "chatgpt_web_time_tool",
    "chatgpt_loader_time",
    "openai_web_time_tool",
    "external_trusted_time",
    "injected_trusted_time",
)
LOCAL_OR_UNTRUSTED_SOURCE_MARKERS = (
    "local_fallback",
    "network_time_unavailable",
    "fallback",
    "manual",
    "unknown",
)


@dataclass(slots=True)
class RuntimeTruthGateResult:
    schema_version: str = STRICT_RUNTIME_TRUTH_SCHEMA
    ok: bool = True
    normal_response_allowed: bool = True
    active_state: str = "active_trusted"
    error_code: str | None = None
    errors: list[str] = field(default_factory=list)
    timestamp_source: str | None = None
    timestamp_trusted: bool | None = None
    timestamp_present: bool | None = None
    timestamp_freshness_seconds: int | None = None
    timestamp_max_age_seconds: int | None = None
    final_visible_integrity_valid: bool | None = None
    final_visible_origin_valid: bool | None = None
    truthful_degraded_disclosure: bool = False
    untrusted_timestamp_header: str | None = None
    truth_boundary: str = (
        "Brama prawdy runtime dopuszcza zwykłą odpowiedź Jaźni, gdy finalny widoczny tekst ma "
        "timestamp obecny i świeży. Czas sieciowy albo zaufany czas wstrzyknięty przez loader daje stan active_trusted. "
        "Lokalny fallback bez zaufanego źródła daje stan active_degraded, ale nie blokuje samej rozmowy."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _source_is_network(source: Any) -> bool:
    value = str(source or "").strip().lower()
    if not value:
        return False
    if any(marker in value for marker in LOCAL_OR_UNTRUSTED_SOURCE_MARKERS):
        return False
    if value.startswith(TRUSTED_EXTERNAL_TIME_SOURCE_PREFIXES):
        return True
    return value.startswith(NETWORK_SOURCE_PREFIXES) or "#http-date" in value


def evaluate_final_response_contract(contract: dict[str, Any] | None) -> RuntimeTruthGateResult:
    contract = dict(contract or {})
    integrity = contract.get("final_visible_integrity") if isinstance(contract.get("final_visible_integrity"), dict) else {}
    errors: list[str] = []
    if not contract:
        errors.append("final_response_contract_missing")
        return RuntimeTruthGateResult(
            ok=False,
            normal_response_allowed=False,
            active_state="active_degraded",
            error_code="runtime_truth_contract_missing",
            errors=errors,
            final_visible_integrity_valid=False,
        )

    valid = bool(integrity.get("valid"))
    present = bool(integrity.get("timestamp_present"))
    source = integrity.get("timestamp_source") or contract.get("timestamp_source")
    trusted = integrity.get("timestamp_trusted")
    if trusted is None:
        trusted = contract.get("timestamp_trusted")
    freshness_ok = bool(integrity.get("timestamp_freshness_ok", True))
    freshness_seconds = integrity.get("timestamp_freshness_seconds")
    max_age_seconds = integrity.get("timestamp_max_age_seconds")
    origin_truth_valid = bool(integrity.get("origin_truth_valid", True))
    validation_passed = bool(integrity.get("validation_passed", True))
    fallback_classification = str(contract.get("fallback_classification") or "not_fallback")
    requires_host_model = bool(contract.get("requires_host_model"))
    truthful_degraded_disclosure = bool(
        not origin_truth_valid and fallback_classification != "not_fallback"
    )
    disclosure_error = (
        "model_guided_speech_required"
        if requires_host_model and fallback_classification == "cannot_answer_directly"
        else "classified_non_dynamic_response"
    )

    if not present:
        errors.append("timestamp_missing")
    if trusted is not True:
        errors.append("timestamp_untrusted")
    if not _source_is_network(source):
        errors.append("timestamp_source_not_network")
    if not freshness_ok:
        errors.append("timestamp_stale_or_missing_freshness")
    if not valid and not truthful_degraded_disclosure and (
        not present or not freshness_ok or not origin_truth_valid or not validation_passed
    ):
        errors.append("final_visible_integrity_invalid")
    if truthful_degraded_disclosure:
        errors.append(disclosure_error)

    blocking_errors = [error for error in errors if error in TIMESTAMP_BLOCKING_ERRORS]
    degraded_errors = [error for error in errors if error in TIMESTAMP_DEGRADED_ERRORS]
    ok = not blocking_errors
    degraded = bool(degraded_errors) and ok
    return RuntimeTruthGateResult(
        ok=ok,
        normal_response_allowed=bool(ok and not truthful_degraded_disclosure),
        active_state="active_degraded" if degraded or truthful_degraded_disclosure else ("active_trusted" if ok else "active_blocked"),
        error_code=(disclosure_error if truthful_degraded_disclosure else ("timestamp_degraded" if degraded else (None if ok else "runtime_truth_gate_blocked"))),
        errors=errors,
        timestamp_source=str(source) if source is not None else None,
        timestamp_trusted=bool(trusted) if trusted is not None else None,
        timestamp_present=present,
        timestamp_freshness_seconds=int(freshness_seconds) if isinstance(freshness_seconds, int) else None,
        timestamp_max_age_seconds=int(max_age_seconds) if isinstance(max_age_seconds, int) else None,
        final_visible_integrity_valid=valid,
        final_visible_origin_valid=origin_truth_valid,
        truthful_degraded_disclosure=truthful_degraded_disclosure,
        untrusted_timestamp_header=contract.get("timestamp_header"),
    )


def build_blocked_visible_text(gate: RuntimeTruthGateResult) -> str:
    source = gate.timestamp_source or "unknown"
    header = gate.untrusted_timestamp_header or "brak timestampu runtime"
    errors = ", ".join(gate.errors) if gate.errors else "runtime_truth_gate_blocked"
    return (
        "[czas lokalny niezweryfikowany — Europe/Warsaw] ⚠️\n"
        "Nie zwracam zwykłej odpowiedzi Jaźni, bo brama prawdy runtime zablokowała turę: "
        f"{gate.error_code or 'runtime_truth_gate_blocked'}.\n"
        f"Niezaufany nagłówek tury: {header}\n"
        f"Źródło czasu: {source}; błędy: {errors}.\n"
        "Uruchom diagnostykę czasu sieciowego (`python main.py --network-time-check`) albo powtórz turę, gdy czas sieciowy będzie dostępny."
    )


def apply_runtime_truth_gate(result: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    updated = dict(result or {})
    gate = evaluate_final_response_contract(
        updated.get("final_response_contract") if isinstance(updated.get("final_response_contract"), dict) else None
    )
    gate_payload = gate.to_dict()
    updated["runtime_truth_gate"] = gate_payload
    if not gate.ok:
        original_final = updated.get("final_visible_text")
        updated["ok"] = False
        updated["error_code"] = gate.error_code or "runtime_truth_gate_blocked"
        updated["normal_response_blocked"] = True
        updated["blocked_final_visible_text"] = original_final
        updated["final_visible_text"] = build_blocked_visible_text(gate)
        updated["runtime_response_status"] = "blocked_by_runtime_truth_gate"
        decision = updated.get("conversation_decision") if isinstance(updated.get("conversation_decision"), dict) else {}
        decision = dict(decision)
        decision["runtime_truth_gate"] = gate_payload
        decision["normal_response_allowed"] = False
        decision["error_code"] = updated["error_code"]
        updated["conversation_decision"] = decision
    else:
        updated.setdefault("ok", True)
        updated["normal_response_blocked"] = False
        if gate.truthful_degraded_disclosure:
            updated["normal_response_blocked"] = True
            updated["runtime_response_status"] = "truthful_degraded_cannot_answer_directly"
            updated["requires_host_model"] = True
            decision = updated.get("conversation_decision") if isinstance(updated.get("conversation_decision"), dict) else {}
            decision = dict(decision)
            decision["runtime_truth_gate"] = gate_payload
            decision["normal_response_allowed"] = False
            decision["requires_host_model"] = True
            updated["conversation_decision"] = decision
        elif gate.active_state == "active_degraded":
            updated["timestamp_degraded"] = True
            updated["runtime_response_status"] = "normal_response_allowed_degraded_timestamp"
            decision = updated.get("conversation_decision") if isinstance(updated.get("conversation_decision"), dict) else {}
            decision = dict(decision)
            decision["runtime_truth_gate"] = gate_payload
            decision["normal_response_allowed"] = True
            decision["timestamp_degraded"] = True
            updated["conversation_decision"] = decision
        else:
            updated["runtime_response_status"] = "normal_response_allowed"
    return updated, gate_payload


def daemon_active_state(*, marker_found: bool, pid_alive: bool, ping_ok: bool, timestamp_trusted: bool | None) -> str:
    if not (marker_found and pid_alive and ping_ok):
        return "inactive"
    if timestamp_trusted is True:
        return "active_trusted"
    return "active_degraded"
