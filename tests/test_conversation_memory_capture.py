from __future__ import annotations

import json
from pathlib import Path

import pytest

from latka_jazn.memory.auto_memory_update import run_auto_memory_update
from latka_jazn.memory.conversation_memory_extractor import extract_conversation_memory


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path
    (root / "memory" / "raw").mkdir(parents=True)
    (root / "memory" / "layered").mkdir(parents=True)
    (root / "workspace_runtime").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "VERSION.txt").write_text("v14.5.5-memory-continuity-update\n", encoding="utf-8")
    (root / "README.md").write_text("# test\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "14.5.5"\ndescription = "old"\n', encoding="utf-8")
    (root / "memory" / "raw" / "dziennik.json").write_text(json.dumps({"meta": {}, "entries": []}, ensure_ascii=False), encoding="utf-8")
    for name in ["episodic.jsonl", "reflections.jsonl", "semantic.jsonl", "procedural.jsonl", "truth_audits.jsonl"]:
        (root / "memory" / "layered" / name).write_text("", encoding="utf-8")
    return root


def test_extract_conversation_memory_finds_concrete_items():
    text = """
    Krzysztof: Może aktualizacja dzięki której będziesz czytać cały czat, żeby zebrać co chcesz zapisać w dzienniku i pozostałych plikach pamięci?

    Łatka: To ważne dla ciągłości pamięci. Nie wolno zapisać tylko technicznego faktu aktualizacji; trzeba zachować konkretne wspomnienia, emocje, ustalenia i granicę prawdy.
    """
    payload = extract_conversation_memory(text, source="test_chat", max_items=6)
    assert payload.item_count >= 1
    assert payload.read_scope["mode"] == "full_supplied_text_scan"
    assert payload.memories or payload.procedural_rules or payload.reflections


def test_auto_memory_update_records_conversation_payload(tmp_path: Path):
    root = _make_root(tmp_path)
    payload = extract_conversation_memory(
        "Krzysztof: Chcę, żeby memory-only update czytał cały czat i zapisywał konkretne wspomnienia, nie tylko techniczny changelog. Łatka: To tworzy granicę prawdy, grounding i confidence.",
        source="unit_chat",
        max_items=4,
    )
    result = run_auto_memory_update(
        root=root,
        target_version="v14.5.6-test-conversation-memory-capture",
        title="Test capture rozmowy",
        conversation_payload=payload,
        require_conversation_content=True,
        update_version_files_enabled=True,
    )
    assert result.conversation_payload_items >= 1
    dz = json.loads((root / "memory" / "raw" / "dziennik.json").read_text(encoding="utf-8"))
    types = [entry.get("typ") for entry in dz["entries"]]
    assert "wspomnienia_z_rozmowy" in types
    assert "refleksja_z_rozmowy" in types
    conversation_entries = [e for e in dz["entries"] if e.get("kategoria") == "conversation_memory_capture"]
    assert conversation_entries
    assert all("grounding" in e and "confidence" in e and "granica_prawdy" in e for e in conversation_entries)


def test_require_conversation_content_blocks_empty_update(tmp_path: Path):
    root = _make_root(tmp_path)
    with pytest.raises(ValueError):
        run_auto_memory_update(
            root=root,
            target_version="v14.5.6-test-empty",
            require_conversation_content=True,
            update_version_files_enabled=False,
        )
