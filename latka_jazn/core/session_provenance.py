from __future__ import annotations

from typing import Any
import re

SCHEMA_VERSION = "session_provenance/v14.8.3.2"

TIMESTAMP_HEADER_RE = re.compile(
    r"^\[🕒 \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT[+-]\d{1,2}, [^,\]]+, Europe/Warsaw\]$"
)

RENDER_ARTIFACTS = (
    "aaaktywny",
    "aaktywny",
    "prrzez",
    "nieddziela",
    "niedzielaa",
    "pierwszoossobową",
    "pierwszoosobowąą",
    "GMMT",
    "2026-066",
    "221:",
    "13:43:228",
    "rozmawiać ć",
    "Uwa ażam",
    "operacyjnnego",
    "ddebug",
    "techniiczna",
)


def build_session_provenance(
    *,
    session_id: str,
    client: str,
    lifecycle: str,
    process_reused: bool,
    engine_reused_between_turns: bool,
    load_metadata: dict[str, Any] | None = None,
    save_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    load_metadata = dict(load_metadata or {})
    save_status = dict(save_status or {})
    save_truth_boundary = save_status.pop("truth_boundary", None)
    truth_boundary = (
        "Sesja oznacza stan rozmowy w tym procesie i ewentualny zapis runtime_session_state. "
        "Nie oznacza, że po EOF, /exit albo zakończeniu batcha działa proces w tle."
    )
    if save_status and not save_status.get("session_state_saved", False):
        truth_boundary += " Zapis stanu sesji nie został potwierdzony; trwałość jest ograniczona do pamięci procesu."
    if save_truth_boundary:
        truth_boundary += f" {save_truth_boundary}"
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "client": client,
        "lifecycle": lifecycle,
        "process_reused": bool(process_reused),
        "engine_reused_between_turns": bool(engine_reused_between_turns),
        "session_reused": bool(load_metadata.get("session_reused", False)),
        "session_resurrected_from_disk": bool(load_metadata.get("session_resurrected_from_disk", False)),
        "session_loaded_from": str(load_metadata.get("session_loaded_from") or "new"),
        "background_process_claim_allowed": False,
        "truth_boundary": truth_boundary,
        **save_status,
    }


def validate_final_visible_integrity(result: dict[str, Any]) -> dict[str, Any]:
    final_visible_text = str(result.get("final_visible_text") or "")
    trace = result.get("trace") or {}
    timestamp_header = str(trace.get("timestamp_header") or "")
    decision = result.get("conversation_decision") or {}
    runtime_provenance = result.get("runtime_provenance") or decision.get("runtime_provenance") or {}
    exact_runtime_text = str(result.get("exact_runtime_text") or runtime_provenance.get("exact_runtime_text") or "")
    visible_answer_text = str(runtime_provenance.get("visible_answer_text") or "")
    handler_result = decision.get("handler_result") or {}
    handler_body = str(handler_result.get("body") or "")

    errors: list[str] = []
    if timestamp_header and not TIMESTAMP_HEADER_RE.match(timestamp_header):
        errors.append("timestamp_header_invalid")
    if timestamp_header and not final_visible_text.startswith(f"{timestamp_header} "):
        errors.append("final_visible_text_missing_timestamp")
    if visible_answer_text and visible_answer_text != final_visible_text:
        errors.append("visible_answer_text_mismatch")
    if handler_body and exact_runtime_text and handler_body != exact_runtime_text:
        errors.append("handler_body_exact_runtime_text_mismatch")
    for artifact in RENDER_ARTIFACTS:
        if artifact in final_visible_text or artifact in exact_runtime_text:
            errors.append(f"render_artifact_detected:{artifact}")
    if "\ufffd" in final_visible_text or "\ufffd" in exact_runtime_text:
        errors.append("unicode_replacement_character_detected")

    payload = {
        "schema_version": "final_visible_integrity/v14.8.3.2",
        "valid": not errors,
        "errors": errors,
        "timestamp_header": timestamp_header,
        "checked_artifact_count": len(RENDER_ARTIFACTS),
    }
    if errors:
        raise ValueError("final_visible_integrity_failed: " + ",".join(errors))
    return payload
