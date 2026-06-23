from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_refresh_manifest_keeps_runtime_memory_out_of_static_manifest(tmp_path: Path) -> None:
    root = tmp_path / "jazn_root"
    root.mkdir()
    (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "VERSION.txt").write_text("v14.8.3.4.092\n", encoding="utf-8")
    (root / "latka_jazn" / "core").mkdir(parents=True)
    (root / "latka_jazn" / "core" / "engine.py").write_text("ENGINE = True\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "README.md").write_text("# docs\n", encoding="utf-8")

    # Runtime/private memory that must not be treated as static package content.
    (root / "workspace_runtime" / "runtime_sessions").mkdir(parents=True)
    (root / "workspace_runtime" / "runtime_state.json").write_text("{}\n", encoding="utf-8")
    (root / "workspace_runtime" / "runtime_sessions" / "smoke.json").write_text("{}\n", encoding="utf-8")
    (root / "memory" / "raw").mkdir(parents=True)
    (root / "memory" / "raw" / "dziennik.json").write_text("{}\n", encoding="utf-8")
    (root / "memory" / "processed_chats").mkdir(parents=True)
    (root / "memory" / "processed_chats" / "chat_context_full_graph.jsonl").write_text("{}\n", encoding="utf-8")
    (root / "memory" / "sqlite" / "conversation_archive_v1").mkdir(parents=True)
    (root / "memory" / "sqlite" / "conversation_archive_v1" / "conversation_archive_manifest.sqlite3").write_bytes(b"not really sqlite")
    (root / ".pytest-tmp" / "test_case").mkdir(parents=True)
    (root / ".pytest-tmp" / "test_case" / "scratch.sqlite3").write_bytes(b"tmp")

    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "JAZN_PROJECT_ROOT": str(root)}
    result = subprocess.run(
        [sys.executable, str(repo_root / "tools" / "refresh_current_manifest.py")],
        cwd=repo_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout

    manifest = json.loads((root / "MANIFEST_CURRENT.json").read_text(encoding="utf-8"))
    runtime_manifest = json.loads((root / "MANIFEST_RUNTIME_MUTABLE.json").read_text(encoding="utf-8"))

    static_paths = {item["path"] for item in manifest["files"]}
    runtime_paths = {item["path"] for item in runtime_manifest["files"]}

    assert "latka_jazn/core/engine.py" in static_paths
    assert "docs/README.md" in static_paths
    assert not any(path.startswith("workspace_runtime/") for path in static_paths)
    assert not any(path.startswith("memory/raw/") for path in static_paths)
    assert not any(path.startswith("memory/processed_chats/") for path in static_paths)
    assert not any(path.startswith("memory/sqlite/") and path.endswith(".sqlite3") for path in static_paths)
    assert not any(path.startswith(".pytest-tmp/") for path in static_paths)

    assert "workspace_runtime/runtime_state.json" in runtime_paths
    assert "workspace_runtime/runtime_sessions/smoke.json" in runtime_paths
    assert "memory/raw/dziennik.json" in runtime_paths
    assert "memory/processed_chats/chat_context_full_graph.jsonl" in runtime_paths
    assert "memory/sqlite/conversation_archive_v1/conversation_archive_manifest.sqlite3" in runtime_paths
    assert not any(path.startswith(".pytest-tmp/") for path in runtime_paths)
    assert manifest["mutable_runtime_file_count"] == 0
    assert manifest["runtime_mutable_file_count"] == len(runtime_paths)
