from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.tools.package_export import export_package


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def test_contextual_fallback_points_to_debug_files(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        reply = engine.handle_user_message("Hej", client_context={"client": "unit_test", "debug_direct": True})
    finally:
        engine.shutdown()

    assert "pusty fallback" in reply
    assert "latka_jazn/core/engine.py::_contextual_fallback" in reply
    assert "--cognitive-frame" in reply


def test_cognitive_frame_contains_fallback_diagnostics(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame("Napraw pusty fallback i powiedz gdzie szukać błędu.", client_context={"client": "unit_test"})
    finally:
        engine.shutdown()

    diag = packet["fallback_diagnostics"]
    assert diag["where_to_look"]
    assert any(item["function"] == "_contextual_fallback" for item in diag["where_to_look"])
    assert any("ConversationResponder" in item or "fallback" in item for item in packet["reply_guidance"])


def test_package_export_modes(tmp_path: Path) -> None:
    (tmp_path / "latka_jazn").mkdir()
    (tmp_path / "latka_jazn" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "memory" / "raw").mkdir(parents=True)
    (tmp_path / "memory" / "raw" / "dziennik.json").write_text("{}", encoding="utf-8")
    (tmp_path / "workspace_runtime").mkdir()
    (tmp_path / "workspace_runtime" / "test.sqlite3").write_bytes(b"sqlite")

    system = export_package(tmp_path, "system", tmp_path / "exports" / "system.zip")
    memory = export_package(tmp_path, "memory", tmp_path / "exports" / "memory.zip")
    full = export_package(tmp_path, "full", tmp_path / "exports" / "full.zip")

    assert system.includes_system and not system.includes_memory
    assert memory.includes_memory and not memory.includes_system
    assert full.includes_system and full.includes_memory
    assert system.file_count >= 2
    assert memory.file_count >= 2
    assert full.file_count >= 4


def test_main_export_system_cli_outputs_json(tmp_path: Path) -> None:
    (tmp_path / "memory" / "raw").mkdir(parents=True)
    (tmp_path / "memory" / "raw" / "dziennik.json").write_text("{}", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            str(project_root / "main.py"),
            "--root",
            str(tmp_path),
            "--export-system",
            "--output",
            str(tmp_path / "system.zip"),
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["mode"] == "system"
    assert Path(payload["output_zip"]).exists()
