from __future__ import annotations

import json
from pathlib import Path

from latka_jazn.core.clock import WarsawClock
from latka_jazn.memory.chat_html_importer import import_chat_html_to_store
from latka_jazn.memory.file_sync import MemoryFileSync
from latka_jazn.memory.store import MemoryStore
from tools.rebuild_latka_memory_database import Progress, Rebuilder, SourceSpec


def test_clock_header_has_timestamp_and_gmt():
    header = WarsawClock().header()
    assert header.startswith("[🕒 ")
    assert "GMT+" in header or "GMT-" in header or "GMT0" in header
    assert "Europe/Warsaw" in header



def test_clock_falls_back_when_tzdata_is_missing(monkeypatch):
    import latka_jazn.core.clock as clock_module
    from zoneinfo import ZoneInfoNotFoundError

    def missing_zoneinfo(_timezone_name: str):
        raise ZoneInfoNotFoundError("No time zone found with key Europe/Warsaw")

    monkeypatch.setattr(clock_module, "ZoneInfo", missing_zoneinfo)

    clock = WarsawClock("Europe/Warsaw")
    assert clock.degraded is True
    assert clock.degraded_reason
    assert "tzdata" in clock.degraded_reason

    sample = clock.now(network_first=False)
    assert sample.dt.tzinfo is not None

    header = clock.header(sample)
    assert header.startswith("[🕒 ")
    assert "GMT+" in header or "GMT-" in header or "GMT0" in header
    assert "Europe/Warsaw" in header


def test_chat_html_importer_indexes_small_export(tmp_path: Path):
    html = tmp_path / "chat.html"
    data = [
        {
            "conversation_id": "c1",
            "id": "c1",
            "title": "Katedra Lumiela",
            "create_time": 1700000000.0,
            "update_time": 1700000100.0,
            "current_node": "m2",
            "mapping": {
                "m1": {"children": ["m2"], "message": {"id": "m1", "author": {"role": "user"}, "create_time": 1700000001.0, "content": {"content_type": "text", "parts": ["Pamiętasz katedrę, w której był Lumiel?"]}}},
                "m2": {"children": [], "message": {"id": "m2", "author": {"role": "assistant"}, "create_time": 1700000002.0, "content": {"content_type": "text", "parts": ["Tak, Lumiel i katedra były sceną literacką."]}}},
            },
        }
    ]
    html.write_text("<html><script>var jsonData = " + json.dumps(data, ensure_ascii=False) + ";</script></html>", encoding="utf-8")
    store = MemoryStore(tmp_path / "workspace_runtime" / "test.sqlite3")
    try:
        report = import_chat_html_to_store(store, html)
        rows = store.search_messages_any(["Lumiel", "katedra"], 10)
    finally:
        store.close()
    assert report.status == "ok"
    assert report.conversations_imported == 1
    assert report.messages_imported == 2
    assert len(rows) >= 2


def test_chat_html_importer_indexes_rendered_dom_export(tmp_path: Path):
    html = tmp_path / "rendered-chat.html"
    html.write_text(
        """<body><div id="root">
        <div class="conversation"><h4>Project files</h4>
        <pre class="message"><div class="author">user</div><div>Show local files</div></pre>
        <pre class="message"><div class="author">ChatGPT</div><div>Here is the file list.</div></pre>
        </div></div></body>""",
        encoding="utf-8",
    )
    store = MemoryStore(tmp_path / "workspace_runtime" / "test.sqlite3")
    try:
        report = import_chat_html_to_store(store, html)
        conversations = store.con.execute("SELECT title FROM legacy_conversations").fetchall()
        messages = store.con.execute(
            "SELECT author_role,text,is_visible_path,visible_index FROM legacy_messages ORDER BY visible_index"
        ).fetchall()
    finally:
        store.close()
    assert report.status == "ok"
    assert report.conversations_imported == 1
    assert report.messages_imported == 2
    assert [row["title"] for row in conversations] == ["Project files"]
    assert [row["author_role"] for row in messages] == ["user", "assistant"]
    assert [row["is_visible_path"] for row in messages] == [1, 1]
    assert "Show local files" in messages[0]["text"]
    assert "Here is the file list." in messages[1]["text"]


def test_rebuild_importer_stages_rendered_dom_export(tmp_path: Path):
    html = tmp_path / "rendered-chat.html"
    html.write_text(
        """<body><div id="root">
        <div class="conversation"><h4>Project files</h4>
        <pre class="message"><div class="author">user</div><div>Show local files</div></pre>
        <pre class="message"><div class="author">ChatGPT</div><div>Here is the file list.</div></pre>
        </div></div></body>""",
        encoding="utf-8",
    )
    db_path = tmp_path / "rebuilt.sqlite3"
    rebuilder = Rebuilder(
        tmp_path,
        db_path,
        progress=Progress(enabled=False, total_bytes=html.stat().st_size),
        store_raw_json_text=True,
    )
    try:
        rebuilder.open()
        rebuilder.import_source(SourceSpec(html, "raw_chatgpt_html", 20, "test_rendered_dom"))
        session = rebuilder.db.execute("SELECT title,message_count,raw_payload_json FROM conversation_sessions").fetchone()
        rows = rebuilder.db.execute(
            "SELECT title,content_text,content_json,tags_json FROM staging_memory_entries ORDER BY source_id_original"
        ).fetchall()
    finally:
        rebuilder.close()
    assert session["title"] == "Project files"
    assert session["message_count"] == 2
    assert json.loads(session["raw_payload_json"])["mapping_node_count"] == 2
    assert [row["content_text"] for row in rows] == ["Show local files", "Here is the file list."]
    first_meta = json.loads(rows[0]["content_json"])
    second_meta = json.loads(rows[1]["content_json"])
    assert first_meta["source_format"] == "rendered_chat_dom_html"
    assert second_meta["author_label"] == "ChatGPT"
    assert second_meta["model_slug"] is None
    assert "rendered_chat_dom_html" in json.loads(rows[1]["tags_json"])


def test_file_sync_imports_raw_layers_and_exports(tmp_path: Path):
    layered = tmp_path / "memory" / "layered"
    layered.mkdir(parents=True)
    (layered / "episodic.jsonl").write_text(json.dumps({"episode_id": "e1", "created_at_utc": "2026-01-01T00:00:00+00:00", "scene": "Spacer do Olsztyna", "source": "test", "grounding": "verified", "confidence": 0.9}, ensure_ascii=False) + "\n", encoding="utf-8")
    for name in ["semantic.jsonl", "procedural.jsonl", "reflections.jsonl", "truth_audits.jsonl", "affective.jsonl"]:
        (layered / name).touch()
    store = MemoryStore(tmp_path / "workspace_runtime" / "test.sqlite3")
    try:
        report = MemoryFileSync(tmp_path, store).synchronize_all(export=True)
        stats = store.stats()
    finally:
        store.close()
    assert report.imported["layered_episodic"] == 1
    assert stats["episodic_memories"] == 1
    assert (tmp_path / "memory" / "exported_from_sqlite" / "episodic_from_sqlite.jsonl").exists()
