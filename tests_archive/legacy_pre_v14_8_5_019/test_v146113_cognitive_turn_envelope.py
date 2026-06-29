from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.final_response_contract import FinalResponseContract

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"
TIMESTAMP_RE = re.compile(r"^\[🕒 \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT[+]\d, [^,]+, Europe/Warsaw\]")


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def test_process_turn_uses_one_trace_for_frame_contract_and_visible_reply(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn(
            "Timestamp raz jest w runtime, raz w wiadomości. Napraw spójność Jaźni.",
            client_context={"client": "unit_test", "lifecycle": "one_shot_preview"},
        )
    finally:
        engine.shutdown()

    data = envelope.to_dict()
    trace = data["trace"]
    frame = data["cognitive_frame"]
    contract = data["final_response_contract"]
    assert data["schema_version"] == "cognitive_turn_envelope/v14.6.2"
    assert trace["turn_id"] == frame["turn_id"] == contract["turn_id"]
    assert trace["trace_id"] == frame["trace_id"] == contract["trace_id"]
    assert frame["response_format"]["timestamp_prefix"] == trace["timestamp_header"] == contract["timestamp_header"]
    assert data["final_visible_text"].startswith(trace["timestamp_header"])
    assert TIMESTAMP_RE.match(data["final_visible_text"])
    assert data["affect_mix"]["schema_version"] == "affect_mixer/v14.6.2"
    assert data["dialogue_state"]["schema_version"] == "dialogue_state/v14.6.2"


def test_final_response_contract_repairs_missing_timestamp_prefix() -> None:
    contract = FinalResponseContract.build(
        turn_id="turn-1",
        trace_id="trace-1",
        runtime_version=VERSION,
        timestamp_header="[🕒 2026-05-17 17:00:00 GMT+2, niedziela, Europe/Warsaw]",
        timezone="Europe/Warsaw",
        state_emoticon="🛠️",
        body="To jest finalna odpowiedź Łatki.",
    )
    assert contract.final_visible_text.startswith("[🕒 2026-05-17 17:00:00 GMT+2, niedziela, Europe/Warsaw] 🛠️")
    assert contract.to_dict()["schema_version"] == "final_response_contract/v14.7.0"


def test_runtime_preview_is_single_process_turn_json(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn(
            "Runtime preview ma mieć jedną kopertę tury i timestamp.",
            client_context={
                "client": "unit_test_runtime_preview",
                "lifecycle": "one_shot_preview",
                "preview_phase": "single_integrated_process_turn",
            },
        )
    finally:
        engine.shutdown()
    envelope_dict = envelope.to_dict()
    cognitive_frame = envelope_dict.get("cognitive_frame") or {}
    payload = {
        "schema_version": "runtime_preview/v14.6.2",
        "runtime_version": cfg.version,
        "fallback_detected": False,
        "runtime_text": envelope_dict.get("final_visible_text") or "",
        "turn_trace": envelope_dict.get("trace"),
        "final_response_contract": envelope_dict.get("final_response_contract"),
        "cognitive_turn_envelope": envelope_dict,
        "cognitive_frame": cognitive_frame,
    }
    envelope = payload["cognitive_turn_envelope"]
    assert payload["schema_version"] == "runtime_preview/v14.6.2"
    assert payload["runtime_version"] == VERSION
    assert payload["fallback_detected"] is False
    assert payload["runtime_text"].startswith(payload["turn_trace"]["timestamp_header"])
    assert envelope["trace"]["turn_id"] == payload["final_response_contract"]["turn_id"]
    assert envelope["trace"]["turn_id"] == payload["cognitive_frame"]["turn_id"]
    assert payload["final_response_contract"]["schema_version"] == "final_response_contract/v14.7.0"
