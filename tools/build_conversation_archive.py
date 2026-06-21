#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from latka_jazn.memory.chat_html_importer import iter_chatgpt_export_conversations, sha256_file, visible_path
from tools.html_conversations_to_simple_sqlite import author_label, extract_full_text, role_from_author


SCRIPT_VERSION = "conversation_archive_builder/v1"
DEFAULT_HARD_LIMIT_MIB = 480
DEFAULT_ARCHIVE_SOFT_MIB = 220
DEFAULT_FTS_SOFT_MIB = 160
DEFAULT_STAGING_SOFT_MIB = 180
DEFAULT_NAMESPACE = "latka.conversation.raw_import"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def mib(value: int) -> float:
    return value / 1024 / 1024


def bytes_from_mib(value: int | float) -> int:
    return int(float(value) * 1024 * 1024)


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2)


def compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def uid(prefix: str, *parts: Any, length: int = 32) -> str:
    seed = "\x1f".join("" if item is None else str(item) for item in parts)
    return f"{prefix}_{sha256_text(seed)[:length]}"


def normalize_text(text: str) -> str:
    return " ".join((text or "").replace("\r\n", "\n").replace("\r", "\n").split())


def safe_str(value: Any) -> str:
    return "" if value is None else str(value)


def parse_roles(value: str) -> set[str] | None:
    value = value.strip().lower()
    if value == "all":
        return None
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def sqlite_open(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=DELETE")
    con.execute("PRAGMA synchronous=OFF")
    con.execute("PRAGMA temp_store=MEMORY")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def sqlite_open_ro(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    return con


def finalize_sqlite(path: Path, *, hard_limit_bytes: int) -> dict[str, Any]:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("VACUUM")
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        fk_count = len(con.execute("PRAGMA foreign_key_check").fetchall())
    finally:
        con.close()
    size = path.stat().st_size
    return {
        "path": str(path),
        "size_bytes": size,
        "size_mib": round(mib(size), 2),
        "sha256": sha256_file(path),
        "integrity_check": integrity,
        "foreign_key_error_count": fk_count,
        "over_limit": size > hard_limit_bytes,
    }


def require_inside_root(path: Path) -> Path:
    resolved = path.resolve()
    root = ROOT.resolve()
    if not str(resolved).lower().startswith(str(root).lower()):
        raise SystemExit(f"Refusing to write outside project root: {resolved}")
    return resolved


def clean_dir(path: Path, *, force: bool) -> None:
    path = require_inside_root(path)
    if path.exists() and any(path.iterdir()):
        if not force:
            raise SystemExit(f"Output directory exists and is not empty: {path}. Use --force or choose a new path.")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


@dataclass
class Progress:
    enabled: bool
    total_source_bytes: int
    completed_source_bytes: int = 0
    messages: int = 0
    conversations: int = 0
    started: float = field(default_factory=time.time)
    last_percent: int = -1

    def source_started(self, source_name: str) -> None:
        if self.enabled:
            print(f"[progress] source started: {source_name}", file=sys.stderr)

    def tick(self, *, conversations: int = 0, messages: int = 0) -> None:
        self.conversations += conversations
        self.messages += messages
        if self.enabled and self.messages and self.messages % 1000 == 0:
            elapsed = time.time() - self.started
            print(
                f"[progress] messages={self.messages} conversations={self.conversations} elapsed={elapsed:.1f}s",
                file=sys.stderr,
            )

    def source_finished(self, source_name: str, size_bytes: int) -> None:
        self.completed_source_bytes += size_bytes
        if not self.enabled or self.total_source_bytes <= 0:
            return
        percent = min(100, int((self.completed_source_bytes / self.total_source_bytes) * 100))
        if percent != self.last_percent:
            elapsed = time.time() - self.started
            print(
                f"[{percent:3d}%] source finished: {source_name} messages={self.messages} elapsed={elapsed:.1f}s",
                file=sys.stderr,
            )
            self.last_percent = percent


class Manifest:
    def __init__(self, path: Path, *, hard_limit_bytes: int, args: argparse.Namespace) -> None:
        self.path = path
        self.hard_limit_bytes = hard_limit_bytes
        self.con = sqlite_open(path)
        self._create_schema()
        self.add_meta(args)

    def _create_schema(self) -> None:
        self.con.executescript(
            """
            CREATE TABLE manifest_meta(
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
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
            CREATE INDEX idx_shards_family ON shard_files(family);
            CREATE INDEX idx_conv_occ_conv ON conversation_occurrence_locations(conversation_uid);
            CREATE INDEX idx_occ_message ON occurrence_locations(message_uid);
            CREATE INDEX idx_stage_message ON staging_locations(message_uid);
            CREATE INDEX idx_fts_message ON fts_locations(message_uid);
            """
        )

    def add_meta(self, args: argparse.Namespace) -> None:
        rows = {
            "script_version": SCRIPT_VERSION,
            "created_at_utc": now_utc(),
            "truth_boundary": "Conversation archive is source-backed storage. FTS is a rebuildable search index. Staging is not canonical memory.",
            "hard_limit_bytes": str(self.hard_limit_bytes),
            "roles": args.roles,
            "visible_only": str(not args.all_nodes),
            "include_blank": str(args.include_blank),
            "archive_soft_mib": str(args.archive_soft_mib),
            "fts_soft_mib": str(args.fts_soft_mib),
            "staging_soft_mib": str(args.staging_soft_mib),
        }
        self.con.executemany("INSERT OR REPLACE INTO manifest_meta(key,value) VALUES(?,?)", rows.items())
        self.con.commit()

    def add_source(self, source: dict[str, Any]) -> None:
        self.con.execute(
            """INSERT OR REPLACE INTO archive_sources
               (source_uid,path,source_name,sha256,size_bytes,imported_at_utc,parser_version,source_kind)
               VALUES(?,?,?,?,?,?,?,?)""",
            (
                source["source_uid"],
                source["path"],
                source["source_name"],
                source["sha256"],
                source["size_bytes"],
                source["imported_at_utc"],
                source["parser_version"],
                source["source_kind"],
            ),
        )

    def add_shard(self, info: dict[str, Any], *, shard_id: str, family: str, ordinal: int, relative_path: str, row_count: int) -> None:
        self.con.execute(
            """INSERT OR REPLACE INTO shard_files
               (shard_id,family,ordinal,relative_path,row_count,size_bytes,size_mib,sha256,integrity_check,
                foreign_key_error_count,hard_limit_bytes,over_limit,created_at_utc)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                shard_id,
                family,
                ordinal,
                relative_path,
                row_count,
                info["size_bytes"],
                info["size_mib"],
                info["sha256"],
                info["integrity_check"],
                info["foreign_key_error_count"],
                self.hard_limit_bytes,
                1 if info["over_limit"] else 0,
                now_utc(),
            ),
        )

    def add_content_location(
        self,
        *,
        content_hash: str,
        normalized_hash: str,
        shard_id: str,
        char_count: int,
        byte_count: int,
        occurrence_uid: str,
        source_uid: str,
    ) -> None:
        self.con.execute(
            """INSERT OR IGNORE INTO content_locations
               (content_hash,normalized_hash,shard_id,char_count,byte_count,first_occurrence_uid,first_source_uid)
               VALUES(?,?,?,?,?,?,?)""",
            (content_hash, normalized_hash, shard_id, char_count, byte_count, occurrence_uid, source_uid),
        )

    def add_conversation_location(
        self,
        *,
        conversation_uid: str,
        shard_id: str,
        source_uid: str,
        source_conversation_id: str,
        title: str,
    ) -> None:
        self.con.execute(
            """INSERT OR IGNORE INTO conversation_locations
               (conversation_uid,shard_id,first_source_uid,first_source_conversation_id,first_title)
               VALUES(?,?,?,?,?)""",
            (conversation_uid, shard_id, source_uid, source_conversation_id, title),
        )

    def add_conversation_occurrence_location(
        self,
        *,
        conversation_occurrence_uid: str,
        conversation_uid: str,
        shard_id: str,
        source_uid: str,
        source_conversation_id: str,
        conversation_index: int,
    ) -> None:
        self.con.execute(
            """INSERT OR REPLACE INTO conversation_occurrence_locations
               (conversation_occurrence_uid,conversation_uid,shard_id,source_uid,source_conversation_id,conversation_index)
               VALUES(?,?,?,?,?,?)""",
            (conversation_occurrence_uid, conversation_uid, shard_id, source_uid, source_conversation_id, conversation_index),
        )

    def add_message_location(
        self,
        *,
        message_uid: str,
        shard_id: str,
        conversation_uid: str,
        content_hash: str,
        logical_hash: str,
        occurrence_uid: str,
        source_uid: str,
    ) -> None:
        self.con.execute(
            """INSERT OR IGNORE INTO message_locations
               (message_uid,shard_id,conversation_uid,content_hash,logical_hash,first_occurrence_uid,first_source_uid)
               VALUES(?,?,?,?,?,?,?)""",
            (message_uid, shard_id, conversation_uid, content_hash, logical_hash, occurrence_uid, source_uid),
        )

    def add_occurrence_location(
        self,
        *,
        occurrence_uid: str,
        shard_id: str,
        message_uid: str,
        conversation_uid: str,
        source_uid: str,
        content_hash: str,
    ) -> None:
        self.con.execute(
            """INSERT OR REPLACE INTO occurrence_locations
               (occurrence_uid,shard_id,message_uid,conversation_uid,source_uid,content_hash)
               VALUES(?,?,?,?,?,?)""",
            (occurrence_uid, shard_id, message_uid, conversation_uid, source_uid, content_hash),
        )

    def add_staging_location(self, *, staging_uid: str, shard_id: str, message_uid: str, occurrence_uid: str, content_hash: str) -> None:
        self.con.execute(
            """INSERT OR REPLACE INTO staging_locations
               (staging_uid,shard_id,message_uid,occurrence_uid,content_hash)
               VALUES(?,?,?,?,?)""",
            (staging_uid, shard_id, message_uid, occurrence_uid, content_hash),
        )

    def add_fts_location(
        self,
        *,
        fts_doc_uid: str,
        shard_id: str,
        shard_rowid: int,
        staging_uid: str,
        message_uid: str,
        content_hash: str,
    ) -> None:
        self.con.execute(
            """INSERT OR REPLACE INTO fts_locations
               (fts_doc_uid,shard_id,shard_rowid,staging_uid,message_uid,content_hash)
               VALUES(?,?,?,?,?,?)""",
            (fts_doc_uid, shard_id, shard_rowid, staging_uid, message_uid, content_hash),
        )

    def commit(self) -> None:
        self.con.commit()

    def close(self) -> None:
        self.con.commit()
        self.con.close()


ARCHIVE_SCHEMA = """
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
CREATE TABLE archive_conversation_occurrences(
  conversation_occurrence_uid TEXT PRIMARY KEY,
  conversation_uid TEXT NOT NULL,
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
  kept_message_count INTEGER NOT NULL DEFAULT 0
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
CREATE INDEX idx_archive_conv_source ON archive_conversations(source_uid, conversation_index);
CREATE INDEX idx_archive_conv_occ_conv ON archive_conversation_occurrences(conversation_uid);
CREATE INDEX idx_archive_conv_occ_source ON archive_conversation_occurrences(source_uid, conversation_index);
CREATE INDEX idx_archive_msg_conv ON archive_messages(conversation_uid);
CREATE INDEX idx_archive_msg_hash ON archive_messages(content_hash);
CREATE INDEX idx_archive_occ_msg ON archive_message_occurrences(message_uid);
CREATE INDEX idx_archive_occ_source ON archive_message_occurrences(source_uid, source_order);
"""


STAGING_SCHEMA = """
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
CREATE INDEX idx_staging_message ON staging_memory_entries(archive_message_uid);
CREATE INDEX idx_staging_occurrence ON staging_memory_entries(archive_occurrence_uid);
CREATE INDEX idx_staging_hash ON staging_memory_entries(content_hash);
CREATE INDEX idx_staging_conversation ON staging_memory_entries(conversation_uid, conversation_order);
CREATE INDEX idx_staging_evidence_message ON staging_evidence(archive_message_uid);
"""


FTS_SCHEMA = """
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
CREATE INDEX idx_fts_docs_staging ON fts_docs(staging_uid);
CREATE INDEX idx_fts_docs_message ON fts_docs(archive_message_uid);
CREATE INDEX idx_fts_docs_hash ON fts_docs(content_hash);
"""


class ShardWriter:
    def __init__(
        self,
        *,
        family: str,
        output_dir: Path,
        file_prefix: str,
        schema_sql: str,
        manifest: Manifest,
        soft_limit_bytes: int,
        hard_limit_bytes: int,
    ) -> None:
        self.family = family
        self.output_dir = output_dir
        self.file_prefix = file_prefix
        self.schema_sql = schema_sql
        self.manifest = manifest
        self.soft_limit_bytes = soft_limit_bytes
        self.hard_limit_bytes = hard_limit_bytes
        self.ordinal = 0
        self.con: sqlite3.Connection | None = None
        self.path: Path | None = None
        self.shard_id = ""
        self.estimated_bytes = 0
        self.row_count = 0
        self.generated: list[dict[str, Any]] = []
        self._open_new()

    def _open_new(self) -> None:
        self.ordinal += 1
        self.shard_id = f"{self.family}_{self.ordinal:04d}"
        self.path = self.output_dir / f"{self.file_prefix}_{self.ordinal:04d}.sqlite3"
        self.con = sqlite_open(self.path)
        self.con.executescript(self.schema_sql)
        meta = {
            "script_version": SCRIPT_VERSION,
            "created_at_utc": now_utc(),
            "family": self.family,
            "shard_id": self.shard_id,
            "truth_boundary": "Derived storage. FTS is rebuildable; staging is not canonical memory.",
        }
        self.con.executemany("INSERT INTO shard_meta(key,value) VALUES(?,?)", meta.items())
        self.con.commit()
        self.estimated_bytes = 0
        self.row_count = 0

    def ensure_room(self, estimated_bytes: int) -> None:
        if self.row_count > 0 and self.estimated_bytes + max(estimated_bytes, 1) > self.soft_limit_bytes:
            self.finish_current()
            self._open_new()

    def execute(self, sql: str, params: Iterable[Any], *, estimated_bytes: int = 256, count_row: bool = True) -> None:
        self.ensure_room(estimated_bytes)
        assert self.con is not None
        self.con.execute(sql, tuple(params))
        self.estimated_bytes += max(estimated_bytes, 1)
        if count_row:
            self.row_count += 1
        if self.row_count and self.row_count % 1000 == 0:
            self.con.commit()

    def finish_current(self) -> None:
        if self.con is None or self.path is None:
            return
        self.con.commit()
        self.con.close()
        info = finalize_sqlite(self.path, hard_limit_bytes=self.hard_limit_bytes)
        rel = self.path.relative_to(self.output_dir).as_posix()
        self.manifest.add_shard(
            info,
            shard_id=self.shard_id,
            family=self.family,
            ordinal=self.ordinal,
            relative_path=rel,
            row_count=self.row_count,
        )
        self.generated.append({"shard_id": self.shard_id, "family": self.family, "row_count": self.row_count, **info})
        self.con = None

    def close(self) -> None:
        self.finish_current()


class FtsShardWriter(ShardWriter):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.rowid = 0

    def _open_new(self) -> None:
        super()._open_new()
        self.rowid = 0

    def insert_doc(
        self,
        *,
        fts_doc_uid: str,
        staging_uid: str,
        message_uid: str,
        occurrence_uid: str,
        conversation_uid: str,
        source_uid: str,
        content_hash: str,
        role: str,
        title: str,
        create_time: str,
        text: str,
        manifest: Manifest,
    ) -> None:
        estimated = len(text.encode("utf-8", errors="replace")) + len(title.encode("utf-8", errors="replace")) + 512
        self.ensure_room(estimated)
        assert self.con is not None
        self.rowid += 1
        self.con.execute(
            """INSERT INTO fts_docs
               (rowid,fts_doc_uid,staging_uid,archive_message_uid,archive_occurrence_uid,conversation_uid,
                source_uid,content_hash,role,title,create_time)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                self.rowid,
                fts_doc_uid,
                staging_uid,
                message_uid,
                occurrence_uid,
                conversation_uid,
                source_uid,
                content_hash,
                role,
                title,
                create_time,
            ),
        )
        self.con.execute("INSERT INTO message_fts(rowid,content_text,title,role) VALUES(?,?,?,?)", (self.rowid, text, title, role))
        manifest.add_fts_location(
            fts_doc_uid=fts_doc_uid,
            shard_id=self.shard_id,
            shard_rowid=self.rowid,
            staging_uid=staging_uid,
            message_uid=message_uid,
            content_hash=content_hash,
        )
        self.estimated_bytes += estimated
        self.row_count += 1
        if self.row_count % 1000 == 0:
            self.con.commit()


@dataclass(slots=True)
class Counters:
    sources: int = 0
    conversations: int = 0
    conversation_occurrences: int = 0
    nodes_seen: int = 0
    messages_kept: int = 0
    messages_skipped: int = 0
    blank_skipped: int = 0
    content_blobs: int = 0
    logical_messages: int = 0
    occurrences: int = 0
    staging_entries: int = 0
    fts_docs: int = 0


def source_records(sources: Iterable[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source in sources:
        path = Path(source).resolve()
        if not path.exists():
            raise SystemExit(f"Source not found: {path}")
        sha = sha256_file(path)
        records.append(
            {
                "source_uid": f"src_{sha[:24]}",
                "path": str(path),
                "source_name": path.name,
                "sha256": sha,
                "size_bytes": path.stat().st_size,
                "imported_at_utc": now_utc(),
                "parser_version": "chat_html_importer.iter_chatgpt_export_conversations",
                "source_kind": "chatgpt_html",
            }
        )
    return records


def source_order_key(source: Path) -> tuple[str, str]:
    return (source.parent.as_posix().lower(), source.name.lower())


def default_sources() -> list[Path]:
    raw_dir = ROOT / "memory" / "raw_chats"
    return sorted(raw_dir.glob("*.html"), key=source_order_key)


def logical_key_for_message(
    *,
    source_conversation_id: str,
    source_message_id: str,
    node_id: str,
    parent_node_id: str,
    role: str,
    create_time: str,
    content_hash: str,
) -> str:
    if source_message_id:
        return f"source_message_id:{source_message_id}"
    if source_conversation_id and node_id:
        return f"conversation_node:{source_conversation_id}:{node_id}"
    return f"fallback:{source_conversation_id}:{parent_node_id}:{role}:{create_time}:{content_hash}"


def actor_ids(role: str, label: str | None) -> tuple[str, str | None, float]:
    label_norm = normalize_text(label or role or "unknown").lower().replace(" ", "_")[:80] or "unknown"
    if role == "assistant":
        return (f"actor:assistant:{label_norm}", "actor:user:unknown", 0.45)
    if role == "user":
        return ("actor:user:unknown", "actor:assistant:unknown", 0.2)
    return (f"actor:{role or 'unknown'}:{label_norm}", None, 0.1)


def should_keep(role: str, text: str, roles: set[str] | None, include_blank: bool) -> tuple[bool, str]:
    if roles is not None and role not in roles:
        return False, "role_filtered"
    if not include_blank and not text.strip():
        return False, "blank_text"
    return True, ""


def compare_simple_db(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    con = sqlite_open_ro(path)
    try:
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"sources", "conversations", "messages"}.issubset(tables):
            return {"path": str(path), "status": "unsupported_schema"}
        duplicate_text_surplus = con.execute(
            """
            SELECT COALESCE(SUM(cnt-1),0)
              FROM (SELECT text, COUNT(*) AS cnt FROM messages GROUP BY text HAVING cnt > 1)
            """
        ).fetchone()[0]
        duplicate_source_message_id_surplus = con.execute(
            """
            SELECT COALESCE(SUM(cnt-1),0)
              FROM (
                    SELECT source_message_id, COUNT(*) AS cnt
                      FROM messages
                     WHERE COALESCE(source_message_id,'') <> ''
                     GROUP BY source_message_id
                    HAVING cnt > 1
                   )
            """
        ).fetchone()[0]
        return {
            "path": str(path),
            "status": "ok",
            "sources": con.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
            "conversations": con.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
            "messages": con.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
            "blank_messages": con.execute("SELECT COUNT(*) FROM messages WHERE COALESCE(TRIM(text),'')=''").fetchone()[0],
            "distinct_texts": con.execute("SELECT COUNT(DISTINCT text) FROM messages").fetchone()[0],
            "duplicate_text_surplus": int(duplicate_text_surplus or 0),
            "duplicate_source_message_id_surplus": int(duplicate_source_message_id_surplus or 0),
        }
    finally:
        con.close()


def build_outputs(args: argparse.Namespace) -> dict[str, Any]:
    sources = [Path(item) for item in args.source] if args.source else default_sources()
    if not sources:
        raise SystemExit("No HTML sources found. Pass --source or place files in memory/raw_chats.")

    output_root = require_inside_root(Path(args.output_root))
    archive_dir = output_root / "conversation_archive_v1"
    fts_dir = output_root / "conversation_fts_v1"
    staging_dir = output_root / "staging_v1"
    for path in (archive_dir, fts_dir, staging_dir):
        clean_dir(path, force=args.force)

    hard_limit_bytes = bytes_from_mib(args.hard_limit_mib)
    archive_soft_bytes = bytes_from_mib(args.archive_soft_mib)
    fts_soft_bytes = bytes_from_mib(args.fts_soft_mib)
    staging_soft_bytes = bytes_from_mib(args.staging_soft_mib)

    manifest_path = archive_dir / "conversation_archive_manifest.sqlite3"
    manifest = Manifest(manifest_path, hard_limit_bytes=hard_limit_bytes, args=args)

    source_info = source_records(sources)
    for source in source_info:
        manifest.add_source(source)
    manifest.commit()

    total_source_bytes = sum(item["size_bytes"] for item in source_info)
    progress = Progress(enabled=not args.no_progress, total_source_bytes=total_source_bytes)

    archive = ShardWriter(
        family="archive",
        output_dir=archive_dir,
        file_prefix="conversation_archive",
        schema_sql=ARCHIVE_SCHEMA,
        manifest=manifest,
        soft_limit_bytes=archive_soft_bytes,
        hard_limit_bytes=hard_limit_bytes,
    )
    staging = ShardWriter(
        family="staging",
        output_dir=staging_dir,
        file_prefix="staging_memory",
        schema_sql=STAGING_SCHEMA,
        manifest=manifest,
        soft_limit_bytes=staging_soft_bytes,
        hard_limit_bytes=hard_limit_bytes,
    )
    fts = FtsShardWriter(
        family="fts",
        output_dir=fts_dir,
        file_prefix="conversation_fts",
        schema_sql=FTS_SCHEMA,
        manifest=manifest,
        soft_limit_bytes=fts_soft_bytes,
        hard_limit_bytes=hard_limit_bytes,
    )

    roles = parse_roles(args.roles)
    counters = Counters()
    known_content: set[str] = set()
    known_messages: set[str] = set()
    known_conversations: set[str] = set()
    content_shard_by_hash: dict[str, str] = {}
    previous_message_by_conversation: dict[str, str] = {}

    source_by_path = {Path(item["path"]).resolve(): item for item in source_info}

    for source_path in sources:
        source_path = Path(source_path).resolve()
        source = source_by_path[source_path]
        source_uid = source["source_uid"]
        counters.sources += 1
        progress.source_started(source_path.name)
        source_order = 0
        for conv_index, conv in enumerate(iter_chatgpt_export_conversations(source_path), start=1):
            if args.limit_conversations is not None and conv_index > args.limit_conversations:
                break
            counters.conversations += 1
            progress.tick(conversations=1)
            source_conversation_id = safe_str(conv.get("conversation_id") or conv.get("id") or "")
            conversation_uid = uid("conv", source_conversation_id or source_uid, source_conversation_id or conv_index)
            mapping = conv.get("mapping") or {}
            current_node = conv.get("current_node")
            visible_nodes_list = visible_path(mapping, current_node)
            visible_nodes = set(str(item) for item in visible_nodes_list)
            visible_index = {str(node_id): index for index, node_id in enumerate(visible_nodes_list)}
            node_ids = visible_nodes_list if visible_nodes_list and not args.all_nodes else list(mapping.keys())
            title = safe_str(conv.get("title") or "")
            conversation_occurrence_uid = uid(
                "convocc",
                source_uid,
                source_conversation_id or conv_index,
                conv_index,
                title,
            )

            if conversation_uid not in known_conversations:
                archive.execute(
                    """INSERT OR IGNORE INTO archive_conversations
                       (conversation_uid,source_uid,conversation_index,source_conversation_id,title,create_time,update_time,
                        source_format,current_node,visible_node_count,source_node_count,message_count,occurrence_count)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,0,0)""",
                    (
                        conversation_uid,
                        source_uid,
                        conv_index,
                        source_conversation_id,
                        title,
                        safe_str(conv.get("create_time")),
                        safe_str(conv.get("update_time")),
                        safe_str(conv.get("source_format") or "chatgpt_jsondata_stream"),
                        safe_str(current_node),
                        len(visible_nodes_list),
                        len(mapping),
                    ),
                    estimated_bytes=len(title.encode("utf-8", errors="replace")) + 512,
                )
                manifest.add_conversation_location(
                    conversation_uid=conversation_uid,
                    shard_id=archive.shard_id,
                    source_uid=source_uid,
                    source_conversation_id=source_conversation_id,
                    title=title,
                )
                known_conversations.add(conversation_uid)

            archive.execute(
                """INSERT OR REPLACE INTO archive_conversation_occurrences
                   (conversation_occurrence_uid,conversation_uid,source_uid,conversation_index,source_conversation_id,
                    title,create_time,update_time,source_format,current_node,visible_node_count,source_node_count,kept_message_count)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,0)""",
                (
                    conversation_occurrence_uid,
                    conversation_uid,
                    source_uid,
                    conv_index,
                    source_conversation_id,
                    title,
                    safe_str(conv.get("create_time")),
                    safe_str(conv.get("update_time")),
                    safe_str(conv.get("source_format") or "chatgpt_jsondata_stream"),
                    safe_str(current_node),
                    len(visible_nodes_list),
                    len(mapping),
                ),
                estimated_bytes=len(title.encode("utf-8", errors="replace")) + 512,
            )
            manifest.add_conversation_occurrence_location(
                conversation_occurrence_uid=conversation_occurrence_uid,
                conversation_uid=conversation_uid,
                shard_id=archive.shard_id,
                source_uid=source_uid,
                source_conversation_id=source_conversation_id,
                conversation_index=conv_index,
            )
            counters.conversation_occurrences += 1

            message_index = 0
            for raw_node_id in node_ids:
                node_id = str(raw_node_id)
                node = mapping.get(raw_node_id) or mapping.get(node_id) or {}
                msg = node.get("message") if isinstance(node, dict) else None
                counters.nodes_seen += 1
                if not isinstance(msg, dict):
                    counters.messages_skipped += 1
                    continue
                author = msg.get("author") or {}
                metadata = msg.get("metadata") or {}
                content = msg.get("content") or {}
                role = role_from_author(author, metadata)
                text, text_length = extract_full_text(msg)
                keep, skip_reason = should_keep(role, text, roles, args.include_blank)
                if not keep:
                    counters.messages_skipped += 1
                    if skip_reason == "blank_text":
                        counters.blank_skipped += 1
                    continue

                message_index += 1
                source_order += 1
                counters.messages_kept += 1
                progress.tick(messages=1)

                source_message_id = safe_str(msg.get("id") or node_id)
                parent_node_id = safe_str(node.get("parent"))
                content_hash = sha256_text(text)
                normalized = normalize_text(text)
                normalized_hash = sha256_text(normalized)
                logical_key = logical_key_for_message(
                    source_conversation_id=source_conversation_id,
                    source_message_id=source_message_id,
                    node_id=node_id,
                    parent_node_id=parent_node_id,
                    role=role,
                    create_time=safe_str(msg.get("create_time")),
                    content_hash=content_hash,
                )
                logical_hash = sha256_text(logical_key)
                message_uid = uid("msg", logical_hash)
                occurrence_hash = sha256_text(
                    compact_json(
                        {
                            "source_uid": source_uid,
                            "conversation_uid": conversation_uid,
                            "source_conversation_id": source_conversation_id,
                            "source_message_id": source_message_id,
                            "node_id": node_id,
                            "message_index": message_index,
                            "content_hash": content_hash,
                        }
                    )
                )
                occurrence_uid = f"occ_{occurrence_hash[:32]}"
                text_bytes = len(text.encode("utf-8", errors="replace"))
                source_locator = f"{source_path.name}#{source_conversation_id or conv_index}/{node_id}"
                is_visible = 1 if node_id in visible_nodes or not visible_nodes else 0
                vindex = visible_index.get(node_id)

                if content_hash not in known_content:
                    archive.execute(
                        """INSERT OR IGNORE INTO content_blobs
                           (content_hash,normalized_hash,text,char_count,byte_count,first_occurrence_uid,first_source_uid,created_at_utc)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (
                            content_hash,
                            normalized_hash,
                            text,
                            len(text),
                            text_bytes,
                            occurrence_uid,
                            source_uid,
                            now_utc(),
                        ),
                        estimated_bytes=text_bytes + 512,
                    )
                    manifest.add_content_location(
                        content_hash=content_hash,
                        normalized_hash=normalized_hash,
                        shard_id=archive.shard_id,
                        char_count=len(text),
                        byte_count=text_bytes,
                        occurrence_uid=occurrence_uid,
                        source_uid=source_uid,
                    )
                    known_content.add(content_hash)
                    content_shard_by_hash[content_hash] = archive.shard_id
                    counters.content_blobs += 1
                content_shard_id = content_shard_by_hash.get(content_hash, archive.shard_id)

                label = author_label(author, metadata, role)
                if message_uid not in known_messages:
                    archive.execute(
                        """INSERT OR IGNORE INTO archive_messages
                           (message_uid,conversation_uid,source_message_id,node_id,parent_node_id,role,author_label,
                            model_slug,default_model_slug,content_type,create_time,is_visible_path,visible_index,
                            content_hash,content_shard_id,normalized_hash,logical_hash,text_length,first_source_uid,
                            first_occurrence_uid,occurrence_count)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                        (
                            message_uid,
                            conversation_uid,
                            source_message_id,
                            node_id,
                            parent_node_id,
                            role,
                            label,
                            metadata.get("model_slug"),
                            metadata.get("default_model_slug"),
                            safe_str(content.get("content_type")),
                            safe_str(msg.get("create_time")),
                            is_visible,
                            vindex,
                            content_hash,
                            content_shard_id,
                            normalized_hash,
                            logical_hash,
                            text_length,
                            source_uid,
                            occurrence_uid,
                        ),
                        estimated_bytes=1024,
                    )
                    manifest.add_message_location(
                        message_uid=message_uid,
                        shard_id=archive.shard_id,
                        conversation_uid=conversation_uid,
                        content_hash=content_hash,
                        logical_hash=logical_hash,
                        occurrence_uid=occurrence_uid,
                        source_uid=source_uid,
                    )
                    known_messages.add(message_uid)
                    counters.logical_messages += 1
                else:
                    assert archive.con is not None
                    archive.con.execute(
                        "UPDATE archive_messages SET occurrence_count=occurrence_count+1 WHERE message_uid=?",
                        (message_uid,),
                    )

                archive.execute(
                    """INSERT OR REPLACE INTO archive_message_occurrences
                       (occurrence_uid,message_uid,conversation_uid,source_uid,source_conversation_id,source_message_id,
                        node_id,parent_node_id,conversation_index,message_index,source_order,is_visible_path,
                        visible_index,source_locator,occurrence_hash,content_hash)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        occurrence_uid,
                        message_uid,
                        conversation_uid,
                        source_uid,
                        source_conversation_id,
                        source_message_id,
                        node_id,
                        parent_node_id,
                        conv_index,
                        message_index,
                        source_order,
                        is_visible,
                        vindex,
                        source_locator,
                        occurrence_hash,
                        content_hash,
                    ),
                    estimated_bytes=768,
                )
                manifest.add_occurrence_location(
                    occurrence_uid=occurrence_uid,
                    shard_id=archive.shard_id,
                    message_uid=message_uid,
                    conversation_uid=conversation_uid,
                    source_uid=source_uid,
                    content_hash=content_hash,
                )
                counters.occurrences += 1

                speaker_actor_id, interlocutor_actor_id, identity_confidence = actor_ids(role, label)
                context_before = previous_message_by_conversation.get(conversation_uid)
                previous_message_by_conversation[conversation_uid] = message_uid
                staging_uid = uid("stage", occurrence_uid, message_uid)
                staging.execute(
                    """INSERT OR REPLACE INTO staging_memory_entries
                       (staging_uid,archive_message_uid,archive_occurrence_uid,conversation_uid,source_uid,content_hash,
                        normalized_hash,role,speaker_actor_id,interlocutor_actor_id,identity_confidence,privacy_scope,
                        memory_namespace,entry_type,create_time,time_confidence,emotional_weight,conversation_order,
                        context_before_message_uid,context_after_message_uid,review_status,canonical_candidate,created_at_utc)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        staging_uid,
                        message_uid,
                        occurrence_uid,
                        conversation_uid,
                        source_uid,
                        content_hash,
                        normalized_hash,
                        role,
                        speaker_actor_id,
                        interlocutor_actor_id,
                        identity_confidence,
                        "private_local",
                        DEFAULT_NAMESPACE,
                        "conversation_turn",
                        safe_str(msg.get("create_time")),
                        0.5 if msg.get("create_time") is not None else 0.1,
                        0.0,
                        source_order,
                        context_before,
                        None,
                        "unreviewed",
                        0,
                        now_utc(),
                    ),
                    estimated_bytes=1024,
                )
                staging.execute(
                    """INSERT OR REPLACE INTO staging_evidence
                       (staging_uid,evidence_kind,archive_message_uid,archive_occurrence_uid,source_uid,content_hash,evidence_weight)
                       VALUES(?,?,?,?,?,?,?)""",
                    (staging_uid, "source_occurrence", message_uid, occurrence_uid, source_uid, content_hash, 1.0),
                    estimated_bytes=512,
                )
                manifest.add_staging_location(
                    staging_uid=staging_uid,
                    shard_id=staging.shard_id,
                    message_uid=message_uid,
                    occurrence_uid=occurrence_uid,
                    content_hash=content_hash,
                )
                counters.staging_entries += 1

                if text.strip():
                    fts_doc_uid = uid("ftsdoc", staging_uid, message_uid, occurrence_uid)
                    fts.insert_doc(
                        fts_doc_uid=fts_doc_uid,
                        staging_uid=staging_uid,
                        message_uid=message_uid,
                        occurrence_uid=occurrence_uid,
                        conversation_uid=conversation_uid,
                        source_uid=source_uid,
                        content_hash=content_hash,
                        role=role,
                        title=title,
                        create_time=safe_str(msg.get("create_time")),
                        text=text,
                        manifest=manifest,
                    )
                    counters.fts_docs += 1

            assert archive.con is not None
            archive.con.execute(
                "UPDATE archive_conversations SET message_count=message_count+?, occurrence_count=occurrence_count+1 WHERE conversation_uid=?",
                (message_index, conversation_uid),
            )
            archive.con.execute(
                "UPDATE archive_conversation_occurrences SET kept_message_count=? WHERE conversation_occurrence_uid=?",
                (message_index, conversation_occurrence_uid),
            )
            if conv_index % 20 == 0:
                manifest.commit()

        progress.source_finished(source_path.name, source["size_bytes"])

    archive.close()
    staging.close()
    fts.close()
    manifest.commit()
    manifest.close()
    manifest_info = finalize_sqlite(manifest_path, hard_limit_bytes=hard_limit_bytes)

    generated = archive.generated + staging.generated + fts.generated
    generated.append({"shard_id": "manifest", "family": "manifest", "row_count": 0, **manifest_info})

    over_limit = [item for item in generated if item.get("over_limit")]
    comparison = compare_simple_db(Path(args.comparison_db).resolve() if args.comparison_db else None)
    status = "ok" if not over_limit else "over_limit"
    report = {
        "status": status,
        "script_version": SCRIPT_VERSION,
        "created_at_utc": now_utc(),
        "truth_boundary": "Raw HTML is the source. conversation_archive is source-backed. FTS is rebuildable. staging is not canonical memory.",
        "inputs": {
            "sources": source_info,
            "comparison_db": comparison,
            "roles": args.roles,
            "visible_only": not args.all_nodes,
            "include_blank": args.include_blank,
            "limit_conversations": args.limit_conversations,
        },
        "outputs": {
            "archive_dir": str(archive_dir),
            "fts_dir": str(fts_dir),
            "staging_dir": str(staging_dir),
            "manifest_db": str(manifest_path),
        },
        "limits": {
            "hard_limit_mib": args.hard_limit_mib,
            "archive_soft_mib": args.archive_soft_mib,
            "fts_soft_mib": args.fts_soft_mib,
            "staging_soft_mib": args.staging_soft_mib,
        },
        "counts": asdict(counters),
        "dedupe": {
            "content_blobs_saved_by_exact_text": max(0, counters.occurrences - counters.content_blobs),
            "logical_messages_saved_by_strong_keys": max(0, counters.occurrences - counters.logical_messages),
            "method": "content text is stored once by exact content_hash; occurrences preserve every source occurrence; logical messages use source_message_id/node/time/content strong keys.",
        },
        "generated_files": generated,
        "over_limit_files": over_limit,
    }
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build source-backed conversation_archive, separate FTS shards, and staging shards from raw ChatGPT HTML files."
    )
    parser.add_argument("--source", action="append", help="HTML source path. Defaults to memory/raw_chats/*.html.")
    parser.add_argument("--output-root", default=str(ROOT / "memory" / "sqlite"), help="Output root inside the project.")
    parser.add_argument("--comparison-db", default=None, help="Optional simple_all_chats sqlite3 used only for comparison.")
    parser.add_argument("--report", default=None, help="JSON report path. Defaults to workspace_runtime/conversation_archive_build_*.json.")
    parser.add_argument("--force", action="store_true", help="Replace output directories if they already contain files.")
    parser.add_argument("--roles", default="user,assistant", help="Comma-separated roles to archive/stage, or 'all'. Default: user,assistant.")
    parser.add_argument("--all-nodes", action="store_true", help="Include hidden/non-visible graph nodes too.")
    parser.add_argument("--include-blank", action="store_true", help="Keep blank messages.")
    parser.add_argument("--limit-conversations", type=int, default=None, help="Debug limit per source.")
    parser.add_argument("--hard-limit-mib", type=int, default=DEFAULT_HARD_LIMIT_MIB, help="Hard maximum size per sqlite3 file.")
    parser.add_argument("--archive-soft-mib", type=int, default=DEFAULT_ARCHIVE_SOFT_MIB, help="Soft archive shard target.")
    parser.add_argument("--fts-soft-mib", type=int, default=DEFAULT_FTS_SOFT_MIB, help="Soft FTS shard target.")
    parser.add_argument("--staging-soft-mib", type=int, default=DEFAULT_STAGING_SOFT_MIB, help="Soft staging shard target.")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.report:
        report_path = require_inside_root(Path(args.report))
    else:
        report_path = ROOT / "workspace_runtime" / f"conversation_archive_build_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = build_outputs(args)
    report_path.write_text(json_dumps(report), encoding="utf-8")
    print(json_dumps({"status": report["status"], "report": str(report_path), "counts": report["counts"]}))
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
