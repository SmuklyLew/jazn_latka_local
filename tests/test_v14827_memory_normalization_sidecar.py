from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sqlite3

from latka_jazn.config import JaznConfig
from latka_jazn.core.startup_contract import build_startup_status, cli_capabilities
from latka_jazn.memory.normalization_sidecar import MemoryNormalizationSidecar


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_source_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.executescript(
            """
            CREATE TABLE messages(
              message_id TEXT PRIMARY KEY,
              conversation_id TEXT NOT NULL,
              conversation_title TEXT,
              role TEXT,
              timestamp TEXT,
              content_text TEXT,
              content_hash TEXT,
              first_source_file TEXT,
              first_source_sha256 TEXT,
              source_refs_json TEXT,
              created_at TEXT,
              updated_at TEXT
            );
            CREATE VIEW messages_user_assistant AS
              SELECT * FROM messages WHERE role IN ('user','assistant');
            CREATE VIEW active_conversation_messages AS
              SELECT * FROM messages WHERE role IN ('user','assistant');
            CREATE TABLE legacy_chunks(
              legacy_chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_sha256 TEXT NOT NULL,
              source_file TEXT NOT NULL,
              source_rel_path TEXT NOT NULL,
              chunk_index INTEGER NOT NULL,
              page_start INTEGER NOT NULL,
              page_end INTEGER NOT NULL,
              content_text TEXT NOT NULL,
              content_sha256 TEXT NOT NULL,
              char_count INTEGER NOT NULL,
              inferred_date TEXT,
              inferred_date_source TEXT NOT NULL,
              has_visible_timestamps INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE episodic_memories(
              episode_id TEXT PRIMARY KEY,
              created_at_utc TEXT NOT NULL,
              local_time_label TEXT,
              scene TEXT NOT NULL,
              participants_json TEXT NOT NULL DEFAULT '[]',
              emotional_anchor TEXT,
              source TEXT NOT NULL,
              grounding TEXT NOT NULL,
              confidence REAL NOT NULL,
              raw_excerpt TEXT,
              tags_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE semantic_facts(
              fact_id TEXT PRIMARY KEY,
              created_at_utc TEXT NOT NULL,
              subject TEXT NOT NULL,
              predicate TEXT NOT NULL,
              value TEXT NOT NULL,
              source TEXT NOT NULL,
              confidence REAL NOT NULL,
              tags_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE procedural_rules(
              rule_id TEXT PRIMARY KEY,
              created_at_utc TEXT NOT NULL,
              trigger TEXT NOT NULL,
              action TEXT NOT NULL,
              reason TEXT NOT NULL,
              priority INTEGER NOT NULL,
              source TEXT NOT NULL
            );
            CREATE TABLE reflection_entries(
              reflection_id TEXT PRIMARY KEY,
              created_at_utc TEXT NOT NULL,
              episode_id TEXT,
              meaning_for_latka TEXT NOT NULL,
              identity_impact TEXT NOT NULL,
              boundary_note TEXT NOT NULL,
              next_question TEXT,
              confidence REAL NOT NULL
            );
            CREATE TABLE truth_audits(
              audit_id TEXT PRIMARY KEY,
              created_at_utc TEXT NOT NULL,
              text TEXT NOT NULL,
              audit_json TEXT NOT NULL
            );
            """
        )
        con.execute(
            """INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "m-user",
                "conv-1",
                "Test rozmowy",
                "user",
                "2026-06-18T01:00:00+00:00",
                "Pytanie użytkownika o pamięć Łatki.",
                "h-user",
                "chat_0.html",
                "sha-source",
                json.dumps([{"source_file": "chat_0.html", "source_sha256": "sha-source"}]),
                "2026-06-18T01:00:00+00:00",
                "2026-06-18T01:00:00+00:00",
            ),
        )
        con.execute(
            """INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "m-assistant",
                "conv-1",
                "Test rozmowy",
                "assistant",
                "2026-06-18T01:01:00+00:00",
                "Odpowiedź Łatki z granicą prawdy.",
                "h-assistant",
                "chat_0.html",
                "sha-source",
                json.dumps([{"source_file": "chat_0.html", "source_sha256": "sha-source"}]),
                "2026-06-18T01:01:00+00:00",
                "2026-06-18T01:01:00+00:00",
            ),
        )
        con.execute(
            """INSERT INTO legacy_chunks(source_sha256,source_file,source_rel_path,chunk_index,page_start,page_end,content_text,content_sha256,char_count,inferred_date,inferred_date_source)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            ("sha-legacy", "legacy.txt", "legacy.txt", 0, 1, 1, "Odzyskany fragment starej rozmowy.", "chunk-hash", 34, "2026-06-17", "test"),
        )
        con.execute(
            """INSERT INTO episodic_memories VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "ep-1",
                "2026-06-18T01:02:00+00:00",
                "2026-06-18",
                "Krzysztof i Łatka rozmawiają o prawdzie pamięci.",
                json.dumps(["Krzysztof", "Łatka"], ensure_ascii=False),
                "uważność",
                "test",
                "curated",
                0.8,
                "raw excerpt",
                "[]",
            ),
        )


def test_dry_run_does_not_create_sidecar(tmp_path: Path) -> None:
    source = tmp_path / "memory" / "sqlite" / "chat_context.sqlite3"
    audit = tmp_path / "memory" / "sqlite" / "chat_context_audit.sqlite3"
    _make_source_db(source)
    sidecar = MemoryNormalizationSidecar(tmp_path, source_db_path=source, sidecar_db_path=audit, runtime_version="test")

    report = sidecar.normalize(dry_run=True)

    assert report.status == "dry_run_ok"
    assert report.output_counts["normalized_memory_items"] >= 4
    assert not audit.exists()
    assert sidecar.status().status == "sidecar_missing"


def test_normalization_writes_sidecar_without_modifying_source(tmp_path: Path) -> None:
    source = tmp_path / "memory" / "sqlite" / "chat_context.sqlite3"
    audit = tmp_path / "memory" / "sqlite" / "chat_context_audit.sqlite3"
    _make_source_db(source)
    before = _sha(source)
    sidecar = MemoryNormalizationSidecar(tmp_path, source_db_path=source, sidecar_db_path=audit, runtime_version="test")

    report = sidecar.normalize(limit=4)

    assert report.status == "ok"
    assert _sha(source) == before
    assert sidecar.status().status == "ready"
    with sqlite3.connect(audit) as con:
        con.row_factory = sqlite3.Row
        assert con.execute("SELECT COUNT(*) FROM actors").fetchone()[0] == 3
        assert con.execute("SELECT COUNT(*) FROM normalized_memory_items").fetchone()[0] == 4
        user_item = con.execute(
            "SELECT * FROM normalized_memory_items WHERE message_id='m-user'"
        ).fetchone()
        assert user_item["speaker_actor_id"] == "interlocutor_unknown"
        assert user_item["interlocutor_actor_id"] == "latka"
        assert user_item["memory_namespace"] == "dialogue_general_unverified"


def test_wake_state_uses_sidecar_and_keeps_private_namespace_locked(tmp_path: Path) -> None:
    source = tmp_path / "memory" / "sqlite" / "chat_context.sqlite3"
    audit = tmp_path / "memory" / "sqlite" / "chat_context_audit.sqlite3"
    _make_source_db(source)
    sidecar = MemoryNormalizationSidecar(tmp_path, source_db_path=source, sidecar_db_path=audit, runtime_version="test")
    sidecar.normalize(limit=4)

    dry = sidecar.build_wake_state(dry_run=True)
    assert dry.status == "dry_run_ok"
    assert dry.snapshot
    assert "recent_events" not in dry.snapshot
    assert "open_threads" not in dry.snapshot
    assert dry.snapshot["relationship_digest"]["krzysztof_candidate_present"] is True
    assert dry.snapshot["relationship_digest"]["krzysztof_private_namespace_allowed"] is False
    assert sidecar.wake_state_status().status == "no_active_wake_state"

    report = sidecar.build_wake_state()

    assert report.status == "ok"
    status = sidecar.wake_state_status()
    assert status.status == "ready"
    assert status.active_snapshot
    assert status.active_snapshot["validation_status"] == "valid"
    assert "recent_events" not in status.active_snapshot
    assert "open_threads" not in status.active_snapshot


def test_layered_dedupe_marks_duplicates_without_deleting_items(tmp_path: Path) -> None:
    source = tmp_path / "memory" / "sqlite" / "chat_context.sqlite3"
    audit = tmp_path / "memory" / "sqlite" / "chat_context_audit.sqlite3"
    _make_source_db(source)
    with sqlite3.connect(source) as con:
        con.execute(
            """INSERT INTO legacy_chunks(source_sha256,source_file,source_rel_path,chunk_index,page_start,page_end,content_text,content_sha256,char_count,inferred_date,inferred_date_source)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            ("sha-legacy-2", "legacy-copy.txt", "legacy-copy.txt", 1, 1, 1, "Odzyskany fragment starej rozmowy.", "chunk-hash-2", 34, "2026-06-17", "test"),
        )
        con.commit()

    sidecar = MemoryNormalizationSidecar(tmp_path, source_db_path=source, sidecar_db_path=audit, runtime_version="test")
    sidecar.normalize()
    before_count = sidecar.status().sidecar_counts["normalized_memory_items"]

    dry = sidecar.build_layered_dedupe(dry_run=True)
    assert dry.status == "dry_run_ok"
    assert dry.layer_counts["exact_text"]["duplicate_groups"] >= 1
    assert dry.layer_counts["typed_text"]["duplicate_groups"] >= 1
    assert dry.layer_counts["contextual_safe"]["duplicate_groups"] >= 1

    report = sidecar.build_layered_dedupe()

    assert report.status == "ok"
    assert sidecar.status().sidecar_counts["normalized_memory_items"] == before_count
    with sqlite3.connect(audit) as con:
        assert con.execute("SELECT COUNT(*) FROM layered_dedupe_runs").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM layered_dedupe_groups WHERE layer='contextual_safe'").fetchone()[0] >= 1
        assert con.execute("SELECT COUNT(*) FROM layered_dedupe_members").fetchone()[0] >= 2


def test_startup_status_exposes_normalization_and_wake_state_contracts(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("# test start file\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text("test\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}", encoding="utf-8")

    cfg = JaznConfig(root=tmp_path, version="test", network_time_first=False)
    status = build_startup_status(cfg).to_dict()

    assert cli_capabilities()["--memory-normalization-status"] is True
    assert cli_capabilities()["--normalize-memory-sidecar"] is True
    assert cli_capabilities()["--wake-state-status"] is True
    assert cli_capabilities()["--build-wake-state"] is True
    assert cli_capabilities()["--dedupe-memory-sidecar"] is True
    assert status["memory_normalization_status"]["status"] == "source_missing"
    assert status["wake_state_status"]["status"] == "sidecar_missing"
    assert "latka_jazn/memory/normalization_sidecar.py" in status["runtime_contract_files"]
