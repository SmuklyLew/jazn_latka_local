from __future__ import annotations

import json
from pathlib import Path

from latka_jazn.memory.runtime_persistence import (
    RuntimeMemoryCandidate,
    RuntimeMemoryWriter,
    scan_runtime_duplicates,
)
from latka_jazn.memory.store import MemoryStore


def _lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def test_runtime_writer_appends_once_and_deduplicates(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "workspace_runtime" / "test.sqlite3")
    try:
        writer = RuntimeMemoryWriter(tmp_path, version="v-test", store=store)
        candidate = RuntimeMemoryCandidate(
            kind="runtime_wspomnienie",
            title="Test pamięci runtime",
            content="Krzysztof prosi, aby Łatka zapisywała ważne rozmowy od razu w runtime.",
            source="unit_test",
            grounding="recognized",
            confidence=0.8,
            emotional_tags=["skupienie", "ciągłość"],
            memory_tags=["test"],
            importance=0.9,
            semantic_subject="Runtime memory",
            semantic_predicate="ma zapisywać",
            semantic_value="ważne rozmowy w czasie działania",
            procedural_trigger="ważna rozmowa runtime",
            procedural_action="dopisać dziennik i warstwy pamięci",
            procedural_reason="ochrona ciągłości Jaźni",
        )
        first = writer.persist_candidate(candidate)
        second = writer.persist_candidate(candidate)
    finally:
        store.close()

    assert first.accepted is True
    assert first.appended_count >= 6
    assert second.accepted is True
    assert second.appended_count == 0

    journal = json.loads((tmp_path / "memory/raw/dziennik.json").read_text(encoding="utf-8"))
    assert len(journal["entries"]) == 1
    entry = journal["entries"][0]
    assert entry["grounding"] == "recognized"
    assert entry["confidence"] == 0.8
    assert entry["granica_prawdy"]
    assert entry["fingerprint"] == first.candidate_fingerprint

    for rel in [
        "memory/layered/episodic.jsonl",
        "memory/layered/reflections.jsonl",
        "memory/layered/semantic.jsonl",
        "memory/layered/procedural.jsonl",
        "memory/layered/truth_audits.jsonl",
        "memory/layered/affective.jsonl",
    ]:
        assert len(_lines(tmp_path / rel)) == 1


def test_scan_runtime_duplicates_reports_duplicate_fingerprints(tmp_path: Path) -> None:
    layer = tmp_path / "memory/layered/episodic.jsonl"
    layer.parent.mkdir(parents=True)
    layer.write_text(
        json.dumps({"fingerprint": "abc", "scene": "pierwszy"}, ensure_ascii=False) + "\n"
        + json.dumps({"fingerprint": "abc", "scene": "drugi"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report = scan_runtime_duplicates(tmp_path)
    assert report["duplicates"]
    assert report["files"]["memory/layered/episodic.jsonl"]["duplicate_keys"]["abc"] == 2
