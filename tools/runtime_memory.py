#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from latka_jazn.memory.runtime_persistence import (
    RuntimeMemoryCandidate,
    RuntimeMemoryWriter,
    scan_runtime_duplicates,
)
from latka_jazn.memory.store import MemoryStore
from latka_jazn.config import JaznConfig

def _read_version(root: Path) -> str:
    path = root / "VERSION.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return "runtime-unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Runtimeowy zapis pamięci Łatki do dziennika i warstw JSONL.")
    parser.add_argument("--root", default=".", help="Katalog systemu Jaźni")
    parser.add_argument("--text", help="Treść do zapamiętania")
    parser.add_argument("--title", default="Runtime: ręczny zapis pamięci", help="Tytuł wpisu")
    parser.add_argument("--kind", default="runtime_wspomnienie", help="Typ wpisu dziennika")
    parser.add_argument("--source", default="manual_runtime_command", help="Źródło wpisu")
    parser.add_argument("--grounding", default="recognized", help="Etykieta grounding")
    parser.add_argument("--confidence", type=float, default=0.72, help="Pewność 0..1")
    parser.add_argument("--emotion", action="append", default=[], help="Emocja/afekt; można podać wielokrotnie")
    parser.add_argument("--force", action="store_true", help="Zapisz mimo niskiego progu ważności")
    parser.add_argument("--scan-duplicates", action="store_true", help="Tylko przeskanuj duplikaty")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if args.scan_duplicates:
        print(json.dumps(scan_runtime_duplicates(root), ensure_ascii=False, indent=2))
        return 0
    if not args.text:
        parser.error("--text jest wymagane, chyba że używasz --scan-duplicates")

    cfg = JaznConfig(root=root)
    store = MemoryStore(cfg.memory_db_path)
    try:
        writer = RuntimeMemoryWriter(root, version=cfg.version, store=store)
        result = writer.persist_candidate(
            RuntimeMemoryCandidate(
                kind=args.kind,
                title=args.title,
                content=args.text,
                source=args.source,
                grounding=args.grounding,
                confidence=args.confidence,
                emotional_tags=args.emotion,
                memory_tags=["manual_runtime", "cli"],
                importance=0.85,
                raw_excerpt=args.text[:800],
            ),
            force=args.force,
        )
        print(json.dumps({
            "accepted": result.accepted,
            "reason": result.reason,
            "fingerprint": result.candidate_fingerprint,
            "appended_count": result.appended_count,
            "records": [r.__dict__ for r in result.records],
        }, ensure_ascii=False, indent=2))
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
