from __future__ import annotations

import json
import shutil
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.memory.event_ledger import RuntimeEventLedger
from latka_jazn.memory.runtime_persistence import RuntimeMemoryWriter


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_event_ledger_appends_exact_turns_without_summary(tmp_path: Path) -> None:
    ledger = RuntimeEventLedger(tmp_path, version="v-test", timezone_name="Europe/Warsaw")
    text = "Pierwsza linia.\nDruga linia z pełnym kontekstem, bez streszczeń i bez ucinania."
    result = ledger.append_turn("user", text, source="unit_test", client_context={"client": "unit"})

    assert result is not None
    turns = _jsonl(tmp_path / "memory" / "raw" / "conversation_turns.jsonl")
    events = _jsonl(tmp_path / "memory" / "raw" / "runtime_events.jsonl")
    assert turns[-1]["text"] == text
    assert turns[-1]["no_summary"] is True
    assert any(e.get("exact_text") == text and e.get("event_type") == "conversation_turn" for e in events)


def test_protocol_question_with_typo_is_persisted_as_procedural_rule(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    message = "Czy w systemie Jaźni jest ustalone, że wszystkie wydarzenia muszą być odpisywanie na bierzaco w tle?"
    try:
        packet = engine.build_cognitive_frame(message, client_context={"client": "unit_test"})
    finally:
        engine.shutdown()

    assert packet["persistence"]["accepted"] is True
    assert packet["persistence"]["candidate_kind"] == "reguła_proceduralna"
    turns = _jsonl(tmp_path / "memory" / "raw" / "conversation_turns.jsonl")
    assert any(t.get("text") == message for t in turns)
    procedural = _jsonl(tmp_path / "memory" / "layered" / "procedural.jsonl")
    assert any("append-only" in p.get("action", "") or "append-only" in p.get("procedural_action", "") for p in procedural)


def test_status_readonly_keeps_sqlite_stats_but_writes_raw_turn_log(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        before = engine.store.stats().copy()
        reply = engine.handle_user_message("/status", client_context={"client": "unit_test"})
        after = engine.store.stats().copy()
    finally:
        engine.shutdown()

    assert "Diagnoza runtime" in reply
    assert before == after
    turns = _jsonl(tmp_path / "memory" / "raw" / "conversation_turns.jsonl")
    assert any(t.get("role") == "user" and t.get("text") == "/status" for t in turns)
    assert any(t.get("role") == "assistant" and "Diagnoza runtime" in t.get("text", "") for t in turns)


def test_runtime_memory_writer_accepts_no_summary_full_write_terms(tmp_path: Path) -> None:
    writer = RuntimeMemoryWriter(tmp_path, version="v-test")
    candidate = writer.build_candidate_from_runtime_turn(
        user_text="Nie rób streszczeń, zapisuj pełną treść do końca w plikach pamięci Jaźni.",
        importance=0.2,
        importance_reason="unit test",
        emotional_tags=[],
    )
    accepted, reason = writer.should_persist(candidate)
    assert accepted is True
    assert reason in {"memory_trigger_word", "memory_protocol_intent", "importance_threshold"}
