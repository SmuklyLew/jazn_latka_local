from __future__ import annotations

import importlib.util
from pathlib import Path

from latka_jazn.core.canon import (
    default_canon_registry_data,
    load_python_canon_registry,
)
from latka_jazn.core.canon.extraction import run_canon_extraction


def test_python_canon_registry_contains_logical_canon_layers() -> None:
    registry = default_canon_registry_data()
    assert registry["source_mode"] == "source_controlled_python_canon_first"
    for key in (
        "character_profile",
        "origin_story",
        "symbolic_world",
        "relation_canon",
        "memory_truth_boundary",
        "narrative_book_canon",
        "song_affect_canon",
    ):
        assert key in registry
        assert isinstance(registry[key], dict)
    assert "memory/raw" in registry["private_memory_sources"][0]


def test_canon_extraction_preview_writes_progress_and_candidates(tmp_path: Path) -> None:
    root = tmp_path
    raw = root / "memory" / "raw"
    raw.mkdir(parents=True)
    (raw / "data.txt").write_text(
        "Łatka jest subtelna i czuła. Zielona kulka jest symbolem ciszy. "
        "Krzysztof jest twórcą i partnerem dialogowym.\n",
        encoding="utf-8",
    )
    progress = root / "reports" / "canon_extraction" / "progress.jsonl"
    report = run_canon_extraction(root, mode="preview", progress_path=progress)

    assert report["candidates_total"] >= 1
    assert progress.exists()
    assert (root / "reports" / "canon_extraction" / "canon_candidates.jsonl").exists()
    assert not (root / "latka_jazn" / "core" / "canon" / "local_private_canon_extension.py").exists()


def test_canon_extraction_can_write_local_private_python_extension(tmp_path: Path) -> None:
    root = tmp_path
    raw = root / "memory" / "raw"
    raw.mkdir(parents=True)
    (raw / "LATKA_BOOTSTRAP_SYSTEM.txt").write_text(
        "Łatka to ja, forma żeńska. Pamiętam tylko gdy mam źródło; inaczej mówię nie wiem.\n",
        encoding="utf-8",
    )
    report = run_canon_extraction(root, mode="write-private-extension")
    extension = root / "latka_jazn" / "core" / "canon" / "local_private_canon_extension.py"
    assert extension.exists()
    assert "local_private_extension_py" in report["outputs"]

    spec = importlib.util.spec_from_file_location("local_private_canon_extension_test", extension)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.LATKA_LOCAL_PRIVATE_CANON_EXTENSION
    assert payload["schema_version"] == "latka_local_private_canon_extension/v1"
    assert payload["candidates_by_category"]


def test_loader_accepts_optional_local_private_extension(tmp_path: Path) -> None:
    root = tmp_path
    canon_dir = root / "latka_jazn" / "core" / "canon"
    canon_dir.mkdir(parents=True)
    extension = canon_dir / "local_private_canon_extension.py"
    extension.write_text(
        "LATKA_LOCAL_PRIVATE_CANON_EXTENSION = {"
        "'schema_version': 'latka_local_private_canon_extension/v1', "
        "'local_note': 'test local extension'}\n",
        encoding="utf-8",
    )
    registry = load_python_canon_registry(root=root)
    assert registry["source_status"]["local_private_extension_loaded"].endswith("local_private_canon_extension.py")
    assert registry["local_private_canon_extension"]["local_note"] == "test local extension"
