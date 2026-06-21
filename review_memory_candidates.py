from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_VERSION = "review_memory_candidates/v1-readonly"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value)))
    except Exception:
        return default


def short(value: Any, limit: int = 260) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = " ".join(text.split())
    return text[:limit]


def safe_filename(value: str, limit: int = 90) -> str:
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

    # Kandydaci mogą mieć długie pola tekstowe.
    try:
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        csv.field_size_limit(2_147_483_647)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for idx, row in enumerate(reader, start=1):
            row["_row_number"] = str(idx)
            rows.append({k: "" if v is None else v for k, v in row.items()})
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if fieldnames is None:
        keys: list[str] = []
        seen = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        fieldnames = keys

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def group_counter(rows: list[dict[str, str]], *fields: str) -> Counter[tuple[str, ...]]:
    c: Counter[tuple[str, ...]] = Counter()
    for row in rows:
        c[tuple(row.get(f, "") or "" for f in fields)] += 1
    return c


def counter_to_rows(counter: Counter[tuple[str, ...]], fields: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key, count in counter.most_common():
        item = {field: key[idx] for idx, field in enumerate(fields)}
        item["count"] = count
        out.append(item)
    return out


def add_review_flags(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    enriched: list[dict[str, str]] = []

    for row in rows:
        r = dict(row)
        action = r.get("action", "")
        confidence = r.get("confidence", "")
        conflict_count = as_int(r.get("conflict_count"))
        duplicate_count = as_int(r.get("duplicate_count"))
        source_role = r.get("source_role", "")
        container = r.get("container", "")
        timestamp_day = r.get("timestamp_day", "")

        flags: list[str] = []
        risk = 0

        if conflict_count > 0 or "conflict" in confidence:
            flags.append("HAS_CONFLICT")
            risk += 50

        if action.startswith("REVIEW_OLD_SQLITE"):
            flags.append("OLD_SQLITE_REVIEW")
            risk += 30

        if source_role == "sqlite_snapshot":
            flags.append("SNAPSHOT_SOURCE")
            risk += 15

        if container in {"legacy_messages", "legacy_conversations"}:
            flags.append("LEGACY_RAW_IMPORT_RISK")
            risk += 20

        if duplicate_count > 0:
            flags.append("HAS_DUPLICATE_SOURCES")
            risk -= 5

        if not timestamp_day:
            flags.append("NO_TIMESTAMP_DAY")
            risk += 10

        if action.startswith("IMPORT_ACTIVE_JOURNAL"):
            flags.append("JOURNAL_TO_SQLITE")
            risk += 5

        if action.startswith("EXPORT_ACTIVE_SQLITE"):
            flags.append("SQLITE_TO_DZIENNIK")
            risk += 5

        if confidence == "medium" and conflict_count == 0 and not action.startswith("REVIEW_OLD_SQLITE"):
            flags.append("LIKELY_EASIER_REVIEW")
            risk -= 15

        risk = max(0, min(100, risk))

        if risk >= 70:
            priority = "P0_manual_conflict"
        elif risk >= 45:
            priority = "P1_manual_review"
        elif risk >= 20:
            priority = "P2_batch_review"
        else:
            priority = "P3_low_risk_batch"

        r["review_priority"] = priority
        r["risk_score"] = str(risk)
        r["review_flags"] = ";".join(flags)
        r["text_preview_short"] = short(r.get("text_preview", ""), 260)

        enriched.append(r)

    return enriched


def summarize(rows: list[dict[str, str]], candidates_path: Path) -> dict[str, Any]:
    total = len(rows)

    by_action = counter_to_rows(group_counter(rows, "action"), ["action"])
    by_confidence = counter_to_rows(group_counter(rows, "confidence"), ["confidence"])
    by_priority = counter_to_rows(group_counter(rows, "review_priority"), ["review_priority"])
    by_action_confidence = counter_to_rows(group_counter(rows, "action", "confidence"), ["action", "confidence"])
    by_action_priority = counter_to_rows(group_counter(rows, "action", "review_priority"), ["action", "review_priority"])
    by_container = counter_to_rows(group_counter(rows, "container"), ["container"])
    by_source_file = counter_to_rows(group_counter(rows, "source_file"), ["source_file"])
    by_timestamp_day = counter_to_rows(group_counter(rows, "timestamp_day"), ["timestamp_day"])
    by_source_role = counter_to_rows(group_counter(rows, "source_role"), ["source_role"])

    conflict_rows = [r for r in rows if as_int(r.get("conflict_count")) > 0 or "conflict" in r.get("confidence", "")]
    old_sqlite_rows = [r for r in rows if r.get("action") == "REVIEW_OLD_SQLITE_UNIQUE_CANDIDATE"]
    journal_import_rows = [r for r in rows if r.get("action") == "IMPORT_ACTIVE_JOURNAL_TO_ACTIVE_SQLITE_CANDIDATE"]
    sqlite_export_rows = [r for r in rows if r.get("action") == "EXPORT_ACTIVE_SQLITE_TO_CANONICAL_DZIENNIK_CANDIDATE"]

    unique_hashes = len({r.get("content_sha256", "") for r in rows if r.get("content_sha256")})
    unique_soft_days = len({r.get("timestamp_day", "") for r in rows if r.get("timestamp_day")})

    return {
        "schema_version": SCRIPT_VERSION,
        "created_at_utc": now_utc(),
        "input_csv": str(candidates_path),
        "total_candidates": total,
        "unique_candidate_content_hashes": unique_hashes,
        "unique_timestamp_days": unique_soft_days,
        "conflict_or_low_conflict_rows": len(conflict_rows),
        "old_sqlite_review_rows": len(old_sqlite_rows),
        "active_journal_to_sqlite_rows": len(journal_import_rows),
        "active_sqlite_to_journal_rows": len(sqlite_export_rows),
        "by_action": by_action,
        "by_confidence": by_confidence,
        "by_review_priority": by_priority,
        "by_action_confidence": by_action_confidence,
        "by_action_priority": by_action_priority,
        "top_containers": by_container[:50],
        "top_source_files": by_source_file[:50],
        "top_timestamp_days": by_timestamp_day[:80],
        "by_source_role": by_source_role,
        "truth_boundary": (
            "This report groups migration candidates only. It does not migrate, delete, deduplicate, "
            "or prove semantic equivalence. P0/P1 queues require manual or separately scripted review before migration."
        ),
    }


def select_fields() -> list[str]:
    return [
        "_row_number",
        "review_priority",
        "risk_score",
        "review_flags",
        "action",
        "confidence",
        "reason",
        "source_kind",
        "source_file",
        "source_role",
        "container",
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


def write_group_reports(out_dir: Path, rows: list[dict[str, str]]) -> None:
    fields = select_fields()

    queues = {
        "queue_p0_manual_conflict.csv": [r for r in rows if r.get("review_priority") == "P0_manual_conflict"],
        "queue_p1_manual_review.csv": [r for r in rows if r.get("review_priority") == "P1_manual_review"],
        "queue_p2_batch_review.csv": [r for r in rows if r.get("review_priority") == "P2_batch_review"],
        "queue_p3_low_risk_batch.csv": [r for r in rows if r.get("review_priority") == "P3_low_risk_batch"],
        "queue_import_active_journal_to_sqlite.csv": [r for r in rows if r.get("action") == "IMPORT_ACTIVE_JOURNAL_TO_ACTIVE_SQLITE_CANDIDATE"],
        "queue_export_active_sqlite_to_journal.csv": [r for r in rows if r.get("action") == "EXPORT_ACTIVE_SQLITE_TO_CANONICAL_DZIENNIK_CANDIDATE"],
        "queue_review_old_sqlite_unique.csv": [r for r in rows if r.get("action") == "REVIEW_OLD_SQLITE_UNIQUE_CANDIDATE"],
        "queue_conflicts_all.csv": [r for r in rows if as_int(r.get("conflict_count")) > 0 or "conflict" in r.get("confidence", "")],
        "queue_medium_no_conflict.csv": [r for r in rows if r.get("confidence") == "medium" and as_int(r.get("conflict_count")) == 0],
    }

    for name, subset in queues.items():
        write_csv(out_dir / name, subset, fields)

    # Osobne kolejki według kontenera.
    by_container: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_container[row.get("container", "") or "unknown"].append(row)

    container_dir = out_dir / "by_container"
    for container, subset in sorted(by_container.items(), key=lambda kv: len(kv[1]), reverse=True):
        write_csv(container_dir / f"{safe_filename(container)}.csv", subset, fields)

    # Osobne kolejki według źródła.
    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_source[row.get("source_file", "") or "unknown"].append(row)

    source_dir = out_dir / "by_source_file"
    for source, subset in sorted(by_source.items(), key=lambda kv: len(kv[1]), reverse=True):
        write_csv(source_dir / f"{safe_filename(source)}.csv", subset, fields)

    # Osobne kolejki według dnia.
    by_day: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_day[row.get("timestamp_day", "") or "no_timestamp_day"].append(row)

    day_dir = out_dir / "by_timestamp_day"
    for day, subset in sorted(by_day.items(), key=lambda kv: (kv[0] == "no_timestamp_day", kv[0])):
        write_csv(day_dir / f"{safe_filename(day)}.csv", subset, fields)


def write_markdown(out_path: Path, summary: dict[str, Any], rows: list[dict[str, str]]) -> None:
    lines: list[str] = []
    lines.append("# Review memory candidates — raport grupowania")
    lines.append("")
    lines.append(f"- Utworzono UTC: `{summary['created_at_utc']}`")
    lines.append(f"- Wejściowy CSV: `{summary['input_csv']}`")
    lines.append(f"- Kandydaci łącznie: `{summary['total_candidates']}`")
    lines.append(f"- Unikalne `content_sha256`: `{summary['unique_candidate_content_hashes']}`")
    lines.append(f"- Dni z kandydatami: `{summary['unique_timestamp_days']}`")
    lines.append(f"- Konflikty / low_conflict: `{summary['conflict_or_low_conflict_rows']}`")
    lines.append(f"- Stare SQLite do przeglądu: `{summary['old_sqlite_review_rows']}`")
    lines.append(f"- Import aktywnego dziennika do SQLite: `{summary['active_journal_to_sqlite_rows']}`")
    lines.append(f"- Eksport aktywnej SQLite do dziennika: `{summary['active_sqlite_to_journal_rows']}`")
    lines.append("")
    lines.append("## Kolejność pracy")
    lines.append("")
    lines.append("1. Najpierw `queue_p0_manual_conflict.csv` — konflikty i wpisy niskiej pewności.")
    lines.append("2. Potem `queue_review_old_sqlite_unique.csv` — stare bazy, ale tylko po grupowaniu po dniach/kontenerach.")
    lines.append("3. Potem `queue_import_active_journal_to_sqlite.csv` — aktywny dziennik → aktywna baza.")
    lines.append("4. Potem `queue_export_active_sqlite_to_journal.csv` — aktywna baza → kanoniczny `memory/raw/dziennik.json`.")
    lines.append("5. Na końcu `queue_medium_no_conflict.csv` — potencjalnie najłatwiejsze wpisy wsadowe.")
    lines.append("")
    lines.append("## Według akcji")
    lines.append("")
    lines.append("| Akcja | Liczba |")
    lines.append("|---|---:|")
    for item in summary["by_action"]:
        lines.append(f"| `{item['action']}` | {item['count']} |")
    lines.append("")
    lines.append("## Według pewności")
    lines.append("")
    lines.append("| Confidence | Liczba |")
    lines.append("|---|---:|")
    for item in summary["by_confidence"]:
        lines.append(f"| `{item['confidence']}` | {item['count']} |")
    lines.append("")
    lines.append("## Według priorytetu przeglądu")
    lines.append("")
    lines.append("| Priorytet | Liczba |")
    lines.append("|---|---:|")
    for item in summary["by_review_priority"]:
        lines.append(f"| `{item['review_priority']}` | {item['count']} |")
    lines.append("")
    lines.append("## Najczęstsze kontenery")
    lines.append("")
    lines.append("| Kontener | Liczba |")
    lines.append("|---|---:|")
    for item in summary["top_containers"][:30]:
        lines.append(f"| `{item['container']}` | {item['count']} |")
    lines.append("")
    lines.append("## Najczęstsze źródła")
    lines.append("")
    lines.append("| Źródło | Liczba |")
    lines.append("|---|---:|")
    for item in summary["top_source_files"][:30]:
        lines.append(f"| `{item['source_file']}` | {item['count']} |")
    lines.append("")
    lines.append("## Dni z największą liczbą kandydatów")
    lines.append("")
    lines.append("| Dzień | Liczba |")
    lines.append("|---|---:|")
    for item in summary["top_timestamp_days"][:40]:
        day = item.get("timestamp_day") or "no_timestamp_day"
        lines.append(f"| `{day}` | {item['count']} |")
    lines.append("")
    lines.append("## Pierwsze 40 rekordów P0/P1")
    lines.append("")
    lines.append("| Priorytet | Akcja | Źródło | Kontener | Data | Flagi | Podgląd |")
    lines.append("|---|---|---|---|---|---|---|")

    important = [
        r for r in rows
        if r.get("review_priority") in {"P0_manual_conflict", "P1_manual_review"}
    ]
    important.sort(key=lambda r: (-as_int(r.get("risk_score")), r.get("action", ""), r.get("timestamp_day", "")))

    for row in important[:40]:
        preview = short(row.get("text_preview_short") or row.get("text_preview"), 180).replace("|", "\\|")
        flags = row.get("review_flags", "").replace("|", "\\|")
        lines.append(
            f"| `{row.get('review_priority')}` | `{row.get('action')}` | `{row.get('source_file')}` | "
            f"`{row.get('container')}` | `{row.get('timestamp_day')}` | `{flags}` | {preview} |"
        )

    lines.append("")
    lines.append("## Granica prawdy")
    lines.append("")
    lines.append(summary["truth_boundary"])
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only grouping/review helper for memory unification migration candidates."
    )
    parser.add_argument(
        "--candidates",
        default="reports/memory_unification_plan/migration_candidates.csv",
        help="Path to migration_candidates.csv from plan_memory_unification.py.",
    )
    parser.add_argument(
        "--out",
        default="reports/memory_candidate_review",
        help="Output directory for grouped review reports.",
    )
    args = parser.parse_args()

    candidates_path = Path(args.candidates).resolve()
    out_dir = Path(args.out).resolve()

    rows_raw = read_csv(candidates_path)
    rows = add_review_flags(rows_raw)
    summary = summarize(rows, candidates_path)

    out_dir.mkdir(parents=True, exist_ok=True)

    write_json(out_dir / "review_summary.json", summary)
    write_csv(out_dir / "migration_candidates_review_enriched.csv", rows, select_fields())
    write_group_reports(out_dir, rows)
    write_markdown(out_dir / "REVIEW_MEMORY_CANDIDATES.md", summary, rows)

    print("Review candidates zakończone — READ ONLY.")
    print(f"Input: {candidates_path}")
    print(f"Output: {out_dir}")
    print(f"Total candidates: {summary['total_candidates']}")
    print(f"Conflict / low_conflict rows: {summary['conflict_or_low_conflict_rows']}")
    print(f"Old SQLite review rows: {summary['old_sqlite_review_rows']}")
    print(f"Active journal -> SQLite rows: {summary['active_journal_to_sqlite_rows']}")
    print(f"Active SQLite -> journal rows: {summary['active_sqlite_to_journal_rows']}")
    print()
    print("Main report:")
    print(out_dir / "REVIEW_MEMORY_CANDIDATES.md")
    print()
    print("Najważniejsze kolejki:")
    print(out_dir / "queue_p0_manual_conflict.csv")
    print(out_dir / "queue_review_old_sqlite_unique.csv")
    print(out_dir / "queue_import_active_journal_to_sqlite.csv")
    print(out_dir / "queue_export_active_sqlite_to_journal.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())