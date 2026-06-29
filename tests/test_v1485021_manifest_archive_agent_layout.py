from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_single_active_manifest_and_runtime_state_layout() -> None:
    assert (ROOT / "MANIFEST_CURRENT.json").is_file()
    assert (ROOT / "RUNTIME_STATE.json").is_file()
    assert not (ROOT / "MANIFEST_RUNTIME_MUTABLE.json").exists()

    current = json.loads((ROOT / "MANIFEST_CURRENT.json").read_text(encoding="utf-8"))
    runtime_state = json.loads((ROOT / "RUNTIME_STATE.json").read_text(encoding="utf-8"))

    assert current["schema_version"].startswith("manifest_current/")
    assert current["runtime_state_file"] == "RUNTIME_STATE.json"
    assert "runtime_mutable_manifest" not in current
    assert runtime_state["schema_version"].startswith("runtime_state/")


def test_legacy_manifests_are_archived_with_index() -> None:
    index_path = ROOT / "docs/archive/manifest_history/INDEX.json"
    assert index_path.is_file()
    index = json.loads(index_path.read_text(encoding="utf-8"))

    assert index["active_manifest"] == "MANIFEST_CURRENT.json"
    assert index["runtime_state_file"] == "RUNTIME_STATE.json"
    entries = index["entries"]
    assert entries
    original_paths = {entry["original_path"] for entry in entries}
    archived_paths = {entry["archived_path"] for entry in entries}

    assert "MANIFEST_RUNTIME_MUTABLE.json" in original_paths
    assert "docs/update_history/manifests/MANIFEST_v14_3_0_REWRITE_FULL.json" in original_paths
    assert "docs/archive/manifest_history/root/MANIFEST_RUNTIME_MUTABLE_v14_8_5_017_legacy.json" in archived_paths
    assert all(path.startswith("docs/archive/manifest_history/") for path in archived_paths)


def test_agent_instruction_files_are_separated() -> None:
    for name in ["AGENTS.md", "AGENTS.chatgpt.md", "AGENTS.codex.md", "AGENTS.lmstudio.md"]:
        assert (ROOT / name).is_file(), name

    router = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "AGENTS.chatgpt.md" in router
    assert "AGENTS.codex.md" in router
    assert "AGENTS.lmstudio.md" in router
    assert "MANIFEST_CURRENT.json" in router
    assert "RUNTIME_STATE.json" in router


def test_active_tree_has_no_legacy_manifest_files_outside_archive() -> None:
    forbidden = []
    for path in ROOT.rglob("*manifest*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        # `memory/` is deliberately excluded from this active-manifest scan.
        # Files such as `memory/RAW_MEMORY_MANIFEST.json`,
        # `memory/raw/CHAT_HTML_IMPORT_MANIFEST.json` or
        # `memory/sqlite/.../conversation_archive_manifest.sqlite3` are memory
        # metadata / SQLite databases, not agent-facing control manifests.
        # Moving them during manifest cleanup would be a separate memory
        # migration and could break active cache, importers or SQLite paths.
        if rel.startswith((
            ".git/", ".pytest-tmp/", "workspace_runtime/",
            "docs/archive/manifest_history/", "patchs/", "reports/",
            "memory/", "tests_before_",
        )) or "/__pycache__/" in rel or rel.startswith("__pycache__/"):
            continue
        if rel in {
            "MANIFEST_CURRENT.json",
            "docs/update_history/changelogs/CHANGELOG_v14_8_5_021A_RELEASE_METADATA_MANIFEST_HYGIENE.md",
            "latka_jazn/resources/package_manifest_profiles.json",
            "latka_jazn/resources/update_manifest_schema.json",
            "latka_jazn/core/birth_manifest.py",
            "latka_jazn/db/shard_manifest.py",
            "latka_jazn/tools/dedup_manifest.py",
            "tools/refresh_current_manifest.py",
            "tools/fix_v14825_manifest_marker.py",
        }:
            continue
        if rel.startswith("tests/"):
            continue
        forbidden.append(rel)
    assert forbidden == []
