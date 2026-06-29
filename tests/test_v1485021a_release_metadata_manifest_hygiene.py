from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tomllib

from latka_jazn.version import PACKAGE_RELEASE_NAME, PACKAGE_VERSION, PACKAGE_VERSION_FULL


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_VERSION = "v14.8.5.021a"
RELEASE_NAME = "release-metadata-manifest-hygiene"
PROJECT_VERSION = "14.8.5.21a0"


def _checksum_entries(name: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
        digest, path = line.split("  ", 1)
        entries[path] = digest
    return entries


def test_release_version_metadata_is_consistent_and_bom_free() -> None:
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    version_py_bytes = (ROOT / "latka_jazn" / "version.py").read_bytes()

    assert not version_bytes.startswith(b"\xef\xbb\xbf")
    assert not version_py_bytes.startswith(b"\xef\xbb\xbf")
    assert version_bytes.decode("utf-8").strip() == RUNTIME_VERSION
    assert PACKAGE_VERSION == RUNTIME_VERSION
    assert PACKAGE_RELEASE_NAME == RELEASE_NAME
    assert PACKAGE_VERSION_FULL == f"{RUNTIME_VERSION}-{RELEASE_NAME}"

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == PROJECT_VERSION
    assert (ROOT / "main.py").read_text(encoding="utf-8").splitlines()[0] == (
        f"# Current package version: {RUNTIME_VERSION}-{RELEASE_NAME}"
    )


def test_active_manifest_and_update_index_use_current_version() -> None:
    manifest = json.loads((ROOT / "MANIFEST_CURRENT.json").read_text(encoding="utf-8"))
    index = json.loads((ROOT / "docs" / "update_history" / "INDEX.json").read_text(encoding="utf-8"))

    assert manifest["schema_version"] == "manifest_current/v14.8.5.021a"
    for key in ("version", "runtime_version", "package_version"):
        assert manifest[key] == RUNTIME_VERSION
        assert "v14.8.5.017" not in manifest[key]
    assert index["active_version"] == RUNTIME_VERSION


def test_manifest_keeps_runtime_memory_and_sqlite_out_of_static_files() -> None:
    manifest = json.loads((ROOT / "MANIFEST_CURRENT.json").read_text(encoding="utf-8"))
    entries = manifest["files"]
    paths = [entry["path"].replace("\\", "/") for entry in entries]

    forbidden_prefixes = ("memory/", "workspace_runtime/", "exports/")
    forbidden_suffixes = (".sqlite", ".sqlite3", ".sqlite-wal", ".sqlite-shm", ".zip")
    assert not [path for path in paths if path.startswith(forbidden_prefixes)]
    assert not [path for path in paths if path.lower().endswith(forbidden_suffixes)]

    for entry in entries:
        path = entry["path"].replace("\\", "/")
        if path.startswith(("reports/", "patchs/", "docs/archive/")):
            assert entry["classification"] == "archive_or_backup"
            assert entry["archive"] is True


def test_checksum_files_match_manifest_and_changed_metadata() -> None:
    manifest = json.loads((ROOT / "MANIFEST_CURRENT.json").read_text(encoding="utf-8"))
    expected = {entry["path"]: entry["sha256"] for entry in manifest["files"] if entry.get("sha256")}
    sha_all = _checksum_entries("SHA256SUMS")
    sha_static = _checksum_entries("SHA256SUMS_STATIC")

    assert sha_all == expected
    assert sha_static == expected
    for path in (
        "VERSION.txt",
        "latka_jazn/version.py",
        "pyproject.toml",
        "docs/update_history/INDEX.json",
    ):
        assert sha_all[path] == hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
