from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote


TEXT_HINTS = (
    "text", "body", "content", "message", "rendered", "reply", "response",
    "scene", "note", "notes", "title", "summary", "reflection", "treść",
    "tresc", "opis", "wpis", "payload", "raw", "excerpt",
)

TIME_HINTS = (
    "created", "created_at", "created_at_utc", "created_at_local",
    "timestamp", "time", "date", "data", "local_time", "updated",
)

JOURNAL_HINTS = (
    "journal", "dziennik", "reflection", "reflections", "event", "events",
    "episodic", "memory", "memories", "legacy_messages",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


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


def short(value: Any, limit: int = 280) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:limit]


def safe_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except Exception:
        return str(path)


def sqlite_readonly_uri(path: Path) -> str:
    # Windows-safe URI path.
    return "file:" + quote(str(path.resolve()).replace("\\", "/"), safe="/:") + "?mode=ro"


def is_probably_text_column(name: str) -> bool:
    low = name.lower()
    return any(h in low for h in TEXT_HINTS)


def is_probably_time_column(name: str) -> bool:
    low = name.lower()
    return any(h in low for h in TIME_HINTS)


def is_probably_memory_table(name: str) -> bool:
    low = name.lower()
    return any(h in low for h in JOURNAL_HINTS)


@dataclass
class ContentFingerprint:
    source_kind: str
    source_file: str
    container: str
    row_id: str
    timestamp: str | None
    title: str | None
    text_preview: str
    normalized_sha256: str
    raw_sha256: str
    raw_length: int


def make_fingerprint(
    *,
    source_kind: str,
    source_file: str,
    container: str,
    row_id: str,
    timestamp: str | None,
    title: str | None,
    text: Any,
) -> ContentFingerprint | None:
    raw = "" if text is None else str(text)
    norm = normalize_text(raw)
    if not norm:
        return None
    return ContentFingerprint(
        source_kind=source_kind,
        source_file=source_file,
        container=container,
        row_id=row_id,
        timestamp=timestamp,
        title=short(title, 180) if title else None,
        text_preview=short(raw, 400),
        normalized_sha256=sha256_text(norm),
        raw_sha256=sha256_text(raw),
        raw_length=len(raw),
    )


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


def list_catalog(root: Path, sqlite_files: list[Path], journal_files: list[Path]) -> dict[str, Any]:
    def item(path: Path) -> dict[str, Any]:
        stat = path.stat()
        return {
            "path": safe_rel(path, root),
            "absolute_path": str(path.resolve()),
            "length": stat.st_size,
            "last_write_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "sha256": file_sha256(path),
        }

    return {
        "created_at_utc": now_utc(),
        "root": str(root.resolve()),
        "sqlite_files_count": len(sqlite_files),
        "journal_files_count": len(journal_files),
        "sqlite_files": [item(p) for p in sqlite_files],
        "journal_files": [item(p) for p in journal_files],
    }


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def read_sqlite_database(root: Path, db: Path, max_sample_rows: int = 5) -> tuple[dict[str, Any], list[ContentFingerprint]]:
    rel = safe_rel(db, root)
    fingerprints: list[ContentFingerprint] = []
    summary: dict[str, Any] = {
        "path": rel,
        "absolute_path": str(db.resolve()),
        "size_bytes": db.stat().st_size,
        "sha256": file_sha256(db),
        "opened_readonly": False,
        "integrity_check": None,
        "tables": [],
        "errors": [],
    }

    try:
        with closing(sqlite3.connect(sqlite_readonly_uri(db), uri=True, timeout=2.0)) as con:
            con.row_factory = sqlite3.Row
            summary["opened_readonly"] = True

            try:
                summary["integrity_check"] = con.execute("PRAGMA integrity_check").fetchone()[0]
            except Exception as exc:
                summary["errors"].append(f"integrity_check: {exc}")

            tables = con.execute(
                "SELECT name, type FROM sqlite_master "
                "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            ).fetchall()

            for t in tables:
                table_name = str(t["name"])
                table_info: dict[str, Any] = {
                    "name": table_name,
                    "type": str(t["type"]),
                    "probably_memory_table": is_probably_memory_table(table_name),
                    "columns": [],
                    "row_count": None,
                    "sample_rows": [],
                    "content_fingerprint_count": 0,
                    "errors": [],
                }

                try:
                    cols = con.execute(f"PRAGMA table_info({quote_ident(table_name)})").fetchall()
                    col_names = [str(c["name"]) for c in cols]
                    table_info["columns"] = [
                        {
                            "cid": c["cid"],
                            "name": c["name"],
                            "type": c["type"],
                            "notnull": c["notnull"],
                            "default": c["dflt_value"],
                            "pk": c["pk"],
                            "text_candidate": is_probably_text_column(str(c["name"])),
                            "time_candidate": is_probably_time_column(str(c["name"])),
                        }
                        for c in cols
                    ]
                except Exception as exc:
                    table_info["errors"].append(f"table_info: {exc}")
                    summary["tables"].append(table_info)
                    continue

                try:
                    table_info["row_count"] = con.execute(f"SELECT COUNT(*) FROM {quote_ident(table_name)}").fetchone()[0]
                except Exception as exc:
                    table_info["errors"].append(f"count: {exc}")

                text_cols = [c for c in col_names if is_probably_text_column(c)]
                time_cols = [c for c in col_names if is_probably_time_column(c)]
                title_cols = [c for c in col_names if c.lower() in {"title", "tytuł", "tytul", "kind", "type", "event_type"}]

                # Próbki do raportu.
                try:
                    rows = con.execute(f"SELECT rowid, * FROM {quote_ident(table_name)} LIMIT ?", (max_sample_rows,)).fetchall()
                    for row in rows:
                        table_info["sample_rows"].append({
                            k: short(row[k], 180)
                            for k in row.keys()
                            if k != "rowid"
                        })
                except Exception as exc:
                    table_info["errors"].append(f"samples: {exc}")

                # Pełny skan odcisków: streaming po całej tabeli, bez zapisu pełnych treści.
                if text_cols:
                    try:
                        select_cols = ["rowid"] + col_names
                        query = "SELECT " + ", ".join(quote_ident(c) if c != "rowid" else "rowid" for c in select_cols) + f" FROM {quote_ident(table_name)}"
                        for row in con.execute(query):
                            timestamp = None
                            title = None
                            for c in time_cols:
                                if row[c]:
                                    timestamp = str(row[c])
                                    break
                            for c in title_cols:
                                if row[c]:
                                    title = str(row[c])
                                    break

                            parts = []
                            for c in text_cols:
                                val = row[c]
                                if val is not None:
                                    parts.append(str(val))
                            combined = "\n".join(parts)

                            fp = make_fingerprint(
                                source_kind="sqlite",
                                source_file=rel,
                                container=table_name,
                                row_id=str(row["rowid"]),
                                timestamp=timestamp,
                                title=title,
                                text=combined,
                            )
                            if fp:
                                fingerprints.append(fp)
                                table_info["content_fingerprint_count"] += 1
                    except Exception as exc:
                        table_info["errors"].append(f"fingerprint_scan: {exc}")

                summary["tables"].append(table_info)

    except Exception as exc:
        summary["errors"].append(f"open_readonly: {exc}")

    return summary, fingerprints


def iter_json_entries(data: Any, path_hint: str = "$"):
    if isinstance(data, list):
        for i, item in enumerate(data):
            yield from iter_json_entries(item, f"{path_hint}[{i}]")
    elif isinstance(data, dict):
        # Najpierw traktujemy cały obiekt jako potencjalny wpis.
        yield path_hint, data

        # Potem szukamy list wpisów głębiej.
        for key, value in data.items():
            if isinstance(value, list):
                for i, item in enumerate(value):
                    yield from iter_json_entries(item, f"{path_hint}.{key}[{i}]")
            elif isinstance(value, dict):
                # Ograniczamy rekurencję: nie chcemy milionów fragmentów,
                # ale chcemy złapać np. {"entries":[...]}.
                if any(k.lower() in {"entries", "wpisy", "journal", "dziennik", "items"} for k in value.keys()):
                    yield from iter_json_entries(value, f"{path_hint}.{key}")


def extract_text_from_json_entry(entry: dict[str, Any]) -> tuple[str | None, str | None, str]:
    timestamp = None
    title = None
    text_parts: list[str] = []

    for key, value in entry.items():
        low = str(key).lower()
        if timestamp is None and is_probably_time_column(low) and not isinstance(value, (dict, list)):
            timestamp = str(value)
        if title is None and low in {"title", "tytuł", "tytul", "kind", "type", "typ", "kategoria"}:
            title = str(value)
        if is_probably_text_column(low) or low in {"treść", "tresc", "content", "text", "body", "scene", "opis"}:
            if isinstance(value, (dict, list)):
                text_parts.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
            else:
                text_parts.append(str(value))

    if not text_parts:
        # Fallback: cały obiekt jako tekst do odcisku, ale tylko gdy wygląda jak wpis.
        keys = " ".join(str(k).lower() for k in entry.keys())
        if any(h in keys for h in JOURNAL_HINTS + TEXT_HINTS + TIME_HINTS):
            text_parts.append(json.dumps(entry, ensure_ascii=False, sort_keys=True))

    return timestamp, title, "\n".join(text_parts)


def read_json_file(root: Path, path: Path) -> tuple[dict[str, Any], list[ContentFingerprint]]:
    rel = safe_rel(path, root)
    fingerprints: list[ContentFingerprint] = []
    summary: dict[str, Any] = {
        "path": rel,
        "absolute_path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "sha256": file_sha256(path),
        "json_mode": None,
        "top_type": None,
        "entry_candidates": 0,
        "content_fingerprint_count": 0,
        "top_keys": [],
        "errors": [],
    }

    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception as exc:
        summary["errors"].append(f"read_text: {exc}")
        return summary, fingerprints

    # JSONL fallback.
    if path.suffix.lower().endswith("jsonl") or "\n{" in text[:2000]:
        ok_lines = 0
        bad_lines = 0
        summary["json_mode"] = "jsonl_or_line_scan"
        for idx, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                ok_lines += 1
            except Exception:
                bad_lines += 1
                continue
            if isinstance(obj, dict):
                ts, title, body = extract_text_from_json_entry(obj)
                fp = make_fingerprint(
                    source_kind="json",
                    source_file=rel,
                    container="jsonl",
                    row_id=str(idx),
                    timestamp=ts,
                    title=title,
                    text=body,
                )
                summary["entry_candidates"] += 1
                if fp:
                    fingerprints.append(fp)
                    summary["content_fingerprint_count"] += 1
        summary["jsonl_ok_lines"] = ok_lines
        summary["jsonl_bad_lines"] = bad_lines
        return summary, fingerprints

    try:
        data = json.loads(text)
        summary["json_mode"] = "json"
        summary["top_type"] = type(data).__name__
        if isinstance(data, dict):
            summary["top_keys"] = list(data.keys())[:50]
        elif isinstance(data, list):
            summary["top_length"] = len(data)
    except Exception as exc:
        summary["errors"].append(f"json_decode: {exc}")
        return summary, fingerprints

    for idx, (path_hint, entry) in enumerate(iter_json_entries(data), start=1):
        if not isinstance(entry, dict):
            continue
        ts, title, body = extract_text_from_json_entry(entry)
        summary["entry_candidates"] += 1
        fp = make_fingerprint(
            source_kind="json",
            source_file=rel,
            container=path_hint,
            row_id=str(idx),
            timestamp=ts,
            title=title,
            text=body,
        )
        if fp:
            fingerprints.append(fp)
            summary["content_fingerprint_count"] += 1

    return summary, fingerprints


def build_overlap_report(fps: list[ContentFingerprint]) -> dict[str, Any]:
    by_norm: dict[str, list[ContentFingerprint]] = {}
    for fp in fps:
        by_norm.setdefault(fp.normalized_sha256, []).append(fp)

    duplicate_groups = []
    sqlite_only = []
    json_only = []

    for sha, group in by_norm.items():
        kinds = {g.source_kind for g in group}
        item = {
            "normalized_sha256": sha,
            "count": len(group),
            "sources": [asdict(g) for g in group],
        }
        if len(group) > 1:
            duplicate_groups.append(item)
        elif "sqlite" in kinds:
            sqlite_only.append(asdict(group[0]))
        elif "json" in kinds:
            json_only.append(asdict(group[0]))

    cross_source_duplicates = [
        g for g in duplicate_groups
        if {s["source_kind"] for s in g["sources"]} == {"sqlite", "json"}
        or ("sqlite" in {s["source_kind"] for s in g["sources"]} and "json" in {s["source_kind"] for s in g["sources"]})
    ]

    return {
        "created_at_utc": now_utc(),
        "fingerprints_total": len(fps),
        "unique_normalized_texts": len(by_norm),
        "duplicate_groups_total": len(duplicate_groups),
        "cross_source_duplicate_groups": len(cross_source_duplicates),
        "sqlite_only_count": len(sqlite_only),
        "json_only_count": len(json_only),
        "duplicate_groups": duplicate_groups[:500],
        "cross_source_duplicates": cross_source_duplicates[:500],
        "sqlite_only_samples": sqlite_only[:500],
        "json_only_samples": json_only[:500],
        "truth_boundary": (
            "Ten raport porównuje odciski znormalizowanej treści. "
            "To wykrywa duplikaty i prawdopodobne pokrycie SQLite/JSON, "
            "ale nie jest jeszcze migracją ani decyzją o usuwaniu plików."
        ),
    }


def write_markdown_report(
    out_path: Path,
    catalog: dict[str, Any],
    sqlite_summaries: list[dict[str, Any]],
    json_summaries: list[dict[str, Any]],
    overlap: dict[str, Any],
) -> None:
    lines: list[str] = []
    lines.append("# Audyt źródeł pamięci Jaźni: SQLite + dziennik.json")
    lines.append("")
    lines.append(f"- Utworzono UTC: `{catalog['created_at_utc']}`")
    lines.append(f"- Root: `{catalog['root']}`")
    lines.append(f"- Bazy SQLite: `{catalog['sqlite_files_count']}`")
    lines.append(f"- Pliki dziennika: `{catalog['journal_files_count']}`")
    lines.append(f"- Odciski treści łącznie: `{overlap['fingerprints_total']}`")
    lines.append(f"- Duplikaty między SQLite i JSON: `{overlap['cross_source_duplicate_groups']}`")
    lines.append(f"- Tylko SQLite: `{overlap['sqlite_only_count']}`")
    lines.append(f"- Tylko JSON: `{overlap['json_only_count']}`")
    lines.append("")
    lines.append("## Wniosek techniczny")
    lines.append("")
    lines.append(
        "Ten raport jest etapem przed migracją. Nie usuwa plików, nie scala wpisów i nie zmienia manifestu. "
        "Pozwala zdecydować, czy `workspace_runtime/latka_jazn_active.sqlite3` ma zostać jedyną aktywną bazą, "
        "a `memory/raw/dziennik.json` jedynym aktywnym dziennikiem."
    )
    lines.append("")
    lines.append("## Bazy SQLite")
    lines.append("")
    for s in sqlite_summaries:
        lines.append(f"### `{s['path']}`")
        lines.append(f"- Rozmiar: `{s['size_bytes']}`")
        lines.append(f"- SHA256: `{s['sha256']}`")
        lines.append(f"- Otwarta read-only: `{s['opened_readonly']}`")
        lines.append(f"- integrity_check: `{s.get('integrity_check')}`")
        if s["errors"]:
            lines.append(f"- Błędy: `{s['errors']}`")
        lines.append("")
        lines.append("| Tabela | Wiersze | Kolumny | Memory-like | Odciski treści |")
        lines.append("|---|---:|---:|---:|---:|")
        for t in s["tables"]:
            lines.append(
                f"| `{t['name']}` | {t.get('row_count')} | {len(t.get('columns') or [])} | "
                f"{t.get('probably_memory_table')} | {t.get('content_fingerprint_count')} |"
            )
        lines.append("")
    lines.append("## Pliki dziennika JSON")
    lines.append("")
    for s in json_summaries:
        lines.append(f"### `{s['path']}`")
        lines.append(f"- Rozmiar: `{s['size_bytes']}`")
        lines.append(f"- SHA256: `{s['sha256']}`")
        lines.append(f"- Tryb: `{s.get('json_mode')}`")
        lines.append(f"- Typ top-level: `{s.get('top_type')}`")
        lines.append(f"- Kandydaci wpisów: `{s.get('entry_candidates')}`")
        lines.append(f"- Odciski treści: `{s.get('content_fingerprint_count')}`")
        if s["errors"]:
            lines.append(f"- Błędy: `{s['errors']}`")
        lines.append("")
    lines.append("## Porównanie SQLite ↔ JSON")
    lines.append("")
    lines.append(f"- Grupy duplikatów łącznie: `{overlap['duplicate_groups_total']}`")
    lines.append(f"- Grupy duplikatów między SQLite i JSON: `{overlap['cross_source_duplicate_groups']}`")
    lines.append(f"- Wpisy widoczne tylko w SQLite, próbki: `{len(overlap['sqlite_only_samples'])}`")
    lines.append(f"- Wpisy widoczne tylko w JSON, próbki: `{len(overlap['json_only_samples'])}`")
    lines.append("")
    lines.append("## Rekomendowany następny krok")
    lines.append("")
    lines.append(
        "Jeżeli raport pokaże, że SQLite zawiera komplet albo prawie komplet dziennika, "
        "następny patch powinien zrobić `workspace_runtime/latka_jazn_active.sqlite3` jako aktywną bazę, "
        "zarchiwizować stare `latka_jazn_v*.sqlite3`, wyeksportować jeden `memory/raw/dziennik.json` "
        "i zaktualizować `active_cache_status`, manifest oraz testy regresji."
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, fps: list[ContentFingerprint]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(fps[0]).keys()) if fps else [
            "source_kind", "source_file", "container", "row_id", "timestamp",
            "title", "text_preview", "normalized_sha256", "raw_sha256", "raw_length",
        ])
        writer.writeheader()
        for fp in fps:
            writer.writerow(asdict(fp))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only audit of Jaźń SQLite databases and dziennik.json* files before memory unification."
    )
    parser.add_argument("--root", default=".", help="Root folder to scan, e.g. D:\\.AI\\latka_jazn_v14_8_2_4_codex")
    parser.add_argument("--out", default="reports/memory_unification_audit", help="Output directory for reports")
    parser.add_argument("--max-sample-rows", type=int, default=5, help="Sample rows per SQLite table in report")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = (root / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    sqlite_files, journal_files = find_files(root)

    catalog = list_catalog(root, sqlite_files, journal_files)

    sqlite_summaries: list[dict[str, Any]] = []
    json_summaries: list[dict[str, Any]] = []
    all_fps: list[ContentFingerprint] = []

    for db in sqlite_files:
        summary, fps = read_sqlite_database(root, db, max_sample_rows=args.max_sample_rows)
        sqlite_summaries.append(summary)
        all_fps.extend(fps)

    for jf in journal_files:
        summary, fps = read_json_file(root, jf)
        json_summaries.append(summary)
        all_fps.extend(fps)

    overlap = build_overlap_report(all_fps)

    (out_dir / "memory_sources_catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "sqlite_summary.json").write_text(
        json.dumps(sqlite_summaries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "journal_json_summary.json").write_text(
        json.dumps(json_summaries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "sqlite_json_overlap_report.json").write_text(
        json.dumps(overlap, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv(out_dir / "content_fingerprints.csv", all_fps)
    write_markdown_report(
        out_dir / "MEMORY_UNIFICATION_AUDIT.md",
        catalog,
        sqlite_summaries,
        json_summaries,
        overlap,
    )

    print("Audyt zakończony.")
    print(f"Root: {root}")
    print(f"SQLite files: {len(sqlite_files)}")
    print(f"Dziennik files: {len(journal_files)}")
    print(f"Fingerprints: {len(all_fps)}")
    print(f"Cross-source duplicate groups: {overlap['cross_source_duplicate_groups']}")
    print(f"SQLite-only samples: {overlap['sqlite_only_count']}")
    print(f"JSON-only samples: {overlap['json_only_count']}")
    print(f"Reports: {out_dir}")
    print()
    print("Najważniejszy raport:")
    print(out_dir / "MEMORY_UNIFICATION_AUDIT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
