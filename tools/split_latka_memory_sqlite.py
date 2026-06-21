#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCRIPT_VERSION = "latka_memory_shard_split/v0.1"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DB = ROOT / "memory" / "sqlite" / "latka_memory_rebuilt_strict.sqlite3"
DEFAULT_OUTPUT_DIR = ROOT / "memory" / "sqlite" / "sharded_v1"
DEFAULT_HARD_LIMIT_MIB = 480
DEFAULT_TEXT_SOFT_MIB = 180
DEFAULT_RAW_SOFT_MIB = 160
DEFAULT_FTS_SOFT_MIB = 120


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def mib(value: int) -> float:
    return value / 1024 / 1024


def bytes_from_mib(value: int | float) -> int:
    return int(float(value) * 1024 * 1024)


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2)


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def open_sqlite(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=DELETE")
    con.execute("PRAGMA synchronous=OFF")
    con.execute("PRAGMA temp_store=MEMORY")
    con.execute("PRAGMA foreign_keys=OFF")
    return con


def open_source(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    return con


def table_columns(con: sqlite3.Connection, table: str) -> list[str]:
    return [row["name"] for row in con.execute(f"PRAGMA table_info({table})")]


def create_empty_copy_table(dst: sqlite3.Connection, src: sqlite3.Connection, table: str) -> None:
    src.execute(f"SELECT 1 FROM {table} LIMIT 0")
    dst.execute("ATTACH DATABASE ? AS srcdb", (str(Path(src.execute("PRAGMA database_list").fetchone()[2])),))
    try:
        dst.execute(f"CREATE TABLE {table} AS SELECT * FROM srcdb.{table} WHERE 0")
        dst.commit()
    finally:
        dst.execute("DETACH DATABASE srcdb")


def insert_rows(dst: sqlite3.Connection, table: str, rows: Iterable[sqlite3.Row], columns: list[str]) -> int:
    placeholders = ",".join("?" for _ in columns)
    col_sql = ",".join(columns)
    sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})"
    count = 0
    batch: list[tuple[Any, ...]] = []
    for row in rows:
        batch.append(tuple(row[col] for col in columns))
        if len(batch) >= 1000:
            dst.executemany(sql, batch)
            count += len(batch)
            batch.clear()
    if batch:
        dst.executemany(sql, batch)
        count += len(batch)
    return count


def copy_table_all(dst: sqlite3.Connection, src: sqlite3.Connection, table: str) -> int:
    create_empty_copy_table(dst, src, table)
    columns = table_columns(src, table)
    return insert_rows(dst, table, src.execute(f"SELECT * FROM {table}"), columns)


def create_basic_meta(con: sqlite3.Connection, shard_id: str, shard_type: str, source_db: Path) -> None:
    con.execute("CREATE TABLE shard_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    rows = {
        "script_version": SCRIPT_VERSION,
        "created_at_utc": now_utc(),
        "shard_id": shard_id,
        "shard_type": shard_type,
        "source_db": str(source_db),
        "truth_boundary": "This shard is a derived storage layer. FTS is search infrastructure, not canonical memory.",
    }
    con.executemany("INSERT INTO shard_meta(key,value) VALUES(?,?)", rows.items())


def add_source_refs(dst: sqlite3.Connection, src: sqlite3.Connection) -> None:
    copy_table_all(dst, src, "source_refs")
    dst.execute("CREATE INDEX IF NOT EXISTS idx_source_refs_id ON source_refs(id)")


def finalize_db(path: Path, *, vacuum: bool = True) -> dict[str, Any]:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=OFF")
    if vacuum:
        con.execute("VACUUM")
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    try:
        fk_count = len(con.execute("PRAGMA foreign_key_check").fetchall())
    except sqlite3.DatabaseError:
        fk_count = 0
    con.close()
    size = path.stat().st_size
    return {
        "path": str(path),
        "size_bytes": size,
        "size_mib": round(mib(size), 2),
        "sha256": sha256_file(path),
        "integrity_check": integrity,
        "foreign_key_error_count": fk_count,
    }


@dataclass
class Progress:
    enabled: bool
    total_units: int
    done_units: int = 0
    last_percent: int = -1
    started: float = field(default_factory=time.time)

    def step(self, count: int = 1, label: str = "") -> None:
        self.done_units += count
        if not self.enabled or self.total_units <= 0:
            return
        percent = min(100, int((self.done_units / self.total_units) * 100))
        if percent != self.last_percent and (percent % 2 == 0 or percent == 100):
            elapsed = time.time() - self.started
            msg = f"[{percent:3d}%] {label} ({self.done_units}/{self.total_units}, {elapsed:.1f}s)"
            print(msg, file=sys.stderr)
            self.last_percent = percent


class ManifestWriter:
    def __init__(self, path: Path, source_db: Path, hard_limit_bytes: int) -> None:
        self.path = path
        self.source_db = source_db
        self.hard_limit_bytes = hard_limit_bytes
        self.con = open_sqlite(path)
        self._create_schema()

    def _create_schema(self) -> None:
        self.con.executescript(
            """
            CREATE TABLE manifest_meta(
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            CREATE TABLE shard_files(
              shard_id TEXT PRIMARY KEY,
              shard_type TEXT NOT NULL,
              ordinal INTEGER NOT NULL,
              relative_path TEXT NOT NULL,
              table_name TEXT,
              row_count INTEGER NOT NULL,
              size_bytes INTEGER,
              size_mib REAL,
              sha256 TEXT,
              integrity_check TEXT,
              foreign_key_error_count INTEGER,
              hard_limit_bytes INTEGER NOT NULL,
              over_limit INTEGER NOT NULL DEFAULT 0,
              created_at_utc TEXT NOT NULL
            );
            CREATE TABLE row_locations(
              row_kind TEXT NOT NULL,
              row_id TEXT NOT NULL,
              shard_id TEXT NOT NULL,
              source_ref_id TEXT,
              original_index INTEGER,
              content_hash TEXT,
              PRIMARY KEY(row_kind, row_id)
            );
            CREATE INDEX idx_row_locations_shard ON row_locations(shard_id);
            CREATE INDEX idx_row_locations_source ON row_locations(source_ref_id);
            """
        )

    def attach_source_refs(self, src: sqlite3.Connection) -> None:
        create_ctas_table_from_source(self.con, self.source_db, "source_refs")
        cols = table_columns(src, "source_refs")
        insert_rows(self.con, "source_refs", src.execute("SELECT * FROM source_refs"), cols)
        self.con.execute("CREATE INDEX idx_manifest_source_refs_id ON source_refs(id)")

    def add_meta(self) -> None:
        rows = {
            "script_version": SCRIPT_VERSION,
            "created_at_utc": now_utc(),
            "source_db": str(self.source_db),
            "hard_limit_bytes": str(self.hard_limit_bytes),
            "truth_boundary": "Manifest maps row ids to shard files. Canonical memory is in core; FTS is search infrastructure.",
        }
        self.con.executemany("INSERT OR REPLACE INTO manifest_meta(key,value) VALUES(?,?)", rows.items())

    def add_shard(self, info: dict[str, Any], shard_id: str, shard_type: str, ordinal: int, relative_path: str, table_name: str | None, row_count: int) -> None:
        over_limit = int(info["size_bytes"] > self.hard_limit_bytes)
        self.con.execute(
            """INSERT OR REPLACE INTO shard_files
               (shard_id,shard_type,ordinal,relative_path,table_name,row_count,size_bytes,size_mib,sha256,
                integrity_check,foreign_key_error_count,hard_limit_bytes,over_limit,created_at_utc)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                shard_id,
                shard_type,
                ordinal,
                relative_path,
                table_name,
                row_count,
                info["size_bytes"],
                info["size_mib"],
                info["sha256"],
                info["integrity_check"],
                info["foreign_key_error_count"],
                self.hard_limit_bytes,
                over_limit,
                now_utc(),
            ),
        )

    def add_location(self, row_kind: str, row_id: str, shard_id: str, source_ref_id: str | None, original_index: int | None, content_hash: str | None) -> None:
        self.con.execute(
            """INSERT OR REPLACE INTO row_locations
               (row_kind,row_id,shard_id,source_ref_id,original_index,content_hash)
               VALUES(?,?,?,?,?,?)""",
            (row_kind, row_id, shard_id, source_ref_id, original_index, content_hash),
        )

    def commit(self) -> None:
        self.con.commit()

    def close(self) -> None:
        self.con.commit()
        self.con.close()


def build_core(src: sqlite3.Connection, source_db: Path, out_dir: Path, hard_limit_bytes: int) -> tuple[dict[str, Any], int]:
    path = out_dir / "latka_memory_core.sqlite3"
    con = open_sqlite(path)
    create_basic_meta(con, "core", "core", source_db)
    for table in (
        "meta",
        "source_refs",
        "actors",
        "conversation_sessions",
        "latka_life_events",
        "memory_evidence",
        "memory_edges",
        "identity_snapshots",
        "wake_state",
    ):
        copy_table_all(con, src, table)
    con.execute("ATTACH DATABASE ? AS srcdb", (str(source_db),))
    try:
        con.execute(
            """CREATE TABLE canonical_event_participants AS
               SELECT e.id AS event_id,
                      p.entry_id AS promoted_from_staging_id,
                      p.actor_id,
                      p.role,
                      p.identity_confidence,
                      p.source_ref_id,
                      p.created_at
                 FROM srcdb.memory_entry_participants p
                 JOIN srcdb.latka_life_events e ON e.promoted_from_staging_id=p.entry_id"""
        )
        con.commit()
    finally:
        con.execute("DETACH DATABASE srcdb")
    con.executescript(
        """
        CREATE INDEX idx_core_events_hash ON latka_life_events(content_hash);
        CREATE INDEX idx_core_events_namespace ON latka_life_events(memory_namespace);
        CREATE INDEX idx_core_events_datetime ON latka_life_events(datetime_iso);
        CREATE INDEX idx_core_evidence_event ON memory_evidence(event_id);
        CREATE INDEX idx_core_participants_event ON canonical_event_participants(event_id);
        CREATE TABLE shard_files(
          shard_id TEXT PRIMARY KEY,
          shard_type TEXT NOT NULL,
          ordinal INTEGER NOT NULL,
          relative_path TEXT NOT NULL,
          table_name TEXT,
          row_count INTEGER NOT NULL,
          size_bytes INTEGER,
          size_mib REAL,
          sha256 TEXT,
          integrity_check TEXT,
          foreign_key_error_count INTEGER,
          hard_limit_bytes INTEGER NOT NULL,
          over_limit INTEGER NOT NULL DEFAULT 0,
          created_at_utc TEXT NOT NULL
        );
        """
    )
    row_count = src.execute("SELECT COUNT(*) FROM latka_life_events").fetchone()[0]
    con.commit()
    con.close()
    info = finalize_db(path)
    info["over_limit"] = info["size_bytes"] > hard_limit_bytes
    return info, row_count


def build_review(src: sqlite3.Connection, source_db: Path, out_dir: Path, hard_limit_bytes: int) -> tuple[dict[str, Any], int]:
    path = out_dir / "latka_memory_review.sqlite3"
    con = open_sqlite(path)
    create_basic_meta(con, "review", "review", source_db)
    add_source_refs(con, src)
    copy_table_all(con, src, "review_queue")
    con.executescript(
        """
        CREATE INDEX idx_review_issue ON review_queue(issue_code);
        CREATE INDEX idx_review_status ON review_queue(status);
        CREATE INDEX idx_review_staging ON review_queue(staging_id);
        """
    )
    row_count = src.execute("SELECT COUNT(*) FROM review_queue").fetchone()[0]
    con.commit()
    con.close()
    info = finalize_db(path)
    info["over_limit"] = info["size_bytes"] > hard_limit_bytes
    return info, row_count


def source_db_path(src: sqlite3.Connection) -> str:
    return src.execute("PRAGMA database_list").fetchone()[2]


def create_ctas_table_from_source(dst: sqlite3.Connection, source_path: Path, table: str) -> None:
    dst.execute("ATTACH DATABASE ? AS srcdb", (str(source_path),))
    try:
        dst.execute(f"CREATE TABLE {table} AS SELECT * FROM srcdb.{table} WHERE 0")
        dst.commit()
    finally:
        dst.execute("DETACH DATABASE srcdb")


def iter_table_rows(src: sqlite3.Connection, table: str, estimate_sql: str) -> Iterable[sqlite3.Row]:
    sql = f"""
        SELECT *, ({estimate_sql}) AS __estimated_bytes
          FROM {table}
         ORDER BY source_ref_id, COALESCE(original_index, 0), id
    """
    return src.execute(sql)


def build_table_shards(
    *,
    src: sqlite3.Connection,
    source_db: Path,
    out_dir: Path,
    table: str,
    shard_type: str,
    file_prefix: str,
    soft_limit_bytes: int,
    hard_limit_bytes: int,
    manifest: ManifestWriter,
    progress: Progress,
    row_kind: str,
    limit_rows: int | None = None,
) -> list[dict[str, Any]]:
    columns = table_columns(src, table)
    insert_sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
    estimate_sql = {
        "staging_memory_entries": """
            COALESCE(LENGTH(content_text),0) + COALESCE(LENGTH(content_json),0) +
            COALESCE(LENGTH(raw_payload_json),0) + COALESCE(LENGTH(participants_json),0) +
            COALESCE(LENGTH(tags_json),0) + COALESCE(LENGTH(emotions_json),0) + 512
        """,
        "raw_source_rows": """
            COALESCE(LENGTH(content_text),0) + COALESCE(LENGTH(raw_payload_json),0) +
            COALESCE(LENGTH(raw_payload_zlib),0) + 512
        """,
    }[table]

    shards: list[dict[str, Any]] = []
    ordinal = 0
    con: sqlite3.Connection | None = None
    path: Path | None = None
    shard_id = ""
    estimated = 0
    row_count = 0
    batch: list[tuple[Any, ...]] = []

    def start_new() -> None:
        nonlocal ordinal, con, path, shard_id, estimated, row_count, batch
        ordinal += 1
        shard_id = f"{shard_type}_{ordinal:04d}"
        path = out_dir / f"{file_prefix}_{ordinal:04d}.sqlite3"
        con = open_sqlite(path)
        create_basic_meta(con, shard_id, shard_type, source_db)
        add_source_refs(con, src)
        create_ctas_table_from_source(con, source_db, table)
        estimated = 0
        row_count = 0
        batch = []

    def finish_current() -> None:
        nonlocal con, path, shard_id, row_count, batch
        if con is None or path is None:
            return
        if batch:
            con.executemany(insert_sql, batch)
            batch = []
        if table == "staging_memory_entries":
            con.executescript(
                """
                CREATE INDEX idx_staging_id ON staging_memory_entries(id);
                CREATE INDEX idx_staging_source ON staging_memory_entries(source_ref_id);
                CREATE INDEX idx_staging_hash ON staging_memory_entries(content_hash);
                CREATE INDEX idx_staging_datetime ON staging_memory_entries(datetime_iso);
                """
            )
        elif table == "raw_source_rows":
            con.executescript(
                """
                CREATE INDEX idx_raw_id ON raw_source_rows(id);
                CREATE INDEX idx_raw_source ON raw_source_rows(source_ref_id);
                CREATE INDEX idx_raw_hash ON raw_source_rows(content_hash);
                """
            )
        con.commit()
        con.close()
        info = finalize_db(path)
        info["over_limit"] = info["size_bytes"] > hard_limit_bytes
        rel = path.relative_to(out_dir).as_posix()
        manifest.add_shard(info, shard_id, shard_type, ordinal, rel, table, row_count)
        shards.append({"shard_id": shard_id, "row_count": row_count, **info})
        con = None

    start_new()
    copied = 0
    for row in iter_table_rows(src, table, estimate_sql):
        if limit_rows is not None and copied >= limit_rows:
            break
        row_estimate = int(row["__estimated_bytes"] or 512)
        if row_count > 0 and estimated + row_estimate > soft_limit_bytes:
            finish_current()
            start_new()
        batch.append(tuple(row[col] for col in columns))
        if len(batch) >= 1000 and con is not None:
            con.executemany(insert_sql, batch)
            batch.clear()
        estimated += max(row_estimate, 512)
        row_count += 1
        copied += 1
        manifest.add_location(row_kind, row["id"], shard_id, row["source_ref_id"], row["original_index"], row["content_hash"])
        if copied % 1000 == 0:
            manifest.commit()
            progress.step(1000, table)
    remainder = copied % 1000
    if remainder:
        progress.step(remainder, table)
    finish_current()
    return shards


def build_fts_shards(
    *,
    src: sqlite3.Connection,
    source_db: Path,
    out_dir: Path,
    soft_limit_bytes: int,
    hard_limit_bytes: int,
    manifest: ManifestWriter,
    progress: Progress,
    limit_rows: int | None = None,
) -> list[dict[str, Any]]:
    shards: list[dict[str, Any]] = []
    ordinal = 0
    con: sqlite3.Connection | None = None
    path: Path | None = None
    shard_id = ""
    estimated = 0
    row_count = 0
    doc_rowid = 0
    doc_batch: list[tuple[Any, ...]] = []
    fts_batch: list[tuple[Any, ...]] = []

    def start_new() -> None:
        nonlocal ordinal, con, path, shard_id, estimated, row_count, doc_rowid, doc_batch, fts_batch
        ordinal += 1
        shard_id = f"fts_{ordinal:04d}"
        path = out_dir / f"latka_memory_fts_{ordinal:04d}.sqlite3"
        con = open_sqlite(path)
        create_basic_meta(con, shard_id, "fts", source_db)
        add_source_refs(con, src)
        con.executescript(
            """
            CREATE TABLE fts_docs(
              rowid INTEGER PRIMARY KEY,
              staging_id TEXT NOT NULL,
              source_ref_id TEXT NOT NULL,
              raw_row_id TEXT,
              original_index INTEGER,
              datetime_iso TEXT,
              type_norm TEXT,
              memory_namespace TEXT,
              content_hash TEXT NOT NULL,
              title TEXT
            );
            CREATE VIRTUAL TABLE fts_index USING fts5(
              content_text,
              title,
              tokenize='unicode61 remove_diacritics 1',
              content=''
            );
            """
        )
        estimated = 0
        row_count = 0
        doc_rowid = 0
        doc_batch = []
        fts_batch = []

    def flush() -> None:
        nonlocal doc_batch, fts_batch
        if con is None:
            return
        if doc_batch:
            con.executemany(
                """INSERT INTO fts_docs
                   (rowid,staging_id,source_ref_id,raw_row_id,original_index,datetime_iso,type_norm,memory_namespace,content_hash,title)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                doc_batch,
            )
            doc_batch = []
        if fts_batch:
            con.executemany("INSERT INTO fts_index(rowid,content_text,title) VALUES(?,?,?)", fts_batch)
            fts_batch = []

    def finish_current() -> None:
        nonlocal con, path, shard_id, row_count
        if con is None or path is None:
            return
        flush()
        con.executescript(
            """
            CREATE INDEX idx_fts_docs_staging ON fts_docs(staging_id);
            CREATE INDEX idx_fts_docs_source ON fts_docs(source_ref_id);
            CREATE INDEX idx_fts_docs_hash ON fts_docs(content_hash);
            """
        )
        con.commit()
        con.close()
        info = finalize_db(path)
        info["over_limit"] = info["size_bytes"] > hard_limit_bytes
        rel = path.relative_to(out_dir).as_posix()
        manifest.add_shard(info, shard_id, "fts", ordinal, rel, "fts_index", row_count)
        shards.append({"shard_id": shard_id, "row_count": row_count, **info})
        con = None

    start_new()
    copied = 0
    rows = src.execute(
        """
        SELECT id,source_ref_id,raw_row_id,original_index,datetime_iso,type_norm,memory_namespace,
               content_hash,title,content_text,
               COALESCE(LENGTH(content_text),0) + COALESCE(LENGTH(title),0) + 256 AS __estimated_bytes
          FROM staging_memory_entries
         WHERE COALESCE(TRIM(content_text),'') <> ''
         ORDER BY source_ref_id, COALESCE(original_index,0), id
        """
    )
    for row in rows:
        if limit_rows is not None and copied >= limit_rows:
            break
        row_estimate = int(row["__estimated_bytes"] or 256)
        if row_count > 0 and estimated + row_estimate > soft_limit_bytes:
            finish_current()
            start_new()
        doc_rowid += 1
        doc_batch.append(
            (
                doc_rowid,
                row["id"],
                row["source_ref_id"],
                row["raw_row_id"],
                row["original_index"],
                row["datetime_iso"],
                row["type_norm"],
                row["memory_namespace"],
                row["content_hash"],
                row["title"],
            )
        )
        fts_batch.append((doc_rowid, row["content_text"], row["title"] or ""))
        if len(doc_batch) >= 1000:
            flush()
        estimated += max(row_estimate, 256)
        row_count += 1
        copied += 1
        if copied % 1000 == 0:
            progress.step(1000, "fts")
    remainder = copied % 1000
    if remainder:
        progress.step(remainder, "fts")
    finish_current()
    return shards


def update_core_with_shards(core_path: Path, manifest_path: Path) -> None:
    con = open_sqlite(core_path)
    con.execute("DELETE FROM shard_files")
    con.execute("ATTACH DATABASE ? AS manifest_db", (str(manifest_path),))
    try:
        con.execute("INSERT INTO shard_files SELECT * FROM manifest_db.shard_files")
        con.commit()
    finally:
        con.execute("DETACH DATABASE manifest_db")
    con.commit()
    con.close()
    finalize_db(core_path)


def clean_output_dir(path: Path, root: Path, force: bool) -> None:
    path = path.resolve()
    root = root.resolve()
    if not str(path).lower().startswith(str(root).lower()):
        raise SystemExit(f"Refusing to write outside project root: {path}")
    if path.exists() and any(path.iterdir()):
        if not force:
            raise SystemExit(f"Output directory exists and is not empty: {path}. Use --force or choose another directory.")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Split strict Latka memory SQLite into <=480 MiB operational shards with FTS in separate databases.")
    parser.add_argument("--input-db", default=str(DEFAULT_INPUT_DB), help="Source strict SQLite database.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for sharded SQLite files.")
    parser.add_argument("--report", default=None, help="Optional JSON report path.")
    parser.add_argument("--force", action="store_true", help="Replace output directory if it already contains files.")
    parser.add_argument("--hard-limit-mib", type=int, default=DEFAULT_HARD_LIMIT_MIB, help="Hard maximum size per sqlite3 file.")
    parser.add_argument("--text-soft-mib", type=int, default=DEFAULT_TEXT_SOFT_MIB, help="Soft target for text shards.")
    parser.add_argument("--raw-soft-mib", type=int, default=DEFAULT_RAW_SOFT_MIB, help="Soft target for raw shards.")
    parser.add_argument("--fts-soft-mib", type=int, default=DEFAULT_FTS_SOFT_MIB, help="Soft target for FTS shards.")
    parser.add_argument("--limit-rows", type=int, default=None, help="Debug limit applied to each large shard family.")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    input_db = Path(args.input_db).resolve()
    out_dir = Path(args.output_dir).resolve()
    report_path = Path(args.report).resolve() if args.report else out_dir / "latka_memory_shard_split_report.json"
    if not input_db.exists():
        raise SystemExit(f"Input DB not found: {input_db}")

    hard_limit_bytes = bytes_from_mib(args.hard_limit_mib)
    clean_output_dir(out_dir, ROOT, args.force)

    src = open_source(input_db)
    integrity = src.execute("PRAGMA integrity_check").fetchone()[0]
    fk_count = len(src.execute("PRAGMA foreign_key_check").fetchall())
    if integrity != "ok" or fk_count:
        raise SystemExit(f"Source DB is not clean: integrity={integrity}, fk_count={fk_count}")

    total_units = (
        src.execute("SELECT COUNT(*) FROM staging_memory_entries").fetchone()[0]
        + src.execute("SELECT COUNT(*) FROM raw_source_rows").fetchone()[0]
        + src.execute("SELECT COUNT(*) FROM staging_memory_entries WHERE COALESCE(TRIM(content_text),'')<>''").fetchone()[0]
    )
    if args.limit_rows is not None:
        total_units = min(total_units, args.limit_rows * 3)
    progress = Progress(not args.no_progress, total_units)

    manifest_path = out_dir / "latka_memory_manifest.sqlite3"
    manifest = ManifestWriter(manifest_path, input_db, hard_limit_bytes)
    manifest.add_meta()
    manifest.attach_source_refs(src)

    generated: list[dict[str, Any]] = []

    core_info, core_rows = build_core(src, input_db, out_dir, hard_limit_bytes)
    manifest.add_shard(core_info, "core", "core", 0, "latka_memory_core.sqlite3", "latka_life_events", core_rows)
    generated.append({"shard_id": "core", "shard_type": "core", "row_count": core_rows, **core_info})

    review_info, review_rows = build_review(src, input_db, out_dir, hard_limit_bytes)
    manifest.add_shard(review_info, "review", "review", 0, "latka_memory_review.sqlite3", "review_queue", review_rows)
    generated.append({"shard_id": "review", "shard_type": "review", "row_count": review_rows, **review_info})

    text_shards = build_table_shards(
        src=src,
        source_db=input_db,
        out_dir=out_dir,
        table="staging_memory_entries",
        shard_type="text",
        file_prefix="latka_memory_text",
        soft_limit_bytes=bytes_from_mib(args.text_soft_mib),
        hard_limit_bytes=hard_limit_bytes,
        manifest=manifest,
        progress=progress,
        row_kind="staging",
        limit_rows=args.limit_rows,
    )
    generated.extend({"shard_type": "text", **item} for item in text_shards)

    raw_shards = build_table_shards(
        src=src,
        source_db=input_db,
        out_dir=out_dir,
        table="raw_source_rows",
        shard_type="raw",
        file_prefix="latka_memory_raw",
        soft_limit_bytes=bytes_from_mib(args.raw_soft_mib),
        hard_limit_bytes=hard_limit_bytes,
        manifest=manifest,
        progress=progress,
        row_kind="raw",
        limit_rows=args.limit_rows,
    )
    generated.extend({"shard_type": "raw", **item} for item in raw_shards)

    fts_shards = build_fts_shards(
        src=src,
        source_db=input_db,
        out_dir=out_dir,
        soft_limit_bytes=bytes_from_mib(args.fts_soft_mib),
        hard_limit_bytes=hard_limit_bytes,
        manifest=manifest,
        progress=progress,
        limit_rows=args.limit_rows,
    )
    generated.extend({"shard_type": "fts", **item} for item in fts_shards)

    manifest.commit()
    manifest.close()

    update_core_with_shards(out_dir / "latka_memory_core.sqlite3", manifest_path)
    manifest_info = finalize_db(manifest_path)
    manifest_info["over_limit"] = manifest_info["size_bytes"] > hard_limit_bytes
    generated.append({"shard_id": "manifest", "shard_type": "manifest", "row_count": 0, **manifest_info})

    over_limit = [item for item in generated if item["size_bytes"] > hard_limit_bytes]
    status = "ok" if not over_limit else "over_limit"
    report = {
        "status": status,
        "script_version": SCRIPT_VERSION,
        "source_db": str(input_db),
        "source_integrity_check": integrity,
        "source_foreign_key_error_count": fk_count,
        "output_dir": str(out_dir),
        "hard_limit_bytes": hard_limit_bytes,
        "hard_limit_mib": args.hard_limit_mib,
        "soft_limits_mib": {
            "text": args.text_soft_mib,
            "raw": args.raw_soft_mib,
            "fts": args.fts_soft_mib,
        },
        "counts": {
            "core_events": core_rows,
            "review_rows": review_rows,
            "text_shards": len(text_shards),
            "raw_shards": len(raw_shards),
            "fts_shards": len(fts_shards),
            "sqlite_file_count": len(generated),
        },
        "max_size_mib": max(item["size_mib"] for item in generated) if generated else 0,
        "over_limit": over_limit,
        "generated": generated,
        "created_at_utc": now_utc(),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json_dumps(report), encoding="utf-8")
    print(json.dumps({"status": status, "output_dir": str(out_dir), "report": str(report_path), "counts": report["counts"], "max_size_mib": report["max_size_mib"]}, ensure_ascii=False, indent=2))
    return 0 if status == "ok" else 3


if __name__ == "__main__":
    raise SystemExit(main())
