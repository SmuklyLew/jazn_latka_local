from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.tools.active_extraction_cache import build_active_runtime_status, write_active_runtime_marker

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def test_active_extraction_cache_marker_reuses_matching_folder(tmp_path: Path) -> None:
    root = tmp_path / "jazn"
    root.mkdir()
    (root / "VERSION.txt").write_text(VERSION + "\n", encoding="utf-8")
    (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "MANIFEST_CURRENT.json").write_text('{"version":"' + VERSION + '"}\n', encoding="utf-8")
    marker = tmp_path / "JAZN_ACTIVE_RUNTIME.json"

    written = write_active_runtime_marker(root, marker_output=marker)
    status = build_active_runtime_status(root, marker_output=marker)

    assert written["schema_version"] == "jazn_active_runtime_marker/v14.8.1"
    assert written["version"] == VERSION
    assert status["should_reuse_existing_extraction"] is True
    assert "marker_manifest_sha256_matches" in status["cache_hit_reasons"]
    assert written["visible_runtime_preview_contract"]["schema_version"] == "visible_runtime_preview_contract/v14.8.1"


def test_active_extraction_cache_detects_manifest_change(tmp_path: Path) -> None:
    root = tmp_path / "jazn"
    root.mkdir()
    (root / "VERSION.txt").write_text(VERSION + "\n", encoding="utf-8")
    (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
    manifest = root / "MANIFEST_CURRENT.json"
    manifest.write_text('{"version":"' + VERSION + '"}\n', encoding="utf-8")
    marker = tmp_path / "JAZN_ACTIVE_RUNTIME.json"
    write_active_runtime_marker(root, marker_output=marker)

    manifest.write_text('{"version":"' + VERSION + '","changed":true}\n', encoding="utf-8")
    status = build_active_runtime_status(root, marker_output=marker)

    assert status["should_reuse_existing_extraction"] is False
    assert "marker_manifest_sha256_differs_or_missing" in status["cache_miss_reasons"]


def test_runtime_preview_payload_contains_visible_preview_contract(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False)
    marker = tmp_path / "JAZN_ACTIVE_RUNTIME.json"
    active_status = write_active_runtime_marker(root, marker_output=marker)
    payload = {
        "schema_version": "runtime_preview/v14.6.10",
        "runtime_version": cfg.version,
        "visible_runtime_preview_contract": active_status["visible_runtime_preview_contract"],
        "active_extraction_cache_status": active_status,
    }
    assert payload["schema_version"] == "runtime_preview/v14.6.10"
    assert payload["runtime_version"] == VERSION
    assert payload["visible_runtime_preview_contract"]["schema_version"] == "visible_runtime_preview_contract/v14.8.1"
    assert payload["active_extraction_cache_status"]["schema_version"] == "jazn_active_runtime_marker/v14.8.1"


def test_active_cache_status_cli_can_write_marker(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    marker = tmp_path / "JAZN_ACTIVE_RUNTIME.json"
    result = subprocess.run(
        [sys.executable, "main.py", "--write-active-runtime-marker", "--marker-output", str(marker)],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    payload = json.loads(result.stdout)
    assert marker.exists()
    assert payload["version"] == JaznConfig(root=root, network_time_first=False).version
    assert payload["visible_runtime_preview_contract"]["schema_version"] == "visible_runtime_preview_contract/v14.8.1"
