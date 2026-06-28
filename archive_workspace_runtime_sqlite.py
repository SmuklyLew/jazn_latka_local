#!/usr/bin/env python3
"""
Losslessly archive workspace_runtime/*.sqlite3 inside memory/sqlite/chat_context.sqlite3.

The target's existing conversation tables are never changed. Runtime rows are stored in
separate runtime_archive_* tables. Exact records are deduplicated by a strong SHA256
calculated from the source table name, ordered column names, SQLite value types, and
complete values. Source snapshots and every row occurrence remain traceable.

Default mode is read-only dry-run. Use --apply to write, which always creates a
consistent SQLite backup before opening the target for writes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence
from urllib.parse import quote


SCRIPT_VERSION = "archive_workspace_runtime_sqlite/v1"
DEFAULT_SOURCE_DIR = "workspace_runtime"
DEFAULT_TARGET = "memory/sqlite/chat_context.sqlite3"
ARCHIVE_SCHEMA_VERSION = "1"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8", errors="surrogatepass"))


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def safe_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sqlite_readonly_uri(path: Path) -> str:
    normalized = str(path.resolve()).replace("\\", "/")
    return "file:" + quote(normalized, safe="/:") + "?mode=ro"


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def encode_sqlite_value(value: Any) -> dict[str, Any]:
    """Encode a SQLite value without losing its SQLite storage class or bytes."""
    if value is None:
        return {"type": "null"}
    if isinstance(value, bytes):
        return {"type": "blob", "base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, bool):
        return {"type": "integer", "value": int(value)}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, float):
        return {"type": "real", "hex": value.hex()}
    if isinstance(value, str):
        return {"type": "text", "value": value}
    raise TypeError(f"Unsupported SQLite value type: {type(value).__name__}")


@dataclass
class TableScan:
    name: str
    columns: list[str]
    primary_key_columns: list[str]
    row_count: int
    unique_record_count: int
    multiset_sha256: str


@dataclass
class SourceScan:
    path: Path
    source_file: str
    source_file_sha256: str = ""
    source_wal_sha256: str = ""
    source_size_bytes: int = 0
    source_mtime_ns: int = 0
    snapshot_sha256: str = ""
    integrity_check: str = ""
    pragmas_json: str = "{}"
    schema_objects: list[dict[str, Any]] = field(default_factory=list)
    tables: list[TableScan] = field(default_factory=list)
    row_occurrence_count: int = 0
    unique_record_hashes: set[str] = field(default_factory=set, repr=False)
    errors: list[str] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return not self.errors and self.integrity_check == "ok" and bool(self.snapshot_sha256)

    def report(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "source_size_bytes": self.source_size_bytes,
            "source_file_sha256": self.source_file_sha256,
            "source_wal_sha256": self.source_wal_sha256 or None,
            "snapshot_sha256": self.snapshot_sha256 or None,
            "integrity_check": self.integrity_check or None,
            "schema_object_count": len(self.schema_objects),
            "table_count": len(self.tables),
            "row_occurrence_count": self.row_occurrence_count,
            "unique_record_count": len(self.unique_record_hashes),
            "tables": [
                {
                    "name": table.name,
                    "columns": table.columns,
                    "primary_key_columns": table.primary_key_columns,
                    "row_count": table.row_count,
                    "unique_record_count": table.unique_record_count,
                    "multiset_sha256": table.multiset_sha256,
                }
                for table in self.tables
            ],
            "errors": self.errors,
        }


def open_readonly(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(sqlite_readonly_uri(path), uri=True, timeout=10.0)
    con.text_factory = lambda raw: raw.decode("utf-8", errors="surrogateescape")
    con.execute("PRAGMA query_only = ON")
    con.execute("BEGIN")
    return con


def read_pragmas(con: sqlite3.Connection) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in ("application_id", "auto_vacuum", "encoding", "page_size", "user_version"):
        result[name] = con.execute(f"PRAGMA {name}").fetchone()[0]
    return result


def read_schema_objects(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute(
        "SELECT type, name, tbl_name, rootpage, sql "
        "FROM sqlite_schema ORDER BY type, name, tbl_name, rootpage"
    )
    return [
        {
            "type": row[0],
            "name": row[1],
            "table_name": row[2],
            "rootpage": row[3],
            "sql": row[4],
        }
        for row in rows
    ]


def table_names(con: sqlite3.Connection) -> list[str]:
    return [
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name"
        )
    ]


def table_primary_key_columns(con: sqlite3.Connection, table: str) -> list[str]:
    rows = con.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
    return [
        str(row[1])
        for row in sorted((row for row in rows if int(row[5]) > 0), key=lambda row: int(row[5]))
    ]


def iter_table_records(
    con: sqlite3.Connection, table: str
) -> Iterator[tuple[int, str, str, str, list[str], list[str]]]:
    cursor = con.execute(f"SELECT * FROM {quote_ident(table)}")
    columns = [str(item[0]) for item in cursor.description or ()]
    primary_key_columns = table_primary_key_columns(con, table)
    column_indexes = {name: index for index, name in enumerate(columns)}

    for ordinal, row in enumerate(cursor, start=1):
        encoded_values = [encode_sqlite_value(value) for value in row]
        payload = {
            "table": table,
            "columns": columns,
            "values": encoded_values,
        }
        record_json = canonical_json(payload)
        record_sha256 = sha256_text(record_json)

        if primary_key_columns and all(name in column_indexes for name in primary_key_columns):
            locator = {
                "kind": "primary_key",
                "columns": primary_key_columns,
                "values": [
                    encoded_values[column_indexes[name]]
                    for name in primary_key_columns
                ],
            }
        else:
            locator = {"kind": "scan_ordinal", "ordinal": ordinal}

        yield (
            ordinal,
            record_sha256,
            record_json,
            canonical_json(locator),
            columns,
            primary_key_columns,
        )


def scan_open_connection(path: Path, root: Path, con: sqlite3.Connection) -> SourceScan:
    scan = SourceScan(
        path=path,
        source_file=safe_rel(path, root),
        source_size_bytes=path.stat().st_size,
        source_mtime_ns=path.stat().st_mtime_ns,
    )
    scan.source_file_sha256 = file_sha256(path)
    wal_path = path.with_name(path.name + "-wal")
    if wal_path.is_file():
        scan.source_wal_sha256 = file_sha256(wal_path)

    try:
        quick_rows = [str(row[0]) for row in con.execute("PRAGMA quick_check")]
        scan.integrity_check = "; ".join(quick_rows)
        if quick_rows != ["ok"]:
            scan.errors.append("quick_check: " + scan.integrity_check)
            return scan

        pragmas = read_pragmas(con)
        scan.pragmas_json = canonical_json(pragmas)
        scan.schema_objects = read_schema_objects(con)
        schema_hashes = [
            sha256_text(canonical_json(schema_object))
            for schema_object in scan.schema_objects
        ]

        table_digests: list[dict[str, Any]] = []
        for table in table_names(con):
            record_counts: Counter[str] = Counter()
            columns: list[str] = []
            primary_key_columns: list[str] = []
            try:
                for (
                    _ordinal,
                    record_sha256,
                    _record_json,
                    _locator_json,
                    columns,
                    primary_key_columns,
                ) in iter_table_records(con, table):
                    record_counts[record_sha256] += 1
                    scan.unique_record_hashes.add(record_sha256)
                    scan.row_occurrence_count += 1
            except Exception as exc:
                scan.errors.append(f"table {table}: {type(exc).__name__}: {exc}")
                continue

            multiset = [[digest, count] for digest, count in sorted(record_counts.items())]
            multiset_sha256 = sha256_text(canonical_json(multiset))
            scan.tables.append(
                TableScan(
                    name=table,
                    columns=columns,
                    primary_key_columns=primary_key_columns,
                    row_count=sum(record_counts.values()),
                    unique_record_count=len(record_counts),
                    multiset_sha256=multiset_sha256,
                )
            )
            table_digests.append(
                {
                    "table": table,
                    "columns": columns,
                    "primary_key_columns": primary_key_columns,
                    "row_count": sum(record_counts.values()),
                    "multiset_sha256": multiset_sha256,
                }
            )

        if scan.errors:
            return scan

        snapshot_payload = {
            "archive_snapshot_format": ARCHIVE_SCHEMA_VERSION,
            "pragmas": pragmas,
            "schema_object_sha256": sorted(schema_hashes),
            "tables": table_digests,
        }
        scan.snapshot_sha256 = sha256_text(canonical_json(snapshot_payload))
    except Exception as exc:
        scan.errors.append(f"{type(exc).__name__}: {exc}")
    return scan


def inspect_source(path: Path, root: Path) -> SourceScan:
    scan = SourceScan(path=path, source_file=safe_rel(path, root))
    try:
        with closing(open_readonly(path)) as con:
            return scan_open_connection(path, root, con)
    except Exception as exc:
        try:
            scan.source_size_bytes = path.stat().st_size
            scan.source_mtime_ns = path.stat().st_mtime_ns
            scan.source_file_sha256 = file_sha256(path)
            wal_path = path.with_name(path.name + "-wal")
            if wal_path.is_file():
                scan.source_wal_sha256 = file_sha256(wal_path)
        except Exception as metadata_exc:
            scan.errors.append(
                f"source metadata: {type(metadata_exc).__name__}: {metadata_exc}"
            )
        scan.errors.append(f"{type(exc).__name__}: {exc}")
        return scan


def discover_sources(source_dir: Path, patterns: Sequence[str]) -> list[Path]:
    found: set[Path] = set()
    for pattern in patterns:
        found.update(path.resolve() for path in source_dir.glob(pattern) if path.is_file())
    return sorted(found, key=lambda path: path.name.lower())


def archive_status(target: Path) -> dict[str, Any]:
    result = {
        "target_exists": target.is_file(),
        "archive_schema_exists": False,
        "snapshots": 0,
        "source_files": 0,
        "unique_records": 0,
        "record_occurrences": 0,
    }
    if not target.is_file():
        return result
    try:
        with closing(open_readonly(target)) as con:
            names = {
                row[0]
                for row in con.execute(
                    "SELECT name FROM sqlite_schema WHERE type='table'"
                )
            }
            required = {
                "runtime_archive_snapshots",
                "runtime_archive_snapshot_files",
                "runtime_archive_records",
                "runtime_archive_record_occurrences",
            }
            result["archive_schema_exists"] = required.issubset(names)
            if result["archive_schema_exists"]:
                result["snapshots"] = con.execute(
                    "SELECT COUNT(*) FROM runtime_archive_snapshots"
                ).fetchone()[0]
                result["source_files"] = con.execute(
                    "SELECT COUNT(*) FROM runtime_archive_snapshot_files"
                ).fetchone()[0]
                result["unique_records"] = con.execute(
                    "SELECT COUNT(*) FROM runtime_archive_records"
                ).fetchone()[0]
                result["record_occurrences"] = con.execute(
                    "SELECT COUNT(*) FROM runtime_archive_record_occurrences"
                ).fetchone()[0]
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def create_target_backup(target: Path, backup: Path) -> None:
    if backup.exists():
        raise FileExistsError(f"Backup already exists: {backup}")
    backup.parent.mkdir(parents=True, exist_ok=True)
    try:
        with closing(sqlite3.connect(sqlite_readonly_uri(target), uri=True, timeout=30.0)) as source:
            with closing(sqlite3.connect(str(backup))) as destination:
                source.backup(destination)
                check = destination.execute("PRAGMA quick_check").fetchone()[0]
                if check != "ok":
                    raise sqlite3.DatabaseError(f"Backup quick_check failed: {check}")
    except Exception:
        if backup.exists():
            backup.unlink()
        raise


def create_archive_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        BEGIN IMMEDIATE;

        CREATE TABLE IF NOT EXISTS runtime_archive_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS runtime_archive_snapshots (
            snapshot_sha256 TEXT PRIMARY KEY,
            integrity_check TEXT NOT NULL,
            pragmas_json TEXT NOT NULL,
            schema_object_count INTEGER NOT NULL,
            table_count INTEGER NOT NULL,
            row_occurrence_count INTEGER NOT NULL,
            unique_record_count INTEGER NOT NULL,
            imported_at_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS runtime_archive_snapshot_files (
            snapshot_sha256 TEXT NOT NULL,
            source_file TEXT NOT NULL,
            source_file_sha256 TEXT NOT NULL,
            source_wal_sha256 TEXT NOT NULL DEFAULT '',
            source_size_bytes INTEGER NOT NULL,
            source_mtime_ns INTEGER NOT NULL,
            first_seen_at_utc TEXT NOT NULL,
            PRIMARY KEY (
                snapshot_sha256, source_file, source_file_sha256, source_wal_sha256
            ),
            FOREIGN KEY (snapshot_sha256)
                REFERENCES runtime_archive_snapshots(snapshot_sha256)
        ) WITHOUT ROWID;

        CREATE TABLE IF NOT EXISTS runtime_archive_schema_objects (
            schema_object_sha256 TEXT PRIMARY KEY,
            object_type TEXT NOT NULL,
            object_name TEXT NOT NULL,
            table_name TEXT NOT NULL,
            rootpage INTEGER NOT NULL,
            sql_text TEXT,
            object_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS runtime_archive_snapshot_schema (
            snapshot_sha256 TEXT NOT NULL,
            schema_ordinal INTEGER NOT NULL,
            schema_object_sha256 TEXT NOT NULL,
            PRIMARY KEY (snapshot_sha256, schema_ordinal),
            FOREIGN KEY (snapshot_sha256)
                REFERENCES runtime_archive_snapshots(snapshot_sha256),
            FOREIGN KEY (schema_object_sha256)
                REFERENCES runtime_archive_schema_objects(schema_object_sha256)
        ) WITHOUT ROWID;

        CREATE TABLE IF NOT EXISTS runtime_archive_records (
            record_sha256 TEXT PRIMARY KEY,
            source_table TEXT NOT NULL,
            record_json TEXT NOT NULL,
            record_size_bytes INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS runtime_archive_record_occurrences (
            snapshot_sha256 TEXT NOT NULL,
            source_table TEXT NOT NULL,
            occurrence_ordinal INTEGER NOT NULL,
            record_sha256 TEXT NOT NULL,
            locator_json TEXT NOT NULL,
            PRIMARY KEY (snapshot_sha256, source_table, occurrence_ordinal),
            FOREIGN KEY (snapshot_sha256)
                REFERENCES runtime_archive_snapshots(snapshot_sha256),
            FOREIGN KEY (record_sha256)
                REFERENCES runtime_archive_records(record_sha256)
        ) WITHOUT ROWID;

        CREATE INDEX IF NOT EXISTS idx_runtime_archive_occurrence_record
            ON runtime_archive_record_occurrences(record_sha256);

        CREATE TABLE IF NOT EXISTS runtime_archive_imports (
            import_id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at_utc TEXT NOT NULL,
            ended_at_utc TEXT,
            mode TEXT NOT NULL,
            source_dir TEXT NOT NULL,
            target_db TEXT NOT NULL,
            backup_path TEXT NOT NULL,
            stats_json TEXT
        );

        CREATE TABLE IF NOT EXISTS runtime_archive_failures (
            import_id INTEGER NOT NULL,
            source_file TEXT NOT NULL,
            errors_json TEXT NOT NULL,
            FOREIGN KEY (import_id) REFERENCES runtime_archive_imports(import_id)
        );
        """
    )
    con.execute(
        "INSERT OR REPLACE INTO runtime_archive_meta(key, value) VALUES (?, ?)",
        ("archive_schema_version", ARCHIVE_SCHEMA_VERSION),
    )
    con.execute(
        "INSERT OR REPLACE INTO runtime_archive_meta(key, value) VALUES (?, ?)",
        ("writer_version", SCRIPT_VERSION),
    )


def insert_source_snapshot(
    target: sqlite3.Connection,
    source: sqlite3.Connection,
    scan: SourceScan,
) -> dict[str, int]:
    counters = {
        "new_snapshots": 0,
        "new_source_file_links": 0,
        "new_schema_objects": 0,
        "new_schema_links": 0,
        "new_records": 0,
        "new_occurrences": 0,
    }
    timestamp = now_utc()
    cursor = target.execute(
        """
        INSERT OR IGNORE INTO runtime_archive_snapshots(
            snapshot_sha256, integrity_check, pragmas_json, schema_object_count,
            table_count, row_occurrence_count, unique_record_count, imported_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scan.snapshot_sha256,
            scan.integrity_check,
            scan.pragmas_json,
            len(scan.schema_objects),
            len(scan.tables),
            scan.row_occurrence_count,
            len(scan.unique_record_hashes),
            timestamp,
        ),
    )
    counters["new_snapshots"] += max(cursor.rowcount, 0)
    if counters["new_snapshots"] == 0:
        existing_snapshot = target.execute(
            """
            SELECT integrity_check, pragmas_json, schema_object_count, table_count,
                   row_occurrence_count, unique_record_count
            FROM runtime_archive_snapshots WHERE snapshot_sha256=?
            """,
            (scan.snapshot_sha256,),
        ).fetchone()
        expected_snapshot = (
            scan.integrity_check,
            scan.pragmas_json,
            len(scan.schema_objects),
            len(scan.tables),
            scan.row_occurrence_count,
            len(scan.unique_record_hashes),
        )
        if existing_snapshot != expected_snapshot:
            raise RuntimeError(
                f"Snapshot hash collision or inconsistent archive row: {scan.snapshot_sha256}"
            )

    cursor = target.execute(
        """
        INSERT OR IGNORE INTO runtime_archive_snapshot_files(
            snapshot_sha256, source_file, source_file_sha256, source_wal_sha256,
            source_size_bytes, source_mtime_ns, first_seen_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scan.snapshot_sha256,
            scan.source_file,
            scan.source_file_sha256,
            scan.source_wal_sha256,
            scan.source_size_bytes,
            scan.source_mtime_ns,
            timestamp,
        ),
    )
    counters["new_source_file_links"] += max(cursor.rowcount, 0)

    for ordinal, schema_object in enumerate(scan.schema_objects, start=1):
        object_json = canonical_json(schema_object)
        object_sha256 = sha256_text(object_json)
        cursor = target.execute(
            """
            INSERT OR IGNORE INTO runtime_archive_schema_objects(
                schema_object_sha256, object_type, object_name, table_name,
                rootpage, sql_text, object_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                object_sha256,
                str(schema_object["type"]),
                str(schema_object["name"]),
                str(schema_object["table_name"]),
                int(schema_object["rootpage"] or 0),
                schema_object["sql"],
                object_json,
            ),
        )
        counters["new_schema_objects"] += max(cursor.rowcount, 0)
        if cursor.rowcount == 0:
            existing_object_json = target.execute(
                """
                SELECT object_json FROM runtime_archive_schema_objects
                WHERE schema_object_sha256=?
                """,
                (object_sha256,),
            ).fetchone()
            if existing_object_json is None or existing_object_json[0] != object_json:
                raise RuntimeError(
                    f"Schema object hash collision: {object_sha256}"
                )
        cursor = target.execute(
            """
            INSERT OR IGNORE INTO runtime_archive_snapshot_schema(
                snapshot_sha256, schema_ordinal, schema_object_sha256
            ) VALUES (?, ?, ?)
            """,
            (scan.snapshot_sha256, ordinal, object_sha256),
        )
        counters["new_schema_links"] += max(cursor.rowcount, 0)

    for table in table_names(source):
        for ordinal, record_sha256, record_json, locator_json, _columns, _pk in iter_table_records(
            source, table
        ):
            cursor = target.execute(
                """
                INSERT OR IGNORE INTO runtime_archive_records(
                    record_sha256, source_table, record_json, record_size_bytes
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    record_sha256,
                    table,
                    record_json,
                    len(record_json.encode("utf-8", errors="surrogatepass")),
                ),
            )
            counters["new_records"] += max(cursor.rowcount, 0)
            if cursor.rowcount == 0:
                existing_record = target.execute(
                    """
                    SELECT source_table, record_json FROM runtime_archive_records
                    WHERE record_sha256=?
                    """,
                    (record_sha256,),
                ).fetchone()
                if existing_record != (table, record_json):
                    raise RuntimeError(f"Record hash collision: {record_sha256}")
            cursor = target.execute(
                """
                INSERT OR IGNORE INTO runtime_archive_record_occurrences(
                    snapshot_sha256, source_table, occurrence_ordinal,
                    record_sha256, locator_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    scan.snapshot_sha256,
                    table,
                    ordinal,
                    record_sha256,
                    locator_json,
                ),
            )
            counters["new_occurrences"] += max(cursor.rowcount, 0)

    schema_link_count = target.execute(
        """
        SELECT COUNT(*) FROM runtime_archive_snapshot_schema
        WHERE snapshot_sha256=?
        """,
        (scan.snapshot_sha256,),
    ).fetchone()[0]
    occurrence_count, distinct_record_count = target.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT record_sha256)
        FROM runtime_archive_record_occurrences
        WHERE snapshot_sha256=?
        """,
        (scan.snapshot_sha256,),
    ).fetchone()
    if schema_link_count != len(scan.schema_objects):
        raise RuntimeError(
            f"Schema verification failed for {scan.source_file}: "
            f"expected {len(scan.schema_objects)}, archived {schema_link_count}"
        )
    if occurrence_count != scan.row_occurrence_count:
        raise RuntimeError(
            f"Occurrence verification failed for {scan.source_file}: "
            f"expected {scan.row_occurrence_count}, archived {occurrence_count}"
        )
    if distinct_record_count != len(scan.unique_record_hashes):
        raise RuntimeError(
            f"Unique-record verification failed for {scan.source_file}: "
            f"expected {len(scan.unique_record_hashes)}, archived {distinct_record_count}"
        )

    return counters


def default_backup_path(target: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return target.with_name(target.name + f".before_runtime_archive_{stamp}.bak")


def preflight(
    root: Path,
    source_dir: Path,
    target: Path,
    patterns: Sequence[str],
) -> tuple[dict[str, Any], list[SourceScan]]:
    sources = discover_sources(source_dir, patterns)
    scans = [inspect_source(path, root) for path in sources]
    global_hashes: set[str] = set()
    total_occurrences = 0
    for scan in scans:
        global_hashes.update(scan.unique_record_hashes)
        total_occurrences += scan.row_occurrence_count

    report = {
        "script_version": SCRIPT_VERSION,
        "mode": "dry-run",
        "root": str(root.resolve()),
        "source_dir": safe_rel(source_dir, root),
        "target_db": safe_rel(target, root),
        "source_patterns": list(patterns),
        "source_count": len(scans),
        "healthy_source_count": sum(scan.healthy for scan in scans),
        "failed_source_count": sum(not scan.healthy for scan in scans),
        "row_occurrence_count": total_occurrences,
        "unique_record_count_across_sources": len(global_hashes),
        "exact_duplicate_occurrences_across_sources": total_occurrences - len(global_hashes),
        "target_before": archive_status(target),
        "sources": [scan.report() for scan in scans],
        "truth_boundary": (
            "Exact hashes only. Similar text is never merged. Failed SQLite sources are "
            "not silently treated as copied."
        ),
    }
    return report, scans


def apply_archive(
    root: Path,
    source_dir: Path,
    target: Path,
    patterns: Sequence[str],
    backup: Path | None,
    allow_partial: bool,
) -> dict[str, Any]:
    report, scans = preflight(root, source_dir, target, patterns)
    report["mode"] = "apply"

    if not target.is_file():
        report["status"] = "blocked"
        report["errors"] = [f"Target database does not exist: {target}"]
        return report

    failed = [scan for scan in scans if not scan.healthy]
    if failed and not allow_partial:
        report["status"] = "blocked"
        report["errors"] = [
            "At least one source is unreadable or unhealthy. Nothing was written. "
            "Use --allow-partial only if knowingly accepting that those sources remain uncopied."
        ]
        return report

    backup_path = (backup or default_backup_path(target)).resolve()
    create_target_backup(target, backup_path)
    report["backup_path"] = safe_rel(backup_path, root)

    totals: Counter[str] = Counter()
    actual_sources: list[dict[str, Any]] = []
    started_at = now_utc()

    target_con = sqlite3.connect(str(target), timeout=60.0)
    try:
        target_con.execute("PRAGMA foreign_keys = ON")
        create_archive_schema(target_con)
        import_cursor = target_con.execute(
            """
            INSERT INTO runtime_archive_imports(
                started_at_utc, mode, source_dir, target_db, backup_path
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                started_at,
                "allow-partial" if allow_partial else "complete-only",
                safe_rel(source_dir, root),
                safe_rel(target, root),
                safe_rel(backup_path, root),
            ),
        )
        import_id = int(import_cursor.lastrowid)

        for preflight_scan in scans:
            if not preflight_scan.healthy:
                target_con.execute(
                    """
                    INSERT INTO runtime_archive_failures(import_id, source_file, errors_json)
                    VALUES (?, ?, ?)
                    """,
                    (
                        import_id,
                        preflight_scan.source_file,
                        canonical_json(preflight_scan.errors),
                    ),
                )
                totals["failed_sources"] += 1
                continue

            with closing(open_readonly(preflight_scan.path)) as source_con:
                actual_scan = scan_open_connection(preflight_scan.path, root, source_con)
                actual_sources.append(actual_scan.report())
                if not actual_scan.healthy:
                    if not allow_partial:
                        raise sqlite3.DatabaseError(
                            f"Source became unreadable during apply: {actual_scan.source_file}: "
                            + "; ".join(actual_scan.errors)
                        )
                    target_con.execute(
                        """
                        INSERT INTO runtime_archive_failures(import_id, source_file, errors_json)
                        VALUES (?, ?, ?)
                        """,
                        (
                            import_id,
                            actual_scan.source_file,
                            canonical_json(actual_scan.errors),
                        ),
                    )
                    totals["failed_sources"] += 1
                    continue

                counters = insert_source_snapshot(target_con, source_con, actual_scan)
                totals.update(counters)
                totals["processed_sources"] += 1

        ended_at = now_utc()
        stats = dict(totals)
        target_con.execute(
            """
            UPDATE runtime_archive_imports
            SET ended_at_utc=?, stats_json=?
            WHERE import_id=?
            """,
            (ended_at, canonical_json(stats), import_id),
        )
        target_con.commit()
    except Exception:
        target_con.rollback()
        raise
    finally:
        target_con.close()

    report["status"] = "completed"
    report["apply_stats"] = dict(totals)
    report["actual_sources"] = actual_sources
    report["target_after"] = archive_status(target)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Losslessly archive workspace_runtime SQLite databases in separate "
            "runtime_archive_* tables of the main chat context database."
        )
    )
    parser.add_argument("--root", default=".", help="Project root. Default: current directory.")
    parser.add_argument(
        "--source-dir",
        default=DEFAULT_SOURCE_DIR,
        help=f"Source directory relative to root. Default: {DEFAULT_SOURCE_DIR}",
    )
    parser.add_argument(
        "--target",
        default=DEFAULT_TARGET,
        help=f"Target SQLite database relative to root. Default: {DEFAULT_TARGET}",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=None,
        help="Source glob inside source-dir. Repeatable. Default: *.sqlite3",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write archive tables after creating a consistent target backup.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Skip unreadable sources during --apply and record the failures.",
    )
    parser.add_argument(
        "--backup",
        default=None,
        help="Explicit backup path. Only used with --apply.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    source_dir = (root / args.source_dir).resolve()
    target = (root / args.target).resolve()
    patterns = args.include or ["*.sqlite3"]
    backup = Path(args.backup).resolve() if args.backup else None

    if not source_dir.is_dir():
        print(
            canonical_json(
                {
                    "script_version": SCRIPT_VERSION,
                    "status": "blocked",
                    "errors": [f"Source directory does not exist: {source_dir}"],
                }
            )
        )
        return 2

    try:
        if args.apply:
            report = apply_archive(
                root=root,
                source_dir=source_dir,
                target=target,
                patterns=patterns,
                backup=backup,
                allow_partial=args.allow_partial,
            )
        else:
            report, _scans = preflight(root, source_dir, target, patterns)
            report["status"] = (
                "ready" if report["failed_source_count"] == 0 else "blocked_by_unreadable_sources"
            )
    except Exception as exc:
        report = {
            "script_version": SCRIPT_VERSION,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") in {"ready", "completed"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
