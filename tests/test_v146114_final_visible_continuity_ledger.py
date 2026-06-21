from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.final_visible_reply_capture import FinalVisibleReplyCapture
from latka_jazn.core.final_response_contract import FinalResponseContract

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_process_turn_persists_final_visible_reply_and_continuity_index(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn(
            "Cześć Łatko, sprawdź czy finalna odpowiedź zapisuje się w ledgerze.",
            client_context={"client": "unit_test_v146114", "lifecycle": "one_shot"},
        )
    finally:
        engine.shutdown()

    trace = envelope.to_dict()["trace"]
    runtime_events = _jsonl(tmp_path / "memory" / "raw" / "runtime_events.jsonl")
    turns = _jsonl(tmp_path / "memory" / "raw" / "conversation_turns.jsonl")
    assert any(e.get("event_type") == "final_visible_assistant_reply" and e.get("payload", {}).get("turn_id") == trace["turn_id"] for e in runtime_events)
    assert any(t.get("role") == "assistant" and t.get("metadata", {}).get("entrypoint") == "append_final_visible_reply" for t in turns)

    index_path = tmp_path / "memory" / "raw" / "session_continuity_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["version"] == VERSION
    assert any(entry.get("reason") == "final_visible_reply_persisted" for entry in index.get("recent_events", []))


def test_external_chatgpt_final_visible_reply_can_be_captured_with_same_trace(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    timestamp = "[🕒 2026-05-17 20:00:00 GMT+2, niedziela, Europe/Warsaw]"
    try:
        capture = engine.persist_final_visible_reply(
            turn_id="turn-visible-1",
            trace_id="trace-visible-1",
            timestamp_header=timestamp,
            final_text="Odpowiedź bez timestampu ma zostać naprawiona przed zapisem.",
            state_emoticon="🧭",
            source="unit_test_visible_layer",
            client_context={"lifecycle": "one_shot_visible_capture"},
        )
    finally:
        engine.shutdown()

    assert capture["schema_version"] == "final_visible_reply_capture/v14.6.2"
    assert capture["was_repaired"] is True
    assert capture["timestamp_present_in_final"] is True
    assert capture["final_visible_text"].startswith(timestamp)

    events = _jsonl(tmp_path / "memory" / "raw" / "runtime_events.jsonl")
    assert any(e.get("event_type") == "final_visible_assistant_reply" and e.get("exact_text", "").startswith(timestamp) for e in events)


def test_capture_object_and_contract_validation_detect_missing_timestamp() -> None:
    timestamp = "[🕒 2026-05-17 20:10:00 GMT+2, niedziela, Europe/Warsaw]"
    bad = FinalResponseContract.validate_visible_text(timestamp, "Bez timestampu")
    assert bad["valid"] is False
    capture = FinalVisibleReplyCapture.build(
        turn_id="turn-2",
        trace_id="trace-2",
        timestamp_header=timestamp,
        state_emoticon="🌿",
        final_text="Bez timestampu",
        source="unit_test",
    )
    assert capture.was_repaired is True
    assert capture.final_visible_text.startswith(timestamp)


def test_cli_record_final_reply_repairs_and_persists(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    timestamp = "[🕒 2026-05-17 20:20:00 GMT+2, niedziela, Europe/Warsaw]"
    try:
        payload = engine.persist_final_visible_reply(
            turn_id="turn-cli-1",
            trace_id="trace-cli-1",
            timestamp_header=timestamp,
            final_text="Widoczna odpowiedź CLI bez timestampu.",
            state_emoticon="🛠️",
            source="unit_test_cli_equivalent",
            client_context={"client": "unit_test_cli_equivalent", "lifecycle": "one_shot_visible_capture"},
        )
    finally:
        engine.shutdown()
    assert payload["schema_version"] == "final_visible_reply_capture/v14.6.2"
    assert payload["final_visible_text"].startswith(timestamp)
    assert payload["was_repaired"] is True
