from __future__ import annotations

import json
from pathlib import Path

from latka_jazn.memory.auto_memory_update import next_patch_version, run_auto_memory_update


def test_next_patch_version_keeps_semver_and_changes_suffix():
    assert next_patch_version("v14.5.2-memory-continuity-update") == "v14.5.3-memory-continuity-update"
    assert next_patch_version("14.5.9", suffix="auto") == "v14.5.10-auto"


def test_auto_memory_update_writes_journal_and_protocol(tmp_path: Path):
    root = tmp_path
    (root / "memory" / "raw").mkdir(parents=True)
    (root / "memory" / "layered").mkdir(parents=True)
    (root / "workspace_runtime").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "VERSION.txt").write_text("v14.5.2-memory-continuity-update\n", encoding="utf-8")
    (root / "README.md").write_text("# test\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "14.5.2"\ndescription = "old"\n', encoding="utf-8")
    (root / "memory" / "raw" / "dziennik.json").write_text(json.dumps({"meta": {}, "entries": []}, ensure_ascii=False), encoding="utf-8")
    for name in ["episodic.jsonl", "reflections.jsonl", "semantic.jsonl", "procedural.jsonl", "truth_audits.jsonl"]:
        (root / "memory" / "layered" / name).write_text("", encoding="utf-8")

    result = run_auto_memory_update(
        root=root,
        target_version="v14.5.3-test-auto",
        title="Test automatycznej aktualizacji",
        summary="Testowy zapis pamięciowy.",
        tests=["unit-test"],
        update_version_files_enabled=True,
    )

    assert result.target_version == "v14.5.3-test-auto"
    dz = json.loads((root / "memory" / "raw" / "dziennik.json").read_text(encoding="utf-8"))
    assert len(dz["entries"]) == 3
    assert (root / "memory" / "update_protocol.json").exists()
    assert (root / result.update_doc).exists()
    assert (root / result.manifest).exists()
    assert (root / "VERSION.txt").read_text(encoding="utf-8").strip() == "v14.5.3-test-auto"
    assert (root / "memory" / "layered" / "episodic.jsonl").read_text(encoding="utf-8").count("\n") == 1
