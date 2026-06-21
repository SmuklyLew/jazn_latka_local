from __future__ import annotations

import json
import shutil
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.runtime_status import build_runtime_status
from latka_jazn.memory.importer import MemoryImporter
from latka_jazn.memory.store import MemoryStore


def _write_small_chat_html(path: Path) -> None:
    data = [
        {
            "conversation_id": "c-review",
            "id": "c-review",
            "title": "Review Fixes",
            "create_time": 1700000000.0,
            "update_time": 1700000001.0,
            "current_node": "m2",
            "mapping": {
                "m1": {"children": ["m2"], "message": {"id": "m1", "author": {"role": "user"}, "create_time": 1700000000.0, "content": {"content_type": "text", "parts": ["Zaindeksuj surową pamięć przy starcie."]}}},
                "m2": {"children": [], "message": {"id": "m2", "author": {"role": "assistant"}, "create_time": 1700000001.0, "content": {"content_type": "text", "parts": ["Indeks legacy_messages powinien być aktywny automatycznie."]}}},
            },
        }
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("<html><script>var jsonData = " + json.dumps(data, ensure_ascii=False) + ";</script></html>", encoding="utf-8")


def test_register_packaged_sources_auto_imports_present_chat_html(tmp_path: Path) -> None:
    _write_small_chat_html(tmp_path / "memory" / "raw" / "chat.html")
    store = MemoryStore(tmp_path / "workspace_runtime" / "test.sqlite3")
    try:
        report = MemoryImporter(store, tmp_path).register_packaged_sources(auto_import_raw_chat_html=True)
        stats = store.stats()
    finally:
        store.close()

    assert isinstance(report["chat_html_auto_import"], dict)
    assert report["chat_html_auto_import"]["status"] == "ok"
    assert stats["legacy_conversations"] == 1
    assert stats["legacy_messages"] == 2


def test_runtime_status_uses_relative_paths_and_readonly_sqlite(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "workspace_runtime" / "test.sqlite3")
    store.close()
    archive = tmp_path / "memory" / "raw" / "chat.html.7z"
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(b"not-real-archive")

    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    text = build_runtime_status(cfg, store=None, readonly=True)

    assert "tryb diagnostyki: read-only" in text
    assert "memory/raw/chat.html.7z" in text
    assert str(tmp_path) not in text


def test_status_command_does_not_record_runtime_turn(tmp_path: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = tmp_path / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)

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
