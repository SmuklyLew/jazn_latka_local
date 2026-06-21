from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import defaultdict
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote


VERSION = "plan_memory_unification/v1-readonly"

TEXT_KEY_HINTS = (
    "text", "body", "content", "message", "rendered", "reply", "response",
    "scene", "note", "notes", "title", "summary", "reflection", "meaning",
    "treść", "tresc", "opis", "wpis", "payload", "raw", "excerpt",
    "moje_odczucia", "refleksja", "analiza",
)

TIME_KEY_HINTS = (
    "created", "created_at", "created_at_utc", "created_at_local",
    "timestamp", "time", "date", "data", "local_time", "updated",
)

NOISY_TEXT_KEYS = {
    "tags_json", "participants_json", "source", "grounding", "confidence",
    "sha256", "hash", "id", "rowid", "episode_id", "event_id", "journal_id",
    "reflection_id", "conversation_id", "message_id",
}

IMPORTANT_TABLES = {
    "episodic_memories",
    "journal",
    "reflection_entries",
    "events",
    "truth_audits",
    "semantic_facts",
    "legacy_messages",
    "legacy_conversations",
    "procedural_rules",
}

ARCHIVE_DB_NAME_RE = re.compile(r"latka_jazn_v(?P<version>[0-9_]+)\.sqlite3$", re.IGNORECASE)


@dataclass
class MemoryItem:
    source_kind: str
    source_file: str
    source_role: str
    container: str
    row_id: str
    item_kind: str
    timestamp: str | None
    timestamp_day: str | None
    title: str | None
    text_preview: str
    normalized_text: str
    content_sha256: str
    raw_sha256: str
    raw_length: int
    dedupe_key: str
    soft_key: str
    schema_hint: dict[str, Any]


@dataclass
class PlanCandidate:
    action: str
    confidence: str
    reason: str
    item: MemoryItem
    duplicate_sources: list[dict[str, Any]]
    conflict_sources: list[dict[str, Any]]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except Exception:
            value = str(value)
    text = str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def short(value: Any, limit: int = 420) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def timestamp_day(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", str(value))
    return match.group(1) if match else None


def safe_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except Exception:
        return str(path)


def sqlite_readonly_uri(path: Path) -> str:
    # Windows-safe URI. mode=ro prevents accidental creation or writes.
    return "file:" + quote(str(path.resolve()).replace("\\", "/"), safe="/:") + "?mode=ro"


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def is_time_key(name: str) -> bool:
    low = name.lower()
    return any(h in low for h in TIME_KEY_HINTS)


def is_text_key(name: str) -> bool:
    low = name.lower()
    return any(h in low for h in TEXT_KEY_HINTS)


def looks_like_versioned_sqlite(path: Path) -> bool:
    return bool(ARCHIVE_DB_NAME_RE.search(path.name))


def guess_source_role(path: Path, root: Path, active_db: Path, active_journal: Path) -> str:
    rel = safe_rel(path, root)
    if path.resolve() == active_db.resolve():
        return "active_sqlite"
    if path.resolve() == active_journal.resolve():
        return "active_journal_json"
    if rel.startswith("memory/versioned_sources/"):
        return "versioned_journal_source"
    if path.suffix.lower() == ".sqlite3":
        if path.name == "dictionary_cache.sqlite3":
            return "dictionary_cache"
        if looks_like_versioned_sqlite(path):
            return "sqlite_snapshot"
        return "sqlite_other"
    return "json_other"


def find_files(root: Path) -> tuple[list[Path], list[Path]]:
    sqlite_files = sorted(
        p for p in root.rglob("*.sqlite3")
        if ".git" not in p.parts and p.is_file()
    )
    journal_files = sorted(
        p for p in root.rglob("dziennik.json*")
        if ".git" not in p.parts and p.is_file()
    )
    return sqlite_files, journal_files


def choose_default_active_db(root: Path, sqlite_files: list[Path]) -> Path | None:
    preferred = root / "workspace_runtime" / "latka_jazn_v14_8_2.sqlite3"
    if preferred.exists():
        return preferred

    candidates = [
        p for p in sqlite_files
        if p.name != "dictionary_cache.sqlite3" and looks_like_versioned_sqlite(p)
    ]
    if not candidates:
        return None

    # Prefer largest healthy-looking latest snapshot if exact v14_8_2 is missing.
    return sorted(candidates, key=lambda p: (p.stat().st_size, p.name), reverse=True)[0]


def choose_default_active_journal(root: Path) -> Path:
    return root / "memory" / "raw" / "dziennik.json"


def load_sqlite_tables(path: Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    info: dict[str, Any] = {
        "path": str(path),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "sha256": file_sha256(path) if path.exists() else None,
        "opened_readonly": False,
        "integrity_check": None,
        "tables": {},
        "errors": errors,
    }
    try:
        with closing(sqlite3.connect(sqlite_readonly_uri(path), uri=True, timeout=2.0)) as con:
            con.row_factory = sqlite3.Row
            info["opened_readonly"] = True
            try:
                info["integrity_check"] = con.execute("PRAGMA integrity_check").fetchone()[0]
            except Exception as exc:
                errors.append(f"integrity_check: {exc}")
                return info, errors

            rows = con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            ).fetchall()
            for row in rows:
                table = str(row["name"])
                try:
                    cols = con.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
                    count = con.execute(f"SELECT COUNT(*) FROM {quote_ident(table)}").fetchone()[0]
                    info["tables"][table] = {
                        "row_count": count,
                        "columns": [
                            {
                                "name": str(c["name"]),
                                "type": str(c["type"] or ""),
                                "pk": int(c["pk"] or 0),
                                "notnull": int(c["notnull"] or 0),
                            }
                            for c in cols
                        ],
                    }
                except Exception as exc:
                    info["tables"][table] = {"error": str(exc)}
    except Exception as exc:
        errors.append(f"open_readonly: {exc}")
    return info, errors


def sqlite_text_columns(columns: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    names = [c["name"] for c in columns]
    text_cols: list[str] = []
    time_cols: list[str] = []
    title_cols: list[str] = []

    for c in columns:
        name = str(c["name"])
        low = name.lower()
        typ = str(c.get("type") or "").upper()

        if is_time_key(low):
            time_cols.append(name)

        if low in {"title", "tytuł", "tytul", "kind", "type", "event_type", "kategoria", "typ"}:
            title_cols.append(name)

        if low in NOISY_TEXT_KEYS:
            continue

        # For SQLite memories, payload_json and scene/text/raw_excerpt are important.
        if is_text_key(low):
            text_cols.append(name)
            continue

        # Some old schemas may have TEXT columns with unexpected names.
        if "TEXT" in typ and low not in {"source", "actor", "grounding", "lang"}:
            text_cols.append(name)

    # Avoid scanning tables that only expose IDs/tags.
    text_cols = [c for c in text_cols if c in names]
    return text_cols, time_cols, title_cols


def make_memory_item(
    *,
    root: Path,
    source_kind: str,
    source_file: Path,
    source_role: str,
    container: str,
    row_id: str,
    item_kind: str,
    timestamp: str | None,
    title: str | None,
    text: Any,
    schema_hint: dict[str, Any] | None = None,
) -> MemoryItem | None:
    raw = "" if text is None else str(text)
    normalized = normalize_text(raw)
    if len(normalized) < 3:
        return None

    day = timestamp_day(timestamp)
    content_hash = sha256_text(normalized)
    raw_hash = sha256_text(raw)

    # Dedupe key is content-based so the same text from old snapshots is not imported many times.
    # Soft key helps detect conflicts around same day/type/title with different text.
    kind_norm = normalize_text(item_kind) or "unknown"
    title_norm = normalize_text(title)[:80] if title else ""
    soft_key = "|".join([day or "no-date", kind_norm, title_norm])

    return MemoryItem(
        source_kind=source_kind,
        source_file=safe_rel(source_file, root),
        source_role=source_role,
        container=container,
        row_id=row_id,
        item_kind=item_kind,
        timestamp=timestamp,
        timestamp_day=day,
        title=short(title, 180) if title else None,
        text_preview=short(raw, 480),
        normalized_text=normalized,
        content_sha256=content_hash,
        raw_sha256=raw_hash,
        raw_length=len(raw),
        dedupe_key=content_hash,
        soft_key=soft_key,
        schema_hint=schema_hint or {},
    )


def extract_items_from_sqlite(root: Path, db: Path, active_db: Path, active_journal: Path, max_rows_per_table: int | None = None) -> tuple[dict[str, Any], list[MemoryItem]]:
    role = guess_source_role(db, root, active_db, active_journal)
    summary, errors = load_sqlite_tables(db)
    items: list[MemoryItem] = []
    rel = safe_rel(db, root)

    if errors or summary.get("integrity_check") != "ok":
        summary["skipped_for_items"] = True
        summary["skip_reason"] = "database not healthy or not readable read-only"
        return summary, items

    if role == "dictionary_cache":
        summary["skipped_for_items"] = True
        summary["skip_reason"] = "dictionary cache is not runtime memory"
        return summary, items

    try:
        with closing(sqlite3.connect(sqlite_readonly_uri(db), uri=True, timeout=2.0)) as con:
            con.row_factory = sqlite3.Row

            for table, table_info in summary.get("tables", {}).items():
                if table_info.get("error"):
                    continue

                # Scan important memory tables first; skip unknown empty/noisy tables.
                columns = table_info.get("columns") or []
                text_cols, time_cols, title_cols = sqlite_text_columns(columns)
                if not text_cols:
                    continue

                col_names = [c["name"] for c in columns]
                select_cols = col_names
                sql = "SELECT rowid AS __rowid__, " + ", ".join(quote_ident(c) for c in select_cols) + f" FROM {quote_ident(table)}"
                if max_rows_per_table:
                    sql += f" LIMIT {int(max_rows_per_table)}"

                for row in con.execute(sql):
                    timestamp = None
                    title = None

                    for c in time_cols:
                        try:
                            if row[c]:
                                timestamp = str(row[c])
                                break
                        except Exception:
                            pass

                    for c in title_cols:
                        try:
                            if row[c]:
                                title = str(row[c])
                                break
                        except Exception:
                            pass

                    parts: list[str] = []
                    for c in text_cols:
                        try:
                            val = row[c]
                        except Exception:
                            continue
                        if val is None:
                            continue
                        sval = str(val)
                        if not sval.strip():
                            continue
                        # payload_json can be huge but important. Keep it in hash; preview will be shortened.
                        parts.append(sval)

                    if not parts:
                        continue

                    item = make_memory_item(
                        root=root,
                        source_kind="sqlite",
                        source_file=db,
                        source_role=role,
                        container=table,
                        row_id=str(row["__rowid__"]),
                        item_kind=f"sqlite:{table}",
                        timestamp=timestamp,
                        title=title,
                        text="\n".join(parts),
                        schema_hint={
                            "table": table,
                            "columns_used": text_cols,
                            "db_integrity": summary.get("integrity_check"),
                        },
                    )
                    if item:
                        items.append(item)

    except Exception as exc:
        summary.setdefault("errors", []).append(f"extract_items: {exc}")

    summary["extracted_item_count"] = len(items)
    summary["path_rel"] = rel
    return summary, items


def load_json(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    return json.loads(text)


def iter_json_entries(data: Any, path_hint: str = "$"):
    if isinstance(data, list):
        for i, item in enumerate(data):
            yield from iter_json_entries(item, f"{path_hint}[{i}]")
    elif isinstance(data, dict):
        # Prefer explicit entries list if present.
        if isinstance(data.get("entries"), list):
            for i, item in enumerate(data["entries"]):
                yield from iter_json_entries(item, f"{path_hint}.entries[{i}]")
            return

        yield path_hint, data

        for key, value in data.items():
            if key in {"meta", "metadata"}:
                continue
            if isinstance(value, list):
                for i, item in enumerate(value):
                    yield from iter_json_entries(item, f"{path_hint}.{key}[{i}]")
            elif isinstance(value, dict) and any(k in value for k in ("entries", "wpisy", "items")):
                yield from iter_json_entries(value, f"{path_hint}.{key}")


def extract_text_from_json_entry(entry: dict[str, Any]) -> tuple[str | None, str | None, str, str]:
    timestamp = None
    title = None
    kind = None
    parts: list[str] = []

    for key, value in entry.items():
        low = str(key).lower()

        if timestamp is None and is_time_key(low) and not isinstance(value, (dict, list)):
            timestamp = str(value)

        if title is None and low in {"title", "tytuł", "tytul", "nazwa"}:
            title = str(value)

        if kind is None and low in {"kind", "type", "typ", "kategoria"}:
            kind = str(value)

        if low in {"meta", "metadata"}:
            continue

        if is_text_key(low) or low in {
            "treść", "tresc", "refleksja_latki", "moje_odczucia_latki",
            "notatka_introspekcyjna", "podsumowanie", "analiza",
        }:
            if isinstance(value, (dict, list)):
                parts.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
            else:
                parts.append(str(value))

    if not parts:
        # Fallback: whole object, but only if it looks like a meaningful entry.
        keys = " ".join(str(k).lower() for k in entry.keys())
        if any(h in keys for h in TEXT_KEY_HINTS + TIME_KEY_HINTS):
            parts.append(json.dumps(entry, ensure_ascii=False, sort_keys=True))

    return timestamp, title, "\n".join(parts), kind or "json_entry"


def extract_items_from_json(root: Path, jf: Path, active_db: Path, active_journal: Path) -> tuple[dict[str, Any], list[MemoryItem]]:
    role = guess_source_role(jf, root, active_db, active_journal)
    rel = safe_rel(jf, root)
    summary: dict[str, Any] = {
        "path": rel,
        "size_bytes": jf.stat().st_size,
        "sha256": file_sha256(jf),
        "source_role": role,
        "json_loaded": False,
        "entry_candidates": 0,
        "extracted_item_count": 0,
        "errors": [],
    }
    items: list[MemoryItem] = []

    try:
        data = load_json(jf)
        summary["json_loaded"] = True
        summary["top_type"] = type(data).__name__
        if isinstance(data, dict):
            summary["top_keys"] = list(data.keys())[:50]
        elif isinstance(data, list):
            summary["top_length"] = len(data)
    except Exception as exc:
        summary["errors"].append(f"json_load: {exc}")
        return summary, items

    for idx, (path_hint, entry) in enumerate(iter_json_entries(data), start=1):
        if not isinstance(entry, dict):
            continue

        timestamp, title, body, kind = extract_text_from_json_entry(entry)
        summary["entry_candidates"] += 1

        item = make_memory_item(
            root=root,
            source_kind="json",
            source_file=jf,
            source_role=role,
            container=path_hint,
            row_id=str(idx),
            item_kind=f"json:{kind}",
            timestamp=timestamp,
            title=title,
            text=body,
            schema_hint={
                "json_path": path_hint,
                "keys": list(entry.keys())[:40],
            },
        )
        if item:
            items.append(item)

    summary["extracted_item_count"] = len(items)
    return summary, items


def build_indexes(items: list[MemoryItem]) -> dict[str, Any]:
    by_hash: dict[str, list[MemoryItem]] = defaultdict(list)
    by_soft: dict[str, list[MemoryItem]] = defaultdict(list)
    by_role: dict[str, list[MemoryItem]] = defaultdict(list)

    for item in items:
        by_hash[item.dedupe_key].append(item)
        by_soft[item.soft_key].append(item)
        by_role[item.source_role].append(item)

    return {
        "by_hash": by_hash,
        "by_soft": by_soft,
        "by_role": by_role,
    }


def item_public_dict(item: MemoryItem, include_text: bool = False) -> dict[str, Any]:
    data = asdict(item)
    if not include_text:
        data.pop("normalized_text", None)
    return data


def source_brief(item: MemoryItem) -> dict[str, Any]:
    return {
        "source_kind": item.source_kind,
        "source_file": item.source_file,
        "source_role": item.source_role,
        "container": item.container,
        "row_id": item.row_id,
        "item_kind": item.item_kind,
        "timestamp": item.timestamp,
        "title": item.title,
        "text_preview": item.text_preview,
        "content_sha256": item.content_sha256,
    }


def build_plan(items: list[MemoryItem], active_db: Path, active_journal: Path, root: Path) -> tuple[dict[str, Any], list[PlanCandidate], list[dict[str, Any]], list[dict[str, Any]]]:
    idx = build_indexes(items)
    by_hash: dict[str, list[MemoryItem]] = idx["by_hash"]
    by_soft: dict[str, list[MemoryItem]] = idx["by_soft"]
    by_role: dict[str, list[MemoryItem]] = idx["by_role"]

    active_sqlite_hashes = {item.dedupe_key for item in by_role.get("active_sqlite", [])}
    active_journal_hashes = {item.dedupe_key for item in by_role.get("active_journal_json", [])}
    canonical_hashes = active_sqlite_hashes | active_journal_hashes

    candidates: list[PlanCandidate] = []

    # 1. Active journal entries missing in active SQLite.
    for item in by_role.get("active_journal_json", []):
        if item.dedupe_key not in active_sqlite_hashes:
            conflicts = [
                other for other in by_soft.get(item.soft_key, [])
                if other.dedupe_key != item.dedupe_key
            ]
            candidates.append(
                PlanCandidate(
                    action="IMPORT_ACTIVE_JOURNAL_TO_ACTIVE_SQLITE_CANDIDATE",
                    confidence="medium" if not conflicts else "low_conflict_review",
                    reason="Entry exists in memory/raw/dziennik.json but no exact normalized-text match was found in active SQLite.",
                    item=item,
                    duplicate_sources=[source_brief(x) for x in by_hash[item.dedupe_key] if x is not item],
                    conflict_sources=[source_brief(x) for x in conflicts[:20]],
                )
            )

    # 2. Active SQLite journal/reflection entries missing in active dziennik.json.
    for item in by_role.get("active_sqlite", []):
        if item.container in {"journal", "reflection_entries"} and item.dedupe_key not in active_journal_hashes:
            conflicts = [
                other for other in by_soft.get(item.soft_key, [])
                if other.dedupe_key != item.dedupe_key
            ]
            candidates.append(
                PlanCandidate(
                    action="EXPORT_ACTIVE_SQLITE_TO_CANONICAL_DZIENNIK_CANDIDATE",
                    confidence="medium" if not conflicts else "low_conflict_review",
                    reason="Entry exists in active SQLite journal/reflection layer but no exact normalized-text match was found in memory/raw/dziennik.json.",
                    item=item,
                    duplicate_sources=[source_brief(x) for x in by_hash[item.dedupe_key] if x is not item],
                    conflict_sources=[source_brief(x) for x in conflicts[:20]],
                )
            )

    # 3. Old DB unique material not in active DB/journal.
    for role in ("sqlite_snapshot", "sqlite_other"):
        for item in by_role.get(role, []):
            if item.dedupe_key not in canonical_hashes:
                conflicts = [
                    other for other in by_soft.get(item.soft_key, [])
                    if other.dedupe_key != item.dedupe_key
                ]
                candidates.append(
                    PlanCandidate(
                        action="REVIEW_OLD_SQLITE_UNIQUE_CANDIDATE",
                        confidence="low_manual_review",
                        reason="This content appears in an old SQLite source but not in the active SQLite or active journal by exact normalized hash. Do not import automatically.",
                        item=item,
                        duplicate_sources=[source_brief(x) for x in by_hash[item.dedupe_key] if x is not item],
                        conflict_sources=[source_brief(x) for x in conflicts[:20]],
                    )
                )

    # 4. Versioned journal unique material not in active DB/journal.
    for item in by_role.get("versioned_journal_source", []):
        if item.dedupe_key not in canonical_hashes:
            conflicts = [
                other for other in by_soft.get(item.soft_key, [])
                if other.dedupe_key != item.dedupe_key
            ]
            candidates.append(
                PlanCandidate(
                    action="REVIEW_VERSIONED_DZIENNIK_UNIQUE_CANDIDATE",
                    confidence="low_manual_review",
                    reason="This content appears in a versioned dziennik source but not in active SQLite or active dziennik by exact normalized hash. Do not import automatically.",
                    item=item,
                    duplicate_sources=[source_brief(x) for x in by_hash[item.dedupe_key] if x is not item],
                    conflict_sources=[source_brief(x) for x in conflicts[:20]],
                )
            )

    duplicate_groups: list[dict[str, Any]] = []
    for content_hash, group in by_hash.items():
        if len(group) <= 1:
            continue
        roles = sorted({g.source_role for g in group})
        duplicate_groups.append(
            {
                "content_sha256": content_hash,
                "count": len(group),
                "roles": roles,
                "sources": [source_brief(g) for g in group[:50]],
                "truncated": len(group) > 50,
            }
        )

    conflicts: list[dict[str, Any]] = []
    for soft_key, group in by_soft.items():
        hashes = sorted({g.dedupe_key for g in group})
        if len(hashes) <= 1:
            continue
        # This is intentionally conservative: same day/kind/title but different content.
        conflicts.append(
            {
                "soft_key": soft_key,
                "different_hashes": len(hashes),
                "items": [source_brief(g) for g in group[:50]],
                "truncated": len(group) > 50,
            }
        )

    summary = {
        "schema_version": VERSION,
        "created_at_utc": now_utc(),
        "root": str(root.resolve()),
        "active_db": safe_rel(active_db, root),
        "active_journal": safe_rel(active_journal, root),
        "target_active_db_recommendation": "workspace_runtime/latka_jazn_active.sqlite3",
        "target_active_journal_recommendation": "memory/raw/dziennik.json",
        "items_total": len(items),
        "items_by_role": {role: len(vals) for role, vals in sorted(by_role.items())},
        "unique_content_hashes": len(by_hash),
        "duplicate_groups": len(duplicate_groups),
        "soft_conflict_groups": len(conflicts),
        "candidates_total": len(candidates),
        "candidates_by_action": dict(sorted((action, sum(1 for c in candidates if c.action == action)) for action in {c.action for c in candidates})),
        "truth_boundary": (
            "This is a dry-run plan. It does not prove semantic equivalence. "
            "It finds exact normalized-text duplicates and conservative soft conflicts. "
            "Apply/migration must still use backup, unique keys and manual review for low-confidence candidates."
        ),
    }

    return summary, candidates, duplicate_groups, conflicts


def write_csv(path: Path, candidates: list[PlanCandidate]) -> None:
    fields = [
        "action", "confidence", "reason",
        "source_kind", "source_file", "source_role", "container", "row_id",
        "item_kind", "timestamp", "timestamp_day", "title", "text_preview",
        "content_sha256", "raw_sha256", "raw_length",
        "duplicate_count", "conflict_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for c in candidates:
            item = c.item
            writer.writerow(
                {
                    "action": c.action,
                    "confidence": c.confidence,
                    "reason": c.reason,
                    "source_kind": item.source_kind,
                    "source_file": item.source_file,
                    "source_role": item.source_role,
                    "container": item.container,
                    "row_id": item.row_id,
                    "item_kind": item.item_kind,
                    "timestamp": item.timestamp,
                    "timestamp_day": item.timestamp_day,
                    "title": item.title,
                    "text_preview": item.text_preview,
                    "content_sha256": item.content_sha256,
                    "raw_sha256": item.raw_sha256,
                    "raw_length": item.raw_length,
                    "duplicate_count": len(c.duplicate_sources),
                    "conflict_count": len(c.conflict_sources),
                }
            )


def write_markdown(path: Path, summary: dict[str, Any], db_summaries: list[dict[str, Any]], json_summaries: list[dict[str, Any]], candidates: list[PlanCandidate], duplicate_groups: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    lines.append("# Plan scalenia pamięci Jaźni — dry-run")
    lines.append("")
    lines.append(f"- Utworzono UTC: `{summary['created_at_utc']}`")
    lines.append(f"- Root: `{summary['root']}`")
    lines.append(f"- Aktywna baza źródłowa: `{summary['active_db']}`")
    lines.append(f"- Aktywny dziennik źródłowy: `{summary['active_journal']}`")
    lines.append(f"- Rekomendowana aktywna baza docelowa: `{summary['target_active_db_recommendation']}`")
    lines.append(f"- Rekomendowany aktywny dziennik docelowy: `{summary['target_active_journal_recommendation']}`")
    lines.append("")
    lines.append("## Najważniejsze liczby")
    lines.append("")
    lines.append(f"- Wszystkie odczytane elementy pamięci: `{summary['items_total']}`")
    lines.append(f"- Unikalne hashe treści: `{summary['unique_content_hashes']}`")
    lines.append(f"- Grupy duplikatów dokładnych: `{summary['duplicate_groups']}`")
    lines.append(f"- Grupy możliwych konfliktów miękkich: `{summary['soft_conflict_groups']}`")
    lines.append(f"- Kandydaci do działania: `{summary['candidates_total']}`")
    lines.append("")
    lines.append("### Kandydaci według akcji")
    lines.append("")
    for action, count in summary.get("candidates_by_action", {}).items():
        lines.append(f"- `{action}`: `{count}`")
    lines.append("")
    lines.append("## Zasada bezpieczeństwa")
    lines.append("")
    lines.append(
        "Ten plik jest tylko planem. Nie jest migracją. "
        "Po nim trzeba przejrzeć `migration_candidates.csv`, szczególnie pozycje z `low_manual_review` i `low_conflict_review`. "
        "Dopiero następny skrypt może utworzyć `latka_jazn_active.sqlite3`, ale tylko po backupie i z unikalnym kluczem deduplikacji."
    )
    lines.append("")
    lines.append("## Zdrowie baz SQLite")
    lines.append("")
    lines.append("| Baza | Rola | integrity_check | Tabele | Elementy odczytane | Błędy |")
    lines.append("|---|---|---:|---:|---:|---|")
    for s in db_summaries:
        path_rel = s.get("path_rel") or s.get("path") or s.get("absolute_path") or ""
        role = s.get("source_role") or ""
        integrity = s.get("integrity_check")
        tables = len(s.get("tables") or {})
        extracted = s.get("extracted_item_count", 0)
        errors = "; ".join(s.get("errors") or [])[:240]
        lines.append(f"| `{path_rel}` | `{role}` | `{integrity}` | {tables} | {extracted} | {errors} |")
    lines.append("")
    lines.append("## Pliki dziennika JSON")
    lines.append("")
    lines.append("| Plik | Rola | Kandydaci | Elementy odczytane | Błędy |")
    lines.append("|---|---|---:|---:|---|")
    for s in json_summaries:
        errors = "; ".join(s.get("errors") or [])[:240]
        lines.append(f"| `{s.get('path')}` | `{s.get('source_role')}` | {s.get('entry_candidates')} | {s.get('extracted_item_count')} | {errors} |")
    lines.append("")
    lines.append("## Pierwsze 50 kandydatów")
    lines.append("")
    lines.append("| Akcja | Pewność | Źródło | Kontener | Data | Podgląd |")
    lines.append("|---|---|---|---|---|---|")
    for c in candidates[:50]:
        item = c.item
        preview = item.text_preview.replace("|", "\\|")
        lines.append(
            f"| `{c.action}` | `{c.confidence}` | `{item.source_file}` | `{item.container}` | `{item.timestamp or ''}` | {preview[:220]} |"
        )
    lines.append("")
    lines.append("## Interpretacja")
    lines.append("")
    lines.append(
        "- `IMPORT_ACTIVE_JOURNAL_TO_ACTIVE_SQLITE_CANDIDATE`: wpis jest w aktywnym `dziennik.json`, ale nie ma dokładnego odpowiednika w aktywnej bazie."
    )
    lines.append(
        "- `EXPORT_ACTIVE_SQLITE_TO_CANONICAL_DZIENNIK_CANDIDATE`: wpis jest w aktywnej bazie w warstwie journal/reflection, ale nie ma dokładnego odpowiednika w aktywnym `dziennik.json`."
    )
    lines.append(
        "- `REVIEW_OLD_SQLITE_UNIQUE_CANDIDATE`: wpis jest tylko w starej bazie; nie wolno go importować automatycznie bez przeglądu."
    )
    lines.append(
        "- `REVIEW_VERSIONED_DZIENNIK_UNIQUE_CANDIDATE`: wpis jest tylko w wersjonowanym dzienniku; wymaga przeglądu."
    )
    lines.append("")
    lines.append("## Granica prawdy")
    lines.append("")
    lines.append(summary["truth_boundary"])
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_reports(out_dir: Path, summary: dict[str, Any], db_summaries: list[dict[str, Any]], json_summaries: list[dict[str, Any]], candidates: list[PlanCandidate], duplicate_groups: list[dict[str, Any]], conflicts: list[dict[str, Any]], include_normalized_text: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "plan_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "db_summaries.json").write_text(
        json.dumps(db_summaries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "json_summaries.json").write_text(
        json.dumps(json_summaries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "migration_candidates.json").write_text(
        json.dumps(
            [
                {
                    "action": c.action,
                    "confidence": c.confidence,
                    "reason": c.reason,
                    "item": item_public_dict(c.item, include_text=include_normalized_text),
                    "duplicate_sources": c.duplicate_sources,
                    "conflict_sources": c.conflict_sources,
                }
                for c in candidates
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (out_dir / "duplicate_groups.json").write_text(
        json.dumps(duplicate_groups[:2000], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "soft_conflicts.json").write_text(
        json.dumps(conflicts[:2000], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv(out_dir / "migration_candidates.csv", candidates)
    write_markdown(out_dir / "PLAN_MEMORY_UNIFICATION.md", summary, db_summaries, json_summaries, candidates, duplicate_groups, conflicts)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run planner for unifying Jaźń memory SQLite databases and dziennik.json files."
    )
    parser.add_argument("--root", default=".", help="Root folder of Jaźń system.")
    parser.add_argument("--active-db", default=None, help="Active SQLite database. Default: workspace_runtime/latka_jazn_v14_8_2.sqlite3 if present.")
    parser.add_argument("--active-journal", default=None, help="Active dziennik JSON. Default: memory/raw/dziennik.json.")
    parser.add_argument("--out", default="reports/memory_unification_plan", help="Output directory for the dry-run plan.")
    parser.add_argument("--max-rows-per-table", type=int, default=0, help="Debug limit. 0 means no limit.")
    parser.add_argument("--include-normalized-text", action="store_true", help="Include normalized full text in JSON reports. Produces larger files.")
    parser.add_argument("--apply", action="store_true", help="Reserved. This script intentionally refuses to modify data.")
    args = parser.parse_args()

    if args.apply:
        print("ODMOWA: plan_memory_unification.py jest tylko skryptem planującym dry-run.")
        print("Nie wykonuję migracji. Najpierw przejrzyj raporty i przygotuj osobny migrate_memory_unification.py.")
        return 2

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root does not exist: {root}", file=sys.stderr)
        return 1

    sqlite_files, journal_files = find_files(root)

    active_db = Path(args.active_db).resolve() if args.active_db else choose_default_active_db(root, sqlite_files)
    active_journal = Path(args.active_journal).resolve() if args.active_journal else choose_default_active_journal(root)

    if active_db is None or not active_db.exists():
        print("Nie znaleziono aktywnej bazy. Podaj --active-db.", file=sys.stderr)
        return 1

    if not active_journal.exists():
        print(f"Nie znaleziono aktywnego dziennika: {active_journal}", file=sys.stderr)
        return 1

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir

    all_items: list[MemoryItem] = []
    db_summaries: list[dict[str, Any]] = []
    json_summaries: list[dict[str, Any]] = []

    max_rows = args.max_rows_per_table if args.max_rows_per_table > 0 else None

    for db in sqlite_files:
        summary, items = extract_items_from_sqlite(root, db, active_db, active_journal, max_rows_per_table=max_rows)
        summary["source_role"] = guess_source_role(db, root, active_db, active_journal)
        db_summaries.append(summary)
        all_items.extend(items)

    for jf in journal_files:
        summary, items = extract_items_from_json(root, jf, active_db, active_journal)
        json_summaries.append(summary)
        all_items.extend(items)

    summary, candidates, duplicate_groups, conflicts = build_plan(all_items, active_db, active_journal, root)

    save_reports(
        out_dir,
        summary,
        db_summaries,
        json_summaries,
        candidates,
        duplicate_groups,
        conflicts,
        include_normalized_text=args.include_normalized_text,
    )

    print("Plan scalenia pamięci zakończony — DRY RUN.")
    print(f"Root: {root}")
    print(f"Active DB: {safe_rel(active_db, root)}")
    print(f"Active journal: {safe_rel(active_journal, root)}")
    print(f"Items total: {summary['items_total']}")
    print(f"Unique content hashes: {summary['unique_content_hashes']}")
    print(f"Duplicate groups: {summary['duplicate_groups']}")
    print(f"Soft conflict groups: {summary['soft_conflict_groups']}")
    print(f"Candidates total: {summary['candidates_total']}")
    print("Candidates by action:")
    for action, count in summary.get("candidates_by_action", {}).items():
        print(f"  - {action}: {count}")
    print()
    print(f"Reports: {out_dir}")
    print(f"Main report: {out_dir / 'PLAN_MEMORY_UNIFICATION.md'}")
    print()
    print("Nie wykonano migracji. To tylko plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())