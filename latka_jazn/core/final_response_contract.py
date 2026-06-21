from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import hashlib
import re

SCHEMA_VERSION = "final_response_contract/v14.7.0"


@dataclass(slots=True)
class FinalResponseContract:
    """Kontrakt widocznej odpowiedzi: timestamp nie może zostać schowany w JSON.

    ChatGPT/runtime może przekazywać wiele pól diagnostycznych, ale użytkownik ma
    zobaczyć jedną odpowiedź Łatki zaczynającą się od tego samego timestampu,
    który powstał w runtime dla tej tury.
    """

    turn_id: str
    trace_id: str
    runtime_version: str
    timestamp_header: str
    timezone: str
    state_emoticon: str
    body: str
    final_visible_text: str
    timestamp_required: bool = True
    timestamp_source: str = "cognitive_turn_envelope.trace.timestamp_header"
    runtime_route: str = "unknown"
    detected_user_intent: str = "unknown"
    direct_answer_required: bool = False
    runtime_next_step: str | None = None
    greeting_prefix: str | None = None
    substantive_remainder: str | None = None
    continuity_badge_policy: dict[str, Any] | None = None
    runtime_followup_required: bool = False
    runtime_answer_quality: str = "topic_aligned"
    fallback_classification: str = "not_fallback"
    startup_procedure_required: bool = False
    response_generation_mode: str = "unknown"
    template_origin: dict[str, Any] | None = None
    source_origin_detail: str | None = None
    chatgpt_interpretation_distance: str = "unknown"
    runtime_text_hash: str | None = None
    visible_answer_hash: str | None = None
    provenance_contract: dict[str, Any] | None = None
    preservation_contract: dict[str, Any] | None = None
    voice_source_contract: dict[str, Any] | None = None
    runtime_rendering_mode: dict[str, Any] | None = None
    memory_recall_contract_status: dict[str, Any] | None = None
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def build(
        cls,
        *,
        turn_id: str,
        trace_id: str,
        runtime_version: str,
        timestamp_header: str,
        timezone: str,
        state_emoticon: str,
        body: str,
        conversation_decision: dict[str, Any] | None = None,
        continuity_badge_policy: dict[str, Any] | None = None,
    ) -> "FinalResponseContract":
        body = re.sub(r"\s+", " ", (body or "").strip())
        decision = dict(conversation_decision or {})
        if not timestamp_header:
            raise ValueError("timestamp_header is required for final visible response")
        marker = state_emoticon or "🌿"
        final_visible_text = cls.ensure_timestamp_prefix(timestamp_header, marker, body)
        fallback_classification = cls.classify_fallback(decision.get("route"), body, runtime_version=runtime_version)
        if fallback_classification != "not_fallback":
            runtime_answer_quality = "stale_route_mismatch" if fallback_classification == "stale_route_mismatch" else "fallback_or_debug"
        else:
            runtime_answer_quality = str(decision.get("runtime_answer_quality") or "topic_aligned")
        preservation_contract = {
            "must_preserve_runtime_body": True,
            "must_preserve_runtime_next_step": bool(decision.get("next_step")),
            "must_not_drop_runtime_followup": bool(decision.get("runtime_followup_required")),
            "must_answer_substantive_remainder": bool(decision.get("direct_answer_required")),
            "must_report_fallback_classification": fallback_classification != "not_fallback",
            "must_report_startup_status_when_required": bool(decision.get("startup_procedure_required")),
            "truth_boundary": "Warstwa ChatGPT może dopowiedzieć, ale nie może po cichu zgubić trasy, next_step, właściwej intencji runtime, klasyfikacji fallbacku ani pochodzenia template/runtime.",
        }
        return cls(
            turn_id=turn_id,
            trace_id=trace_id,
            runtime_version=runtime_version,
            timestamp_header=timestamp_header,
            timezone=timezone,
            state_emoticon=marker,
            body=body,
            final_visible_text=final_visible_text,
            runtime_route=str(decision.get("route") or "unknown"),
            detected_user_intent=str(decision.get("detected_user_intent") or "unknown"),
            direct_answer_required=bool(decision.get("direct_answer_required")),
            runtime_next_step=decision.get("next_step"),
            greeting_prefix=decision.get("greeting_prefix"),
            substantive_remainder=decision.get("substantive_remainder"),
            continuity_badge_policy=continuity_badge_policy or None,
            runtime_followup_required=bool(decision.get("runtime_followup_required")),
            runtime_answer_quality=runtime_answer_quality,
            fallback_classification=fallback_classification,
            startup_procedure_required=bool(decision.get("startup_procedure_required")),
            response_generation_mode=str(decision.get("response_generation_mode") or "unknown"),
            template_origin=decision.get("template_origin") or None,
            source_origin_detail=decision.get("source_origin_detail"),
            chatgpt_interpretation_distance=str(decision.get("interpretation_distance") or "unknown"),
            runtime_text_hash=decision.get("runtime_text_hash"),
            visible_answer_hash=decision.get("visible_answer_hash"),
            provenance_contract=decision.get("runtime_provenance") or None,
            preservation_contract=preservation_contract,
            voice_source_contract=decision.get("voice_source_contract") or None,
            runtime_rendering_mode=decision.get("runtime_rendering_mode") or None,
            memory_recall_contract_status=decision.get("memory_recall_contract_status") or None,
        )

    @staticmethod
    def classify_fallback(route: Any, body: str, *, runtime_version: str | None = None) -> str:
        text = (body or "").lower()
        route_text = str(route or "").lower()
        runtime_text = str(runtime_version or "").lower()
        technical_signatures = (
            "nie znalazłam osobnej trasy odpowiedzi",
            "runtime odebrał wiadomość",
            "debugowy fallback",
            "pusty fallback",
        )
        if any(sig in text for sig in technical_signatures):
            return "technical_fallback"
        if route_text == "v14_6_1_nlp_adapter_update" and not runtime_text.startswith("v14.6.1") and any(
            sig in text for sig in (
                "właściwy bezpieczny krok dla v14.6.1",
                "utrzymać v14.6.1",
                "pełny eksport v14.6.1",
            )
        ):
            return "stale_route_mismatch"
        if runtime_text.startswith("v14.6.10") and route_text == "v14_6_1_nlp_adapter_update" and "v14.6.10" in text:
            return "stale_route_mismatch"
        if route_text in {"general_dialogue", "open_question"} and "odpowiedź runtime ma teraz wyraźny obowiązek" in text:
            return "obligation_instead_of_answer"
        if "kontrakt" in text and "zamiast odpowiedzi" in text:
            return "contract_instead_of_answer"
        if route_text in {"free_open_question_no_specific_source", "free_open_question_synthesized"} and "nie mam dla niego specjalistycznej" in text:
            return "generic_no_source_instead_of_dialogue"
        if route_text == "correction_acknowledged" and any(x in text for x in ("co jeszcze jest źle", "co jest źle", "systemie jaźni")):
            return "diagnostic_question_misread_as_correction"
        if any(x in text for x in ("odebrałam sens wiadomości", "najuczciwszy model jest hybrydowy")) and route_text in {"general_dialogue", "open_question", "free_open_question_synthesized"}:
            return "generic_status_instead_of_answer"
        return "not_fallback"

    @staticmethod
    def ensure_timestamp_prefix(timestamp_header: str, state_emoticon: str, body_or_text: str) -> str:
        text = (body_or_text or "").strip()
        if text.startswith(timestamp_header):
            return text
        marker = state_emoticon or "🌿"
        return f"{timestamp_header} {marker}\n{text}"

    @staticmethod
    def validate_visible_text(timestamp_header: str, text: str) -> dict[str, Any]:
        """Waliduje, czy widoczna odpowiedź dziedziczy timestamp koperty tury."""
        visible = (text or "").strip()
        has_timestamp = bool(timestamp_header) and visible.startswith(timestamp_header)
        return {
            "schema_version": "final_response_contract_validation/v14.7.0",
            "timestamp_header": timestamp_header,
            "timestamp_present": has_timestamp,
            "valid": has_timestamp,
            "text_sha256": hashlib.sha256(visible.encode("utf-8")).hexdigest(),
        }
