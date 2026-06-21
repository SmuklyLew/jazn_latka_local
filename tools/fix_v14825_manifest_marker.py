#!/usr/bin/env python3
"""
fix_v14825_manifest_marker.py

Naprawa spójności manifestu i markerów runtime/cache dla paczki Jaźni v14.8.2.5.

Uruchamiaj z katalogu głównego paczki, np.:
  py .\tools\fix_v14825_manifest_marker.py --dry-run
  py .\tools\fix_v14825_manifest_marker.py
  py .\tools\fix_v14825_manifest_marker.py --run-tests

Co robi:
  1. Ujednolica MANIFEST_CURRENT.json do wersji z VERSION.txt.
  2. Ustawia active_database = memory/sqlite/chat_context.sqlite3.
  3. Usuwa z manifestu wpisy volatile markerów, żeby uniknąć pętli SHA:
       ACTIVE_RUNTIME_CACHE_CONTRACT.json
       BOOTSTRAP_JAZN_CURRENT.json
       workspace_runtime/JAZN_ACTIVE_RUNTIME.json
  4. Liczy świeży SHA256 MANIFEST_CURRENT.json.
  5. Odświeża markery:
       workspace_runtime/JAZN_ACTIVE_RUNTIME.json
       ACTIVE_RUNTIME_CACHE_CONTRACT.json
       BOOTSTRAP_JAZN_CURRENT.json
  6. Aktualizuje linie SHA256SUMS/SHA256SUMS_STATIC dla zmienionych małych plików.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_VERSION = "v14.8.2.6.3-free-dialogue-short-turn-fallback-hotfix"
ACTIVE_DATABASE = "memory/sqlite/chat_context.sqlite3"
AUDIT_DATABASE = "memory/sqlite/chat_context_audit.sqlite3"
START_FILE = "main.py"
CACHE_CONTRACT_VERSION = "active_extraction_cache_contract/v14.8.2.6.3"
ACTIVE_MARKER_SCHEMA = "jazn_active_runtime_marker/v14.8.2.6.3"
BOOTSTRAP_SCHEMA = "bootstrap_jazn_current/v14.8.2.6.3"

VOLATILE_MARKERS = {
    "ACTIVE_RUNTIME_CACHE_CONTRACT.json",
    "BOOTSTRAP_JAZN_CURRENT.json",
    "workspace_runtime/JAZN_ACTIVE_RUNTIME.json",
}

HASHABLE_CHANGED_FILES = [
    "MANIFEST_CURRENT.json",
    "ACTIVE_RUNTIME_CACHE_CONTRACT.json",
    "BOOTSTRAP_JAZN_CURRENT.json",
    "workspace_runtime/JAZN_ACTIVE_RUNTIME.json",
    "tools/fix_v14825_manifest_marker.py",
]


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def normalize_rel(value: str | Path) -> str:
    return str(value).replace("\\", "/").lstrip("./")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(read_text(path))
    if not isinstance(data, dict):
        raise TypeError(f"{path} does not contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_version(root: Path) -> str:
    version_path = root / "VERSION.txt"
    if version_path.exists():
        value = read_text(version_path).strip()
        if value:
            return value
    return DEFAULT_VERSION


def backup_file(root: Path, path: Path, backup_root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": normalize_rel(path.relative_to(root)) if path.exists() else str(path),
        "exists": path.exists(),
        "backed_up": False,
        "error": None,
    }
    if not path.exists():
        return result
    try:
        rel = path.relative_to(root)
        dst = backup_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dst)
        result["backed_up"] = True
        result["backup_path"] = str(dst)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def maybe_path_from_entry(entry: Any) -> str | None:
    if isinstance(entry, str):
        return normalize_rel(entry)
    if isinstance(entry, dict):
        for key in ("path", "rel_path", "file", "filename", "name"):
            value = entry.get(key)
            if isinstance(value, str):
                return normalize_rel(value)
    return None


def prune_volatile_manifest_entries(value: Any) -> Any:
    """Recursively remove entries/keys that point at volatile marker files."""
    if isinstance(value, list):
        new_list = []
        for item in value:
            rel = maybe_path_from_entry(item)
            if rel in VOLATILE_MARKERS:
                continue
            new_list.append(prune_volatile_manifest_entries(item))
        return new_list

    if isinstance(value, dict):
        new_dict: dict[str, Any] = {}
        for key, child in value.items():
            rel_key = normalize_rel(key)
            if rel_key in VOLATILE_MARKERS:
                continue
            rel_child = maybe_path_from_entry(child)
            if rel_child in VOLATILE_MARKERS:
                continue
            new_dict[key] = prune_volatile_manifest_entries(child)
        return new_dict

    return value


def patch_manifest(root: Path, version: str) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = root / "MANIFEST_CURRENT.json"
    if not manifest_path.exists():
        raise FileNotFoundError("MANIFEST_CURRENT.json not found")

    before = read_json(manifest_path)
    after = prune_volatile_manifest_entries(before)

    after["version"] = version
    after["runtime_version"] = version
    after["package_version"] = version
    after["active_database"] = ACTIVE_DATABASE
    after["audit_database"] = AUDIT_DATABASE
    after["updated_at_utc"] = utc_now()
    after["manifest_marker_fix"] = {
        "schema_version": "manifest_marker_fix/v14.8.2.6.3",
        "active_database": ACTIVE_DATABASE,
        "volatile_markers_excluded_from_manifest": sorted(VOLATILE_MARKERS),
        "truth_boundary": (
            "Markery runtime/cache są mutable i nie powinny być hashowane jako statyczna "
            "zawartość MANIFEST_CURRENT.json, bo marker zawiera SHA manifestu."
        ),
    }

    return before, after


def marker_payload(root: Path, version: str, manifest_sha: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(existing or {})
    now = utc_now()
    payload.update({
        "schema_version": ACTIVE_MARKER_SCHEMA,
        "version": version,
        "runtime_version": version,
        "cache_contract_version": CACHE_CONTRACT_VERSION,
        "action": "reuse_existing_unpacked_folder",
        "active_root": str(root),
        "active_database": ACTIVE_DATABASE,
        "start_file": START_FILE,
        "manifest_current_sha256": manifest_sha,
        "should_reuse_existing_extraction": True,
        "source_zip": None,
        "source_zip_sha256": None,
        "checked_at_utc": now,
        "written_at_utc": now,
        "existing_marker_found": True,
        "marker_output": str(root / "workspace_runtime" / "JAZN_ACTIVE_RUNTIME.json"),
        "workspace_runtime_root": str(root / "workspace_runtime"),
        "memory_write_root": str(root / "memory"),
        "exports_root": str(root / "exports"),
        "cache_hit_reasons": [
            "active_root_exists",
            "VERSION.txt_exists",
            "start_file_exists",
            "MANIFEST_CURRENT.json_exists",
            "marker_active_root_matches",
            "marker_version_matches",
            "marker_manifest_sha256_matches",
            "active_database_matches",
            "active_marker_written_now",
        ],
        "cache_miss_reasons": [],
        "must_not_extract_again_when": [
            "active_root exists",
            "VERSION.txt matches expected Jaźń version",
            "MANIFEST_CURRENT.json sha256 matches marker",
            "source ZIP sha256 matches marker when a ZIP path is provided",
        ],
        "truth_boundary": (
            "ZIP jest źródłem importu/eksportu. Bieżące zapisy runtime i pamięci powstają "
            "w aktywnym folderze roboczym; nie wolno udawać, że zapisują się do już utworzonego ZIP-a."
        ),
    })
    return payload


def root_contract_payload(
    root: Path,
    path: Path,
    version: str,
    manifest_sha: str,
    schema_version: str,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(existing or {})
    payload.update({
        "schema_version": schema_version,
        "version": version,
        "runtime_version": version,
        "active_root": str(root),
        "active_folder": str(root),
        "active_database": ACTIVE_DATABASE,
        "audit_database": AUDIT_DATABASE,
        "start_file": START_FILE,
        "manifest_current_sha256": manifest_sha,
        "cache_contract_version": CACHE_CONTRACT_VERSION,
        "updated_at_utc": utc_now(),
        "truth_boundary": (
            "Ten marker opisuje aktywny folder roboczy. Nie jest statycznym źródłem manifestu "
            "i może zmieniać się po rozpakowaniu/uruchomieniu runtime."
        ),
    })
    return payload


def update_sha_file(root: Path, sha_file: Path, rel_paths: list[str]) -> dict[str, Any]:
    result = {"path": normalize_rel(sha_file.relative_to(root)), "exists": sha_file.exists(), "updated": False, "entries": []}
    existing_lines: list[str] = []
    if sha_file.exists():
        existing_lines = sha_file.read_text(encoding="utf-8", errors="replace").splitlines()

    wanted: dict[str, str] = {}
    for rel in rel_paths:
        p = root / rel
        if p.exists() and p.is_file():
            wanted[normalize_rel(rel)] = sha256_file(p)

    new_lines: list[str] = []
    seen: set[str] = set()
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "  " not in stripped:
            new_lines.append(line)
            continue
        old_sha, old_rel = stripped.split(None, 1)
        norm = normalize_rel(old_rel)
        if norm in wanted:
            new_lines.append(f"{wanted[norm]}  {norm}")
            seen.add(norm)
        else:
            new_lines.append(line)

    for norm, digest in wanted.items():
        if norm not in seen:
            new_lines.append(f"{digest}  {norm}")

    sha_file.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
    result["updated"] = True
    result["entries"] = sorted(wanted)
    return result


def run_cmd(root: Path, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        errors="replace",
    )
    return {
        "cmd": " ".join(cmd),
        "rc": proc.returncode,
        "output_tail": (proc.stdout or "")[-6000:],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument("--skip-sha256sums", action="store_true")
    args = parser.parse_args(argv)

    root = Path.cwd().resolve()
    version = read_version(root)
    backup_root = root / "backups" / f"before_v14825_manifest_marker_fix_{stamp()}"

    manifest_path = root / "MANIFEST_CURRENT.json"
    runtime_marker_path = root / "workspace_runtime" / "JAZN_ACTIVE_RUNTIME.json"
    active_contract_path = root / "ACTIVE_RUNTIME_CACHE_CONTRACT.json"
    bootstrap_path = root / "BOOTSTRAP_JAZN_CURRENT.json"

    report: dict[str, Any] = {
        "schema_version": "fix_v148263_manifest_marker_report/v1",
        "status": "dry_run" if args.dry_run else "applying",
        "root": str(root),
        "version": version,
        "active_database": ACTIVE_DATABASE,
        "backup_root": str(backup_root),
        "targets": [
            "MANIFEST_CURRENT.json",
            "workspace_runtime/JAZN_ACTIVE_RUNTIME.json",
            "ACTIVE_RUNTIME_CACHE_CONTRACT.json",
            "BOOTSTRAP_JAZN_CURRENT.json",
        ],
    }

    if not (root / START_FILE).exists():
        report["status"] = "blocked"
        report["errors"] = [f"Missing {START_FILE}. Run this script from package root."]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    try:
        manifest_before, manifest_after = patch_manifest(root, version)
    except Exception as exc:
        report["status"] = "blocked"
        report["errors"] = [f"{type(exc).__name__}: {exc}"]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    report["manifest_before"] = {
        "version": manifest_before.get("version"),
        "runtime_version": manifest_before.get("runtime_version"),
        "package_version": manifest_before.get("package_version"),
        "active_database": manifest_before.get("active_database"),
        "audit_database": manifest_before.get("audit_database"),
    }
    report["manifest_after"] = {
        "version": manifest_after.get("version"),
        "runtime_version": manifest_after.get("runtime_version"),
        "package_version": manifest_after.get("package_version"),
        "active_database": manifest_after.get("active_database"),
        "audit_database": manifest_after.get("audit_database"),
    }

    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    changed_files = [manifest_path, runtime_marker_path, active_contract_path, bootstrap_path]
    report["backup_results"] = [backup_file(root, p, backup_root) for p in changed_files if p.exists()]

    write_json(manifest_path, manifest_after)
    manifest_sha = sha256_file(manifest_path)
    report["manifest_current_sha256"] = manifest_sha

    runtime_marker_existing = read_json(runtime_marker_path) if runtime_marker_path.exists() else {}
    active_contract_existing = read_json(active_contract_path) if active_contract_path.exists() else {}
    bootstrap_existing = read_json(bootstrap_path) if bootstrap_path.exists() else {}

    write_json(runtime_marker_path, marker_payload(root, version, manifest_sha, runtime_marker_existing))
    write_json(
        active_contract_path,
        root_contract_payload(root, active_contract_path, version, manifest_sha, CACHE_CONTRACT_VERSION, active_contract_existing),
    )
    write_json(
        bootstrap_path,
        root_contract_payload(root, bootstrap_path, version, manifest_sha, BOOTSTRAP_SCHEMA, bootstrap_existing),
    )

    report["written"] = [
        "MANIFEST_CURRENT.json",
        "workspace_runtime/JAZN_ACTIVE_RUNTIME.json",
        "ACTIVE_RUNTIME_CACHE_CONTRACT.json",
        "BOOTSTRAP_JAZN_CURRENT.json",
    ]

    if not args.skip_sha256sums:
        sha_updates = []
        sha_path = root / "SHA256SUMS"
        if sha_path.exists():
            sha_updates.append(update_sha_file(root, sha_path, HASHABLE_CHANGED_FILES))
        static_path = root / "SHA256SUMS_STATIC"
        if static_path.exists():
            sha_updates.append(update_sha_file(root, static_path, ["MANIFEST_CURRENT.json"]))
        report["sha256sum_updates"] = sha_updates

    if args.run_tests:
        report["test_results"] = [
            run_cmd(root, [sys.executable, "-X", "utf8", "main.py", "--active-cache-status"]),
            run_cmd(root, [sys.executable, "-X", "utf8", "main.py", "--startup-status"]),
            run_cmd(root, [sys.executable, "-X", "utf8", "main.py", "--raw-chat-status-json"]),
        ]

    report["status"] = "completed"
    print(json.dumps(report, ensure_ascii=False, indent=2))

    failed_tests = any(item.get("rc") for item in report.get("test_results", []))
    return 2 if failed_tests else 0


if __name__ == "__main__":
    raise SystemExit(main())
