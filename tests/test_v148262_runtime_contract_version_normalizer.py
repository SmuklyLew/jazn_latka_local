from __future__ import annotations

import json
from pathlib import Path

from latka_jazn.tools.active_extraction_cache import (
    active_cache_contract_version,
    active_marker_schema_version,
    build_active_runtime_status,
    visible_preview_contract_version,
)
from latka_jazn.tools.runtime_contract_version_normalizer import normalize_runtime_contract_versions

VERSION = "v14.8.2.6.4-route-freshness-no-birth-stale-route-hotfix"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_v148262_active_cache_contract_versions_follow_version_txt(tmp_path: Path) -> None:
    (tmp_path / "VERSION.txt").write_text(VERSION + "\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    _write_json(
        tmp_path / "MANIFEST_CURRENT.json",
        {"version": VERSION, "active_database": "memory/sqlite/conversation_archive_v1/conversation_archive_manifest.sqlite3"},
    )

    status = build_active_runtime_status(tmp_path)
    assert status["schema_version"] == active_marker_schema_version(VERSION)
    assert status["cache_contract_version"] == active_cache_contract_version(VERSION)
    assert visible_preview_contract_version(tmp_path) == "visible_runtime_preview_contract/v14.8.2.6.4"
    assert status["active_database"] == "memory/sqlite/conversation_archive_v1/conversation_archive_manifest.sqlite3"
    assert status["active_runtime_write_database"] == "memory/sqlite/runtime_write_v1/runtime_memory.sqlite3"


def test_v148262_normalizer_fixes_stale_runtime_marker_versions(tmp_path: Path) -> None:
    (tmp_path / "VERSION.txt").write_text(VERSION + "\n", encoding="utf-8")
    _write_json(tmp_path / "MANIFEST_CURRENT.json", {
        "schema_version": "manifest_current/v14.8.2.6.0",
        "version": "v14.8.2.6.1-non-memory-intent-memory-gating-hotfix",
        "runtime_version": "v14.8.2.6.1-non-memory-intent-memory-gating-hotfix",
        "package_version": "v14.8.2.6.1-non-memory-intent-memory-gating-hotfix",
        "active_database": "memory/sqlite/chat_context.sqlite3",
    })
    _write_json(tmp_path / "workspace_runtime" / "JAZN_ACTIVE_RUNTIME.json", {
        "schema_version": "jazn_active_runtime_marker/v14.8.2.6.0",
        "cache_contract_version": "active_extraction_cache_contract/v14.8.2.6.0",
        "version": "v14.8.2.6.1-non-memory-intent-memory-gating-hotfix",
        "runtime_version": "v14.8.2.6.1-non-memory-intent-memory-gating-hotfix",
        "manifest_current_sha256": "stale",
        "visible_runtime_preview_contract": {"schema_version": "visible_runtime_preview_contract/v14.8.2.6.0"},
    })
    _write_json(tmp_path / "ACTIVE_RUNTIME_CACHE_CONTRACT.json", {
        "schema_version": "jazn_active_runtime_marker/v14.8.2.6.0",
        "cache_contract_version": "active_extraction_cache_contract/v14.8.2.6.0",
        "runtime_preview_contract": "visible_runtime_preview_contract/v14.8.2.6.0",
        "version": "v14.8.2.6.1-non-memory-intent-memory-gating-hotfix",
    })
    _write_json(tmp_path / "BOOTSTRAP_JAZN_CURRENT.json", {
        "schema_version": "bootstrap_jazn_current/v14.8.2.6.0",
        "active_extraction_cache_contract": "active_extraction_cache_contract/v14.8.2.6.0",
        "visible_runtime_preview_contract": "visible_runtime_preview_contract/v14.8.2.6.0",
        "runtime_version": "v14.8.2.6.1-non-memory-intent-memory-gating-hotfix",
    })

    dry = normalize_runtime_contract_versions(tmp_path, apply=False)
    assert dry["applied"] is False
    assert any(item["changed"] for item in dry["results"])

    report = normalize_runtime_contract_versions(tmp_path, apply=True)
    assert report["applied"] is True
    assert report["active_marker_schema_version"] == "jazn_active_runtime_marker/v14.8.2.6.4"
    assert report["active_cache_contract_version"] == "active_extraction_cache_contract/v14.8.2.6.4"
    assert report["visible_runtime_preview_contract_version"] == "visible_runtime_preview_contract/v14.8.2.6.4"

    manifest = json.loads((tmp_path / "MANIFEST_CURRENT.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "manifest_current/v14.8.2.6.4"

    marker = json.loads((tmp_path / "workspace_runtime" / "JAZN_ACTIVE_RUNTIME.json").read_text(encoding="utf-8"))
    assert marker["schema_version"] == "jazn_active_runtime_marker/v14.8.2.6.4"
    assert marker["cache_contract_version"] == "active_extraction_cache_contract/v14.8.2.6.4"
    assert marker["visible_runtime_preview_contract"]["schema_version"] == "visible_runtime_preview_contract/v14.8.2.6.4"
    assert marker["version"] == VERSION
    assert marker["manifest_current_sha256"] == report["manifest_current_sha256"]


def test_v148262_no_known_runtime_contract_6_0_constants_left() -> None:
    root = Path(__file__).resolve().parents[1]
    checked = [
        root / "latka_jazn" / "tools" / "active_extraction_cache.py",
        root / "main.py",
        root / "latka_jazn" / "__init__.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in checked)
    assert "active_extraction_cache_contract/v14.8.2.6.0" not in combined
    assert "jazn_active_runtime_marker/v14.8.2.6.0" not in combined
    assert "visible_runtime_preview_contract/v14.8.2.6.0" not in combined
