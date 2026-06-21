from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path

from archive_workspace_runtime_sqlite import apply_archive, preflight


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_target(path: Path) -> None:
    path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(path)) as con:
        con.execute("CREATE TABLE messages(message_id TEXT PRIMARY KEY, content_text TEXT)")
        con.execute("INSERT INTO messages VALUES ('existing', 'do not change')")
        con.commit()


def make_source(path: Path, rows: list[tuple[int, str, bytes, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as con:
        con.execute(
            "CREATE TABLE memories(id INTEGER PRIMARY KEY, text TEXT, raw BLOB, weight REAL)"
        )
        con.executemany("INSERT INTO memories VALUES (?, ?, ?, ?)", rows)
        con.commit()


def test_dry_run_is_read_only_and_detects_exact_duplicates(tmp_path: Path) -> None:
    target = tmp_path / "memory" / "sqlite" / "chat_context.sqlite3"
    sources = tmp_path / "workspace_runtime"
    make_target(target)
    make_source(sources / "a.sqlite3", [(1, "pełna treść", b"\x00\xff", 0.5)])
    make_source(sources / "b.sqlite3", [(1, "pełna treść", b"\x00\xff", 0.5)])
    before = file_sha256(target)

    report, scans = preflight(tmp_path, sources, target, ["*.sqlite3"])

    assert file_sha256(target) == before
    assert report["source_count"] == 2
    assert report["healthy_source_count"] == 2
    assert report["row_occurrence_count"] == 2
    assert report["unique_record_count_across_sources"] == 1
    assert report["exact_duplicate_occurrences_across_sources"] == 1
    assert all(scan.healthy for scan in scans)


def test_identical_database_snapshots_share_records_but_keep_both_source_files(
    tmp_path: Path,
) -> None:
    target = tmp_path / "memory" / "sqlite" / "chat_context.sqlite3"
    sources = tmp_path / "workspace_runtime"
    backup = tmp_path / "backup.sqlite3"
    make_target(target)
    rows = [(1, "pełna treść", b"\x00\xff", 0.5)]
    make_source(sources / "a.sqlite3", rows)
    make_source(sources / "b.sqlite3", rows)

    report = apply_archive(
        tmp_path, sources, target, ["*.sqlite3"], backup, allow_partial=False
    )

    assert report["status"] == "completed"
    with closing(sqlite3.connect(target)) as con:
        assert con.execute("SELECT COUNT(*) FROM runtime_archive_snapshots").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM runtime_archive_snapshot_files").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM runtime_archive_records").fetchone()[0] == 1
        assert con.execute(
            "SELECT COUNT(*) FROM runtime_archive_record_occurrences"
        ).fetchone()[0] == 1


def test_apply_is_lossless_idempotent_and_preserves_existing_tables(tmp_path: Path) -> None:
    target = tmp_path / "memory" / "sqlite" / "chat_context.sqlite3"
    sources = tmp_path / "workspace_runtime"
    backup1 = tmp_path / "backup1.sqlite3"
    backup2 = tmp_path / "backup2.sqlite3"
    make_target(target)
    make_source(
        sources / "a.sqlite3",
        [
            (1, "pełna treść", b"\x00\xff", 0.5),
            (2, "tylko A", b"A", -0.0),
        ],
    )
    make_source(
        sources / "b.sqlite3",
        [
            (1, "pełna treść", b"\x00\xff", 0.5),
            (3, "tylko B", b"B", 1.25),
        ],
    )

    first = apply_archive(
        tmp_path, sources, target, ["*.sqlite3"], backup1, allow_partial=False
    )
    assert first["status"] == "completed"
    assert backup1.exists()

    with closing(sqlite3.connect(target)) as con:
        assert con.execute("SELECT content_text FROM messages").fetchone()[0] == "do not change"
        assert con.execute("SELECT COUNT(*) FROM runtime_archive_snapshots").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM runtime_archive_snapshot_files").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM runtime_archive_records").fetchone()[0] == 3
        assert con.execute(
            "SELECT COUNT(*) FROM runtime_archive_record_occurrences"
        ).fetchone()[0] == 4
        archived_json = con.execute(
            "SELECT record_json FROM runtime_archive_records "
            "WHERE record_json LIKE '%AP8=%'"
        ).fetchone()[0]
        assert r"\u0142" in archived_json
        assert '"base64":"AP8="' in archived_json
        assert '"hex":"0x1.0000000000000p-1"' in archived_json

    second = apply_archive(
        tmp_path, sources, target, ["*.sqlite3"], backup2, allow_partial=False
    )
    assert second["status"] == "completed"
    assert backup2.exists()
    assert second["apply_stats"]["new_snapshots"] == 0
    assert second["apply_stats"]["new_records"] == 0
    assert second["apply_stats"]["new_occurrences"] == 0

    with closing(sqlite3.connect(target)) as con:
        assert con.execute("SELECT COUNT(*) FROM runtime_archive_snapshots").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM runtime_archive_records").fetchone()[0] == 3
        assert con.execute(
            "SELECT COUNT(*) FROM runtime_archive_record_occurrences"
        ).fetchone()[0] == 4


def test_apply_blocks_before_writing_when_any_source_is_unreadable(tmp_path: Path) -> None:
    target = tmp_path / "memory" / "sqlite" / "chat_context.sqlite3"
    sources = tmp_path / "workspace_runtime"
    backup = tmp_path / "must_not_exist.sqlite3"
    make_target(target)
    make_source(sources / "healthy.sqlite3", [(1, "treść", b"x", 1.0)])
    (sources / "broken.sqlite3").write_bytes(b"not a sqlite database")
    before = file_sha256(target)

    report = apply_archive(
        tmp_path, sources, target, ["*.sqlite3"], backup, allow_partial=False
    )

    assert report["status"] == "blocked"
    assert not backup.exists()
    assert file_sha256(target) == before
    with closing(sqlite3.connect(target)) as con:
        names = {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_schema WHERE type='table'")
        }
    assert "runtime_archive_records" not in names
