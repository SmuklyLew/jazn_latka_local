#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from latka_jazn.config import JaznConfig
from latka_jazn.memory.store import MemoryStore
from latka_jazn.memory.importer import MemoryImporter
from latka_jazn.memory.runtime_persistence import scan_runtime_duplicates


def main() -> int:
    parser = argparse.ArgumentParser(description="Naprawa i synchronizacja pamięci Jaźni: pliki JSON/JSONL ↔ SQLite + chat.html.")
    parser.add_argument("--root", default=str(ROOT), help="Katalog systemu Jaźni")
    parser.add_argument("--import-chat-html", action="store_true", help="Zaindeksuj memory/raw/chat.html do SQLite")
    parser.add_argument("--force-chat-html", action="store_true", help="Wyczyść i zaindeksuj chat.html ponownie")
    parser.add_argument("--limit-conversations", type=int, default=None, help="Limit rozmów do testowego importu chat.html")
    parser.add_argument("--no-export", action="store_true", help="Nie eksportuj SQLite do memory/exported_from_sqlite")
    parser.add_argument("--scan-duplicates", action="store_true", help="Pokaż raport duplikatów fingerprint/dedupe_key")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    cfg = JaznConfig(root=root, network_time_first=False)
    store = MemoryStore(cfg.memory_db_path)
    try:
        importer = MemoryImporter(store, root)
        result = {
            "version": cfg.version,
            "root": str(root),
            "register_packaged_sources": importer.register_packaged_sources(),
            "sync_memory_files": importer.synchronize_memory_files(export=not args.no_export),
            "stats_after_file_sync": store.stats(),
        }
        if args.import_chat_html:
            result["chat_html_import"] = importer.import_raw_chat_html(
                force=args.force_chat_html,
                limit_conversations=args.limit_conversations,
            )
            result["stats_after_chat_import"] = store.stats()
        if args.scan_duplicates:
            result["duplicates"] = scan_runtime_duplicates(root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
