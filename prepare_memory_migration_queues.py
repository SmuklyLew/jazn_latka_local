from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_VERSION = "prepare_memory_migration_queues/v1-readonly"

JSON_ENTRY_RE = re.compile(r"^\$\.entries\[\d+\]$")
JSON_ARRAY_INDEX_RE = re.compile(r"\[\d+\]")

JOURNAL_CONTAINERS = {
    "journal",
    "$.entries[*]",
}

REFLECTION_CONTAINERS = {
    "reflection_entries",
}

RUNTIME_MEMORY_CONTAINERS = {
    "episodic_memories",
    "semantic_facts",
    "procedural_rules",
}

TECHNICAL_AUDIT_CONTAINERS = {
    "truth_audits",
    "source_files",
    "meta",
    "events",
}

LEGACY_CONTAINERS = {
    "legacy_messages",
    "legacy_conversations",
}

SOURCE_INDEX_CONTAINERS = {
    "source_files",
}

DO_NOT_DIRECT_IMPORT_DOMAINS = {
    "technical_audit",
    "source_index",
    "legacy_source_index",
    "unknown_hold",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value)))
    except Exception:
        return default


def short(value: Any, limit: int = 320) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = " ".join(text.split())
    return text[:limit]


def safe_filename(value: str, limit: int = 120) -> str:
    cleaned = []
    for ch in value:
        if ch.isalnum() or ch in ("-", "_", "."):
            cleaned.append(ch)
        else:
            cleaned.append("_")
    name = "".join(cleaned).strip("_")
    return (name or "unknown")[:limit]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    try:
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        csv.field_size_limit(2_147_483_647)

    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            clean = {k: "" if v is None else str(v) for k, v in row.items()}
            clean["_input_row_number"] = str(idx)
            rows.append(clean)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_container(container: str) -> str:
    c = (container or "").strip()
    if JSON_ENTRY_RE.match(c):
        return "$.entries[*]"

    # Zachowuje rozpoznawalny schemat dla innych list JSON, np. $.foo[12].bar[3] -> $.foo[*].bar[*]
    if c.startswith("$"):
        return JSON_ARRAY_INDEX_RE.sub("[*]", c)

    return c or "unknown"


def classify_memory_domain(row: dict[str, str]) -> str:
    container = row.get("container_normalized") or normalize_container(row.get("container", ""))
    action = row.get("action", "")
    source_role = row.get("source_role", "")

    if container in JOURNAL_CONTAINERS:
        return "journal_memory"

    if container in REFLECTION_CONTAINERS:
        return "journal_reflection"

    if container in SOURCE_INDEX_CONTAINERS:
        return "source_index"

    if container in TECHNICAL_AUDIT_CONTAINERS:
        return "technical_audit"

    if container in LEGACY_CONTAINERS:
        return "legacy_source_index"

    if container in RUNTIME_MEMORY_CONTAINERS:
        return "runtime_memory"

    if action == "IMPORT_ACTIVE_JOURNAL_TO_ACTIVE_SQLITE_CANDIDATE" or source_role == "active_journal_json":
        return "journal_memory"

    return "unknown_hold"


def classify_target_layer(row: dict[str, str]) -> str:
    domain = row.get("memory_domain", "")
    action = row.get("action", "")

    if domain in {"technical_audit", "source_index"}:
        return "archive_audit_only"

    if domain == "legacy_source_index":
        return "legacy_index_only"

    if domain in {"journal_memory", "journal_reflection"}:
        if action == "IMPORT_ACTIVE_JOURNAL_TO_ACTIVE_SQLITE_CANDIDATE":
            return "active_sqlite_journal_layer"
        if action == "EXPORT_ACTIVE_SQLITE_TO_CANONICAL_DZIENNIK_CANDIDATE":
            return "canonical_dziennik_json"
        if action == "REVIEW_OLD_SQLITE_UNIQUE_CANDIDATE":
            return "review_for_journal_or_reflection_import"
        return "journal_layer_review"

    if domain == "runtime_memory":
        return "runtime_memory_layer_review"

    return "hold_unknown"


def classify_migration_decision(row: dict[str, str]) -> str:
    action = row.get("action", "")
    confidence = row.get("confidence", "")
    domain = row.get("memory_domain", "")
    target = row.get("target_layer", "")
    conflict_count = as_int(row.get("conflict_count"))
    duplicate_count = as_int(row.get("duplicate_count"))
    source_role = row.get("source_role", "")

    has_conflict = conflict_count > 0 or "conflict" in confidence
    is_old_snapshot = source_role == "sqlite_snapshot" or action == "REVIEW_OLD_SQLITE_UNIQUE_CANDIDATE"

    if domain in {"technical_audit", "source_index"}:
        return "ARCHIVE_ONLY_DO_NOT_IMPORT_TO_DZIENNIK"

    if domain == "legacy_source_index":
        return "INDEX_ONLY_DO_NOT_MERGE_AS_MEMORY"

    if domain == "unknown_hold":
        return "HOLD_UNKNOWN_REVIEW_REQUIRED"

    if has_conflict:
        return "MANUAL_REVIEW_REQUIRED_CONFLICT"

    if is_old_snapshot:
        if domain in {"journal_memory", "journal_reflection"}:
            return "OLD_SQLITE_JOURNAL_MANUAL_REVIEW"
        if domain == "runtime_memory":
            return "OLD_SQLITE_RUNTIME_MEMORY_MANUAL_REVIEW"
        return "OLD_SQLITE_MANUAL_REVIEW"

    if action == "IMPORT_ACTIVE_JOURNAL_TO_ACTIVE_SQLITE_CANDIDATE" and domain == "journal_memory":
        if confidence == "medium" and duplicate_count == 0:
            return "CAN_IMPORT_ACTIVE_JOURNAL_AFTER_BACKUP"
        return "ACTIVE_JOURNAL_IMPORT_REVIEW"

    if action == "EXPORT_ACTIVE_SQLITE_TO_CANONICAL_DZIENNIK_CANDIDATE":
        if domain in {"journal_memory", "journal_reflection"} and confidence == "medium":
            return "CAN_EXPORT_ACTIVE_SQLITE_TO_DZIENNIK_AFTER_BACKUP"
        return "ACTIVE_SQLITE_EXPORT_REVIEW"

    if domain == "runtime_memory":
        return "RUNTIME_MEMORY_REVIEW"

    return "MANUAL_REVIEW_REQUIRED"


def compute_risk(row: dict[str, str]) -> tuple[int, str]:
    decision = row.get("migration_decision", "")
    domain = row.get("memory_domain", "")
    confidence = row.get("confidence", "")
    conflict_count = as_int(row.get("conflict_count"))
    source_role = row.get("source_role", "")
    action = row.get("action", "")

    risk = 0
    flags: list[str] = []

    if conflict_count > 0 or "conflict" in confidence:
        risk += 55
        flags.append("conflict")

    if source_role == "sqlite_snapshot" or action == "REVIEW_OLD_SQLITE_UNIQUE_CANDIDATE":
        risk += 25
        flags.append("old_snapshot")

    if domain in {"technical_audit", "source_index"}:
        risk += 20
        flags.append("archive_only")

    if domain == "legacy_source_index":
        risk += 25
        flags.append("legacy_index_only")

    if domain == "unknown_hold":
        risk += 45
        flags.append("unknown_domain")

    if decision.startswith("CAN_"):
        risk -= 20
        flags.append("possible_batch_after_backup")

    if decision.startswith("ARCHIVE_ONLY") or decision.startswith("INDEX_ONLY"):
        flags.append("do_not_import_directly")

    risk = max(0, min(100, risk))

    if risk >= 70:
        priority = "P0_block_migration_until_review"
    elif risk >= 45:
        priority = "P1_manual_review"
    elif risk >= 20:
        priority = "P2_structured_batch_review"
    else:
        priority = "P3_batch_after_backup_candidate"

    return risk, priority + "|" + ";".join(flags)


def enrich_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    enriched: list[dict[str, str]] = []

    for row in rows:
        r = dict(row)

        r["container_normalized"] = normalize_container(r.get("container", ""))
        r["memory_domain"] = classify_memory_domain(r)
        r["target_layer"] = classify_target_layer(r)
        r["migration_decision"] = classify_migration_decision(r)

        risk, priority_flags = compute_risk(r)
        priority, _, flags = priority_flags.partition("|")
        r["pre_migration_priority"] = priority
        r["pre_migration_flags"] = flags
        r["pre_migration_risk_score"] = str(risk)

        if not r.get("text_preview_short"):
            r["text_preview_short"] = short(r.get("text_preview", ""), 320)
        else:
            r["text_preview_short"] = short(r.get("text_preview_short", ""), 320)

        enriched.append(r)

    return enriched


def count_by(rows: list[dict[str, str]], *fields: str) -> list[dict[str, Any]]:
    counter: Counter[tuple[str, ...]] = Counter()
    for row in rows:
        counter[tuple(row.get(f, "") or "" for f in fields)] += 1

    result: list[dict[str, Any]] = []
    for key, count in counter.most_common():
        item = {field: key[idx] for idx, field in enumerate(fields)}
        item["count"] = count
        result.append(item)
    return result


def output_fields(rows: list[dict[str, str]]) -> list[str]:
    preferred = [
        "_input_row_number",
        "pre_migration_priority",
        "pre_migration_risk_score",
        "pre_migration_flags",
        "migration_decision",
        "memory_domain",
        "target_layer",
        "action",
        "confidence",
        "reason",
        "source_kind",
        "source_file",
        "source_role",
        "container",
        "container_normalized",
        "row_id",
        "item_kind",
        "timestamp",
        "timestamp_day",
        "title",
        "text_preview_short",
        "content_sha256",
        "raw_sha256",
        "raw_length",
        "duplicate_count",
        "conflict_count",
    ]

    seen = set(preferred)
    rest: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                rest.append(key)

    return preferred + rest


def write_queue(out_dir: Path, name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    write_csv(out_dir / name, rows, fields)


def write_queues(out_dir: Path, rows: list[dict[str, str]], fields: list[str]) -> dict[str, int]:
    queues: dict[str, list[dict[str, str]]] = {
        "queue_can_import_active_journal_medium.csv": [
            r for r in rows
            if r["migration_decision"] == "CAN_IMPORT_ACTIVE_JOURNAL_AFTER_BACKUP"
        ],
        "queue_can_export_active_sqlite_journal_medium.csv": [
            r for r in rows
            if r["migration_decision"] == "CAN_EXPORT_ACTIVE_SQLITE_TO_DZIENNIK_AFTER_BACKUP"
        ],
        "queue_old_sqlite_journal_candidates_only.csv": [
            r for r in rows
            if r["migration_decision"] == "OLD_SQLITE_JOURNAL_MANUAL_REVIEW"
        ],
        "queue_old_sqlite_runtime_memory_candidates_only.csv": [
            r for r in rows
            if r["migration_decision"] == "OLD_SQLITE_RUNTIME_MEMORY_MANUAL_REVIEW"
        ],
        "queue_runtime_memory_candidates.csv": [
            r for r in rows
            if r["memory_domain"] == "runtime_memory"
        ],
        "queue_archive_technical_audit_only.csv": [
            r for r in rows
            if r["migration_decision"] == "ARCHIVE_ONLY_DO_NOT_IMPORT_TO_DZIENNIK"
        ],
        "queue_legacy_source_index_only.csv": [
            r for r in rows
            if r["migration_decision"] == "INDEX_ONLY_DO_NOT_MERGE_AS_MEMORY"
        ],
        "queue_do_not_import_directly.csv": [
            r for r in rows
            if r["memory_domain"] in DO_NOT_DIRECT_IMPORT_DOMAINS
            or r["migration_decision"] in {
                "ARCHIVE_ONLY_DO_NOT_IMPORT_TO_DZIENNIK",
                "INDEX_ONLY_DO_NOT_MERGE_AS_MEMORY",
                "HOLD_UNKNOWN_REVIEW_REQUIRED",
            }
        ],
        "queue_manual_conflicts.csv": [
            r for r in rows
            if r["migration_decision"] == "MANUAL_REVIEW_REQUIRED_CONFLICT"
        ],
        "queue_hold_unknown.csv": [
            r for r in rows
            if r["migration_decision"] == "HOLD_UNKNOWN_REVIEW_REQUIRED"
        ],
        "queue_p0_block_migration_until_review.csv": [
            r for r in rows
            if r["pre_migration_priority"] == "P0_block_migration_until_review"
        ],
        "queue_p1_manual_review.csv": [
            r for r in rows
            if r["pre_migration_priority"] == "P1_manual_review"
        ],
        "queue_p2_structured_batch_review.csv": [
            r for r in rows
            if r["pre_migration_priority"] == "P2_structured_batch_review"
        ],
        "queue_p3_batch_after_backup_candidate.csv": [
            r for r in rows
            if r["pre_migration_priority"] == "P3_batch_after_backup_candidate"
        ],
    }

    for name, subset in queues.items():
        write_queue(out_dir, name, subset, fields)

    # Dodatkowe grupy dla przeglądu.
    grouped_root = out_dir / "grouped"

    by_domain: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_decision: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_container: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_day: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        by_domain[row.get("memory_domain", "") or "unknown"].append(row)
        by_decision[row.get("migration_decision", "") or "unknown"].append(row)
        by_container[row.get("container_normalized", "") or "unknown"].append(row)
        by_day[row.get("timestamp_day", "") or "no_timestamp_day"].append(row)

    for key, subset in by_domain.items():
        write_csv(grouped_root / "by_memory_domain" / f"{safe_filename(key)}.csv", subset, fields)

    for key, subset in by_decision.items():
        write_csv(grouped_root / "by_migration_decision" / f"{safe_filename(key)}.csv", subset, fields)

    for key, subset in by_container.items():
        write_csv(grouped_root / "by_container_normalized" / f"{safe_filename(key)}.csv", subset, fields)

    for key, subset in by_day.items():
        write_csv(grouped_root / "by_timestamp_day" / f"{safe_filename(key)}.csv", subset, fields)

    return {name: len(subset) for name, subset in queues.items()}


def build_summary(rows: list[dict[str, str]], input_path: Path, queue_counts: dict[str, int]) -> dict[str, Any]:
    return {
        "schema_version": SCRIPT_VERSION,
        "created_at_utc": now_utc(),
        "input_csv": str(input_path),
        "total_candidates": len(rows),
        "unique_content_sha256": len({r.get("content_sha256", "") for r in rows if r.get("content_sha256")}),
        "by_memory_domain": count_by(rows, "memory_domain"),
        "by_target_layer": count_by(rows, "target_layer"),
        "by_migration_decision": count_by(rows, "migration_decision"),
        "by_pre_migration_priority": count_by(rows, "pre_migration_priority"),
        "by_action": count_by(rows, "action"),
        "by_action_and_decision": count_by(rows, "action", "migration_decision"),
        "by_container_normalized": count_by(rows, "container_normalized"),
        "top_source_files": count_by(rows, "source_file")[:50],
        "top_timestamp_days": count_by(rows, "timestamp_day")[:80],
        "queue_counts": queue_counts,
        "truth_boundary": (
            "To jest klasyfikator przed migracją. Nie wykonuje migracji, nie usuwa plików, "
            "nie scala wpisów i nie rozstrzyga semantycznej równoważności. "
            "Jego zadaniem jest oddzielenie pamięci dziennika, pamięci runtime, audytu technicznego, "
            "legacy index i pozycji wymagających ręcznego przeglądu."
        ),
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines: list[str] = []

    lines.append("# Pre-migration memory queues — klasyfikacja przed migracją")
    lines.append("")
    lines.append(f"- Utworzono UTC: `{summary['created_at_utc']}`")
    lines.append(f"- Wejście: `{summary['input_csv']}`")
    lines.append(f"- Kandydaci łącznie: `{summary['total_candidates']}`")
    lines.append(f"- Unikalne `content_sha256`: `{summary['unique_content_sha256']}`")
    lines.append("")
    lines.append("## Decyzja")
    lines.append("")
    lines.append(
        "Ten etap nie migruje danych. Jego wynik ma być wejściem do projektowania "
        "`migrate_memory_unification.py`, ale tylko po przejrzeniu kolejek P0/P1 i decyzji, "
        "które domeny wolno przenieść automatycznie."
    )
    lines.append("")
    lines.append("## Domeny pamięci")
    lines.append("")
    lines.append("| Domena | Liczba |")
    lines.append("|---|---:|")
    for item in summary["by_memory_domain"]:
        lines.append(f"| `{item['memory_domain']}` | {item['count']} |")
    lines.append("")
    lines.append("## Warstwy docelowe")
    lines.append("")
    lines.append("| Warstwa docelowa | Liczba |")
    lines.append("|---|---:|")
    for item in summary["by_target_layer"]:
        lines.append(f"| `{item['target_layer']}` | {item['count']} |")
    lines.append("")
    lines.append("## Decyzje migracyjne")
    lines.append("")
    lines.append("| Decyzja | Liczba |")
    lines.append("|---|---:|")
    for item in summary["by_migration_decision"]:
        lines.append(f"| `{item['migration_decision']}` | {item['count']} |")
    lines.append("")
    lines.append("## Priorytety")
    lines.append("")
    lines.append("| Priorytet | Liczba |")
    lines.append("|---|---:|")
    for item in summary["by_pre_migration_priority"]:
        lines.append(f"| `{item['pre_migration_priority']}` | {item['count']} |")
    lines.append("")
    lines.append("## Najważniejsze kolejki")
    lines.append("")
    lines.append("| Plik | Liczba | Znaczenie |")
    lines.append("|---|---:|---|")

    queue_meanings = {
        "queue_can_import_active_journal_medium.csv": "aktywny dziennik → SQLite, kandydaci do wsadu po backupie",
        "queue_can_export_active_sqlite_journal_medium.csv": "aktywna SQLite → kanoniczny dziennik, kandydaci do wsadu po backupie",
        "queue_old_sqlite_journal_candidates_only.csv": "stare SQLite, tylko kandydaci dziennik/refleksje, ręczny przegląd",
        "queue_old_sqlite_runtime_memory_candidates_only.csv": "stare SQLite, pamięć runtime, ręczny przegląd",
        "queue_runtime_memory_candidates.csv": "episodic/semantic/procedural — nie dziennik bezpośrednio",
        "queue_archive_technical_audit_only.csv": "audyt techniczny — archiwum, nie dziennik",
        "queue_legacy_source_index_only.csv": "legacy messages/conversations — indeks źródłowy, nie dziennik",
        "queue_do_not_import_directly.csv": "pozycje zablokowane przed bezpośrednim importem",
        "queue_manual_conflicts.csv": "konflikty do ręcznej decyzji",
        "queue_hold_unknown.csv": "nierozpoznana domena",
        "queue_p0_block_migration_until_review.csv": "blokuje migrację automatyczną",
        "queue_p1_manual_review.csv": "ręczny przegląd",
        "queue_p2_structured_batch_review.csv": "przegląd wsadowy",
        "queue_p3_batch_after_backup_candidate.csv": "najłatwiejsi kandydaci po backupie",
    }

    for name, count in summary["queue_counts"].items():
        lines.append(f"| `{name}` | {count} | {queue_meanings.get(name, '')} |")

    lines.append("")
    lines.append("## Znormalizowane kontenery")
    lines.append("")
    lines.append("| Kontener | Liczba |")
    lines.append("|---|---:|")
    for item in summary["by_container_normalized"][:40]:
        lines.append(f"| `{item['container_normalized']}` | {item['count']} |")

    lines.append("")
    lines.append("## Dni z największą liczbą kandydatów")
    lines.append("")
    lines.append("| Dzień | Liczba |")
    lines.append("|---|---:|")
    for item in summary["top_timestamp_days"][:40]:
        day = item.get("timestamp_day") or "no_timestamp_day"
        lines.append(f"| `{day}` | {item['count']} |")

    lines.append("")
    lines.append("## Reguły docelowe dla migratora")
    lines.append("")
    lines.append("- `journal_memory` i `journal_reflection` mogą zasilać kanoniczny `memory/raw/dziennik.json`, ale po deduplikacji.")
    lines.append("- `runtime_memory` może zasilać aktywną bazę runtime, ale nie powinno być bezpośrednio przepisywane do dziennika.")
    lines.append("- `technical_audit`, `source_index`, `events`, `truth_audits`, `meta` i `source_files` idą do archiwum/audytu, nie do pamiętnika.")
    lines.append("- `legacy_source_index` zostaje jako indeks źródłowy albo osobna tabela legacy, nie jako wpis dziennika.")
    lines.append("- Wszystko z P0/P1 blokuje automatyczny import do czasu przeglądu.")
    lines.append("")
    lines.append("## Granica prawdy")
    lines.append("")
    lines.append(summary["truth_boundary"])
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def choose_default_input() -> Path:
    enriched = Path("reports/memory_candidate_review/migration_candidates_review_enriched.csv")
    raw = Path("reports/memory_unification_plan/migration_candidates.csv")

    if enriched.exists():
        return enriched
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only pre-migration classifier for Jaźń memory candidates."
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Input candidates CSV. Default: enriched review CSV if present, otherwise memory_unification_plan/migration_candidates.csv.",
    )
    parser.add_argument(
        "--out",
        default="reports/memory_pre_migration_queues",
        help="Output directory.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve() if args.input else choose_default_input().resolve()
    out_dir = Path(args.out).resolve()

    rows = read_csv(input_path)
    enriched = enrich_rows(rows)
    fields = output_fields(enriched)

    out_dir.mkdir(parents=True, exist_ok=True)

    write_csv(out_dir / "pre_migration_candidates_classified.csv", enriched, fields)
    queue_counts = write_queues(out_dir, enriched, fields)

    summary = build_summary(enriched, input_path, queue_counts)
    write_json(out_dir / "pre_migration_summary.json", summary)
    write_markdown(out_dir / "PRE_MIGRATION_QUEUES.md", summary)

    print("Pre-migration classification zakończona — READ ONLY.")
    print(f"Input: {input_path}")
    print(f"Output: {out_dir}")
    print(f"Candidates: {summary['total_candidates']}")
    print()
    print("Najważniejsze kolejki:")
    for name, count in queue_counts.items():
        print(f"  {name}: {count}")
    print()
    print("Raport:")
    print(out_dir / "PRE_MIGRATION_QUEUES.md")
    print()
    print("Nie wykonano migracji.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())