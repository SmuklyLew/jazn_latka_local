from __future__ import annotations

from pathlib import Path
import sqlite3

from latka_jazn.config import JaznConfig
from latka_jazn.core.startup_contract import build_startup_status, cli_capabilities
from latka_jazn.memory.conversation_archive import ConversationArchiveStore


def _exec(path: Path, sql: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.executescript(sql)
        con.commit()


def _make_archive_tree(root: Path) -> None:
    base = root / "memory" / "sqlite"
    archive_dir = base / "conversation_archive_v1"
    fts_dir = base / "conversation_fts_v1"
    staging_dir = base / "staging_v1"
    archive = archive_dir / "conversation_archive_0001.sqlite3"
    fts = fts_dir / "conversation_fts_0001.sqlite3"
    staging = staging_dir / "staging_memory_0001.sqlite3"
    manifest = archive_dir / "conversation_archive_manifest.sqlite3"

    _exec(
        archive,
        """
        CREATE TABLE shard_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE content_blobs(
          content_hash TEXT PRIMARY KEY,
          normalized_hash TEXT NOT NULL,
          text TEXT NOT NULL,
          char_count INTEGER NOT NULL,
          byte_count INTEGER NOT NULL,
          first_occurrence_uid TEXT,
          first_source_uid TEXT,
          created_at_utc TEXT NOT NULL
        );
        CREATE TABLE archive_conversations(
          conversation_uid TEXT PRIMARY KEY,
          source_uid TEXT NOT NULL,
          conversation_index INTEGER NOT NULL,
          source_conversation_id TEXT,
          title TEXT,
          create_time TEXT,
          update_time TEXT,
          source_format TEXT,
          current_node TEXT,
          visible_node_count INTEGER NOT NULL DEFAULT 0,
          source_node_count INTEGER NOT NULL DEFAULT 0,
          message_count INTEGER NOT NULL DEFAULT 0,
          occurrence_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE archive_messages(
          message_uid TEXT PRIMARY KEY,
          conversation_uid TEXT NOT NULL,
          source_message_id TEXT,
          node_id TEXT,
          parent_node_id TEXT,
          role TEXT NOT NULL,
          author_label TEXT,
          model_slug TEXT,
          default_model_slug TEXT,
          content_type TEXT,
          create_time TEXT,
          is_visible_path INTEGER NOT NULL DEFAULT 1,
          visible_index INTEGER,
          content_hash TEXT NOT NULL,
          content_shard_id TEXT NOT NULL,
          normalized_hash TEXT NOT NULL,
          logical_hash TEXT NOT NULL,
          text_length INTEGER NOT NULL DEFAULT 0,
          first_source_uid TEXT NOT NULL,
          first_occurrence_uid TEXT NOT NULL,
          occurrence_count INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE archive_message_occurrences(
          occurrence_uid TEXT PRIMARY KEY,
          message_uid TEXT NOT NULL,
          conversation_uid TEXT NOT NULL,
          source_uid TEXT NOT NULL,
          source_conversation_id TEXT,
          source_message_id TEXT,
          node_id TEXT,
          parent_node_id TEXT,
          conversation_index INTEGER NOT NULL,
          message_index INTEGER NOT NULL,
          source_order INTEGER NOT NULL,
          is_visible_path INTEGER NOT NULL DEFAULT 1,
          visible_index INTEGER,
          source_locator TEXT NOT NULL,
          occurrence_hash TEXT NOT NULL,
          content_hash TEXT NOT NULL
        );
        INSERT INTO content_blobs VALUES(
          'hash-latka','norm-latka','Łatka pamięta rozmowę przez archive i FTS.',
          42,50,'occ-1','src-1','2026-06-19T00:00:00+00:00'
        );
        INSERT INTO archive_conversations VALUES(
          'conv-1','src-1',1,'source-conv-1','Test archive','1','2','chatgpt_jsondata_stream','node-1',2,2,1,1
        );
        INSERT INTO archive_messages VALUES(
          'msg-1','conv-1','source-msg-1','node-1','','assistant','ChatGPT','gpt-test','gpt-test','text',
          '2026-06-19T00:00:00+00:00',1,1,'hash-latka','archive_0001','norm-latka','logical-1',42,
          'src-1','occ-1',1
        );
        INSERT INTO archive_message_occurrences VALUES(
          'occ-1','msg-1','conv-1','src-1','source-conv-1','source-msg-1','node-1','',1,1,1,1,1,
          'chat_0.html#source-conv-1/node-1','occ-hash-1','hash-latka'
        );
        """,
    )

    _exec(
        staging,
        """
        CREATE TABLE shard_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE staging_memory_entries(
          staging_uid TEXT PRIMARY KEY,
          archive_message_uid TEXT NOT NULL,
          archive_occurrence_uid TEXT NOT NULL,
          conversation_uid TEXT NOT NULL,
          source_uid TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          normalized_hash TEXT NOT NULL,
          role TEXT NOT NULL,
          speaker_actor_id TEXT NOT NULL,
          interlocutor_actor_id TEXT,
          identity_confidence REAL NOT NULL,
          privacy_scope TEXT NOT NULL,
          memory_namespace TEXT NOT NULL,
          entry_type TEXT NOT NULL,
          create_time TEXT,
          time_confidence REAL NOT NULL,
          emotional_weight REAL NOT NULL,
          conversation_order INTEGER NOT NULL,
          context_before_message_uid TEXT,
          context_after_message_uid TEXT,
          review_status TEXT NOT NULL,
          canonical_candidate INTEGER NOT NULL DEFAULT 0,
          created_at_utc TEXT NOT NULL
        );
        CREATE TABLE staging_evidence(
          staging_uid TEXT NOT NULL,
          evidence_kind TEXT NOT NULL,
          archive_message_uid TEXT NOT NULL,
          archive_occurrence_uid TEXT NOT NULL,
          source_uid TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          evidence_weight REAL NOT NULL,
          PRIMARY KEY(staging_uid, evidence_kind, archive_occurrence_uid)
        );
        INSERT INTO staging_memory_entries VALUES(
          'stage-1','msg-1','occ-1','conv-1','src-1','hash-latka','norm-latka','assistant',
          'actor:assistant:chatgpt','actor:user:unknown',0.45,'private_local','latka.conversation.raw_import',
          'conversation_turn','2026-06-19T00:00:00+00:00',0.5,0.0,1,NULL,NULL,'unreviewed',0,
          '2026-06-19T00:00:00+00:00'
        );
        INSERT INTO staging_evidence VALUES('stage-1','source_occurrence','msg-1','occ-1','src-1','hash-latka',1.0);
        """,
    )

    _exec(
        fts,
        """
        CREATE TABLE shard_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE fts_docs(
          rowid INTEGER PRIMARY KEY,
          fts_doc_uid TEXT NOT NULL UNIQUE,
          staging_uid TEXT NOT NULL,
          archive_message_uid TEXT NOT NULL,
          archive_occurrence_uid TEXT NOT NULL,
          conversation_uid TEXT NOT NULL,
          source_uid TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          role TEXT NOT NULL,
          title TEXT,
          create_time TEXT
        );
        CREATE VIRTUAL TABLE message_fts USING fts5(
          content_text,
          title,
          role,
          tokenize='unicode61 remove_diacritics 1',
          content=''
        );
        INSERT INTO fts_docs VALUES(
          1,'ftsdoc-1','stage-1','msg-1','occ-1','conv-1','src-1','hash-latka','assistant',
          'Test archive','2026-06-19T00:00:00+00:00'
        );
        INSERT INTO message_fts(rowid,content_text,title,role)
        VALUES(1,'Łatka pamięta rozmowę przez archive i FTS.','Test archive','assistant');
        """,
    )

    _exec(
        manifest,
        f"""
        CREATE TABLE manifest_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE archive_sources(
          source_uid TEXT PRIMARY KEY,
          path TEXT NOT NULL,
          source_name TEXT NOT NULL,
          sha256 TEXT NOT NULL,
          size_bytes INTEGER NOT NULL,
          imported_at_utc TEXT NOT NULL,
          parser_version TEXT NOT NULL,
          source_kind TEXT NOT NULL
        );
        CREATE TABLE shard_files(
          shard_id TEXT PRIMARY KEY,
          family TEXT NOT NULL,
          ordinal INTEGER NOT NULL,
          relative_path TEXT NOT NULL,
          row_count INTEGER NOT NULL DEFAULT 0,
          size_bytes INTEGER,
          size_mib REAL,
          sha256 TEXT,
          integrity_check TEXT,
          foreign_key_error_count INTEGER,
          hard_limit_bytes INTEGER NOT NULL,
          over_limit INTEGER NOT NULL DEFAULT 0,
          created_at_utc TEXT NOT NULL
        );
        CREATE TABLE content_locations(
          content_hash TEXT PRIMARY KEY,
          normalized_hash TEXT NOT NULL,
          shard_id TEXT NOT NULL,
          char_count INTEGER NOT NULL,
          byte_count INTEGER NOT NULL,
          first_occurrence_uid TEXT,
          first_source_uid TEXT
        );
        CREATE TABLE conversation_locations(
          conversation_uid TEXT PRIMARY KEY,
          shard_id TEXT NOT NULL,
          first_source_uid TEXT,
          first_source_conversation_id TEXT,
          first_title TEXT
        );
        CREATE TABLE conversation_occurrence_locations(
          conversation_occurrence_uid TEXT PRIMARY KEY,
          conversation_uid TEXT NOT NULL,
          shard_id TEXT NOT NULL,
          source_uid TEXT NOT NULL,
          source_conversation_id TEXT,
          conversation_index INTEGER NOT NULL
        );
        CREATE TABLE message_locations(
          message_uid TEXT PRIMARY KEY,
          shard_id TEXT NOT NULL,
          conversation_uid TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          logical_hash TEXT NOT NULL,
          first_occurrence_uid TEXT,
          first_source_uid TEXT
        );
        CREATE TABLE occurrence_locations(
          occurrence_uid TEXT PRIMARY KEY,
          shard_id TEXT NOT NULL,
          message_uid TEXT NOT NULL,
          conversation_uid TEXT NOT NULL,
          source_uid TEXT NOT NULL,
          content_hash TEXT NOT NULL
        );
        CREATE TABLE staging_locations(
          staging_uid TEXT PRIMARY KEY,
          shard_id TEXT NOT NULL,
          message_uid TEXT NOT NULL,
          occurrence_uid TEXT NOT NULL,
          content_hash TEXT NOT NULL
        );
        CREATE TABLE fts_locations(
          fts_doc_uid TEXT PRIMARY KEY,
          shard_id TEXT NOT NULL,
          shard_rowid INTEGER NOT NULL,
          staging_uid TEXT NOT NULL,
          message_uid TEXT NOT NULL,
          content_hash TEXT NOT NULL
        );
        INSERT INTO manifest_meta VALUES('hard_limit_bytes','{480 * 1024 * 1024}');
        INSERT INTO archive_sources VALUES('src-1','memory/raw_chats/chat_0.html','chat_0.html','sha-source',123,'now','parser','chatgpt_html');
        INSERT INTO shard_files VALUES('archive_0001','archive',1,'conversation_archive_0001.sqlite3',1,NULL,NULL,NULL,'ok',0,{480 * 1024 * 1024},0,'now');
        INSERT INTO shard_files VALUES('fts_0001','fts',1,'conversation_fts_0001.sqlite3',1,NULL,NULL,NULL,'ok',0,{480 * 1024 * 1024},0,'now');
        INSERT INTO shard_files VALUES('staging_0001','staging',1,'staging_memory_0001.sqlite3',1,NULL,NULL,NULL,'ok',0,{480 * 1024 * 1024},0,'now');
        INSERT INTO content_locations VALUES('hash-latka','norm-latka','archive_0001',42,50,'occ-1','src-1');
        INSERT INTO conversation_locations VALUES('conv-1','archive_0001','src-1','source-conv-1','Test archive');
        INSERT INTO conversation_occurrence_locations VALUES('convocc-1','conv-1','archive_0001','src-1','source-conv-1',1);
        INSERT INTO message_locations VALUES('msg-1','archive_0001','conv-1','hash-latka','logical-1','occ-1','src-1');
        INSERT INTO occurrence_locations VALUES('occ-1','archive_0001','msg-1','conv-1','src-1','hash-latka');
        INSERT INTO staging_locations VALUES('stage-1','staging_0001','msg-1','occ-1','hash-latka');
        INSERT INTO fts_locations VALUES('ftsdoc-1','fts_0001',1,'stage-1','msg-1','hash-latka');
        """,
    )


def test_missing_conversation_archive_status(tmp_path: Path) -> None:
    status = ConversationArchiveStore(tmp_path).status()

    assert status.status == "missing"
    assert status.ready_for_search is False
    assert "conversation_archive_manifest_missing" in status.issues


def test_conversation_archive_status_and_search(tmp_path: Path) -> None:
    _make_archive_tree(tmp_path)

    store = ConversationArchiveStore(tmp_path)
    status = store.status()
    result = store.search("Łatka FTS", limit=3, include_snippets=True)

    assert status.status == "ready"
    assert status.counts["message_occurrences"] == 1
    assert status.counts["fts_locations"] == 1
    assert result.status == "ok"
    assert result.hits[0]["message_uid"] == "msg-1"
    assert result.hits[0]["source_name"] == "chat_0.html"
    assert result.hits[0]["source_locator"] == "chat_0.html#source-conv-1/node-1"
    assert "Łatka" in result.hits[0]["excerpt"]


def test_conversation_archive_search_repairs_common_powershell_mojibake(tmp_path: Path) -> None:
    _make_archive_tree(tmp_path)

    store = ConversationArchiveStore(tmp_path)
    result = store.search("Krzysztof \u0139\u0081atka pami\u00c4\u2122\u00c4\u2021", limit=3)

    assert result.status == "ok"
    assert result.query == "Krzysztof Łatka pamięć"
    assert result.input_query == "Krzysztof \u0139\u0081atka pami\u00c4\u2122\u00c4\u2021"
    assert '"łatka"' in result.fts_query
    assert result.hits[0]["message_uid"] == "msg-1"


def test_startup_status_exposes_conversation_archive_contract(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("# test start file\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text("v14.8.2.6.5-test\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}", encoding="utf-8")

    cfg = JaznConfig(root=tmp_path, version="v14.8.2.6.5-test", network_time_first=False)
    status = build_startup_status(cfg).to_dict()

    assert cli_capabilities()["--conversation-archive-status"] is True
    assert cli_capabilities()["--conversation-archive-search"] is True
    assert status["active_database"] == "memory/sqlite/conversation_archive_v1/conversation_archive_manifest.sqlite3"
    assert status["active_runtime_write_database"] == "memory/sqlite/runtime_write_v1/runtime_memory.sqlite3"
    assert status["storage_layout"] == "conversation_archive_v1+fts_v1+staging_v1+runtime_write_v1"
    assert status["conversation_archive_status"]["status"] == "missing"
    assert "latka_jazn/memory/conversation_archive.py" in status["runtime_contract_files"]


def test_v14831_archive_status_metadata_does_not_run_integrity_check(tmp_path: Path, monkeypatch) -> None:
    _make_archive_tree(tmp_path)
    calls: list[str] = []
    original = ConversationArchiveStore._health

    def wrapped(self, path, *, family, shard_id, hard_limit_bytes, health_mode="metadata"):
        calls.append(health_mode)
        assert health_mode != "deep"
        return original(self, path, family=family, shard_id=shard_id, hard_limit_bytes=hard_limit_bytes, health_mode=health_mode)

    monkeypatch.setattr(ConversationArchiveStore, "_health", wrapped)
    status = ConversationArchiveStore(tmp_path).status(health_mode="metadata")
    assert status.status == "ready"
    assert calls
    assert "deep" not in calls


def test_v14831_archive_status_deep_keeps_integrity_contract(tmp_path: Path) -> None:
    _make_archive_tree(tmp_path)
    status = ConversationArchiveStore(tmp_path).status(health_mode="deep")
    assert status.status == "ready"
    assert all(item["integrity_check"] == "ok" for item in status.files)
