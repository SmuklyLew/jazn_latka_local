from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.tools.dedup_manifest import build_dedup_report

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def test_v14539_version_and_active_sqlite_name() -> None:
    cfg = JaznConfig()
    assert cfg.version == VERSION
    assert cfg.memory_db_path.name == "latka_jazn_v14_8_2.sqlite3"


def test_v14539_dedup_manifest_exists_and_records_actions() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = root / "docs" / "update_history" / "manifests" / "MANIFEST_V14_5_39_CLEANUP_DEDUP.json"
    assert manifest.exists()
    text = manifest.read_text(encoding="utf-8")
    assert "cleanup/dedup" in text
    assert "sha256" in text
    assert "canonical_path" in text


def test_v14539_no_exact_duplicate_noncode_content_left() -> None:
    root = Path(__file__).resolve().parents[1]
    report = build_dedup_report(root)
    assert report.duplicate_group_count == 0
    assert report.duplicate_file_count == 0


def test_v14539_file_hash_index_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    index = root / "reports" / "FILE_HASH_INDEX_V14_5_39.json"
    assert index.exists()
    assert "latka_jazn/tools/dedup_manifest.py" in index.read_text(encoding="utf-8")
