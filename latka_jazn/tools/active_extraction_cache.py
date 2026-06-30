# Current package version: v14.8.5.015-runtime-bump-active-runtime-access-contract
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from latka_jazn.version import PACKAGE_VERSION, PACKAGE_VERSION_FULL, version_number

ACTIVE_EXTRACTION_CACHE_TOOL_VERSION = PACKAGE_VERSION_FULL

import hashlib
import json
import os

FALLBACK_PACKAGE_VERSION = PACKAGE_VERSION_FULL
SCHEMA_PREFIX = "jazn_active_runtime_marker"
CACHE_CONTRACT_PREFIX = "active_extraction_cache_contract"
VISIBLE_PREVIEW_CONTRACT_PREFIX = "visible_runtime_preview_contract"
SCHEMA_VERSION = f"{SCHEMA_PREFIX}/{PACKAGE_VERSION_FULL}"
CACHE_CONTRACT_VERSION = f"{CACHE_CONTRACT_PREFIX}/{PACKAGE_VERSION_FULL}"
VISIBLE_PREVIEW_CONTRACT_VERSION = f"{VISIBLE_PREVIEW_CONTRACT_PREFIX}/{PACKAGE_VERSION_FULL}"
DEFAULT_MARKER_NAME = "JAZN_ACTIVE_RUNTIME.json"
START_FILE_ORDER = ("main.py", "run.py", "jazn.py")


def _version_number(package_version: str | None = None) -> str:
    value = str(package_version or FALLBACK_PACKAGE_VERSION or "").strip()
    value = value.lstrip("\ufeff").strip()
    if value.startswith("v"):
        value = value[1:]
    return value or version_number(PACKAGE_VERSION_FULL)


def active_marker_schema_version(package_version: str | None = None) -> str:
    return f"{SCHEMA_PREFIX}/v{_version_number(package_version)}"


def active_cache_contract_version(package_version: str | None = None) -> str:
    return f"{CACHE_CONTRACT_PREFIX}/v{_version_number(package_version)}"


def visible_preview_contract_version(root: Path | None = None, package_version: str | None = None) -> str:
    version = package_version
    if version is None and root is not None:
        version = _read_text(Path(root) / "VERSION.txt")
    return f"{VISIBLE_PREVIEW_CONTRACT_PREFIX}/v{_version_number(version)}"


def _sha256_file(path: Path) -> str | None:
    path = Path(path)
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig").strip().lstrip("\ufeff").strip()
    except FileNotFoundError:
        return None


def _default_marker_output(root: Path) -> Path:
    env = os.environ.get("JAZN_ACTIVE_RUNTIME_MARKER")
    if env:
        return Path(env)
    root = Path(root).resolve()
    for parent in [root, *root.parents]:
        if parent.as_posix() == "/mnt/data":
            return parent / DEFAULT_MARKER_NAME
    return root / "workspace_runtime" / DEFAULT_MARKER_NAME


def detect_start_file(root: Path) -> str | None:
    root = Path(root)
    for name in START_FILE_ORDER:
        if (root / name).is_file():
            return name
    return None


def manifest_hash(root: Path) -> str | None:
    return _sha256_file(Path(root) / "MANIFEST_CURRENT.json")


def read_active_marker(marker_output: Path) -> dict[str, Any] | None:
    path = Path(marker_output)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema_version": "invalid_json", "marker_path": str(path), "valid": False}
    data.setdefault("marker_path", str(path))
    return data


def _runtime_versions_equivalent(marker_version: Any, file_version: str | None) -> bool:
    """Compare runtime identity versions without treating release-name suffixes as cache drift."""
    if not marker_version or not file_version:
        return False
    return version_number(str(marker_version)) == version_number(str(file_version))


def _active_storage_from_bootstrap(root: Path, version: str | None) -> dict[str, Any]:
    try:
        data = json.loads((Path(root) / "BOOTSTRAP_JAZN_CURRENT.json").read_text(encoding="utf-8"))
        active = str(data.get("active_database") or "").strip()
        if active:
            return {
                "active_database": active,
                "active_runtime_write_database": str(data.get("active_runtime_write_database") or "memory/sqlite/runtime_write_v1/runtime_memory.sqlite3"),
                "active_audit_database": str(data.get("active_audit_database") or data.get("audit_database") or "memory/sqlite/runtime_write_v1/runtime_audit.sqlite3"),
                "active_conversation_archive": str(data.get("active_conversation_archive") or active),
                "active_conversation_fts": str(data.get("active_conversation_fts") or "memory/sqlite/conversation_fts_v1/conversation_fts_0001.sqlite3"),
                "active_staging_database": str(data.get("active_staging_database") or "memory/sqlite/staging_v1/staging_memory_0001.sqlite3"),
                "storage_layout": str(data.get("storage_layout") or "conversation_archive_v1+fts_v1+staging_v1+runtime_write_v1"),
            }
    except Exception:
        pass
    if str(version).startswith(("v14.8.5", "v14.8.4", "v14.8.3")):
        return {
            "active_database": "memory/sqlite/conversation_archive_v1/conversation_archive_manifest.sqlite3",
            "active_runtime_write_database": "memory/sqlite/runtime_write_v1/runtime_memory.sqlite3",
            "active_audit_database": "memory/sqlite/runtime_write_v1/runtime_audit.sqlite3",
            "active_conversation_archive": "memory/sqlite/conversation_archive_v1/conversation_archive_manifest.sqlite3",
            "active_conversation_fts": "memory/sqlite/conversation_fts_v1/conversation_fts_0001.sqlite3",
            "active_staging_database": "memory/sqlite/staging_v1/staging_memory_0001.sqlite3",
            "storage_layout": "conversation_archive_v1+fts_v1+staging_v1+runtime_write_v1",
        }
    if str(version).startswith("v14.8.2"):
        active = "workspace_runtime/latka_jazn_v14_8_2.sqlite3"
    elif str(version).startswith("v14.8.1"):
        active = "workspace_runtime/latka_jazn_v14_8_1.sqlite3"
    elif str(version).startswith("v14.8.0"):
        active = "workspace_runtime/latka_jazn_v14_8_0.sqlite3"
    elif str(version).startswith("v14.7.0"):
        active = "workspace_runtime/latka_jazn_v14_7_0.sqlite3"
    else:
        active = "workspace_runtime/latka_jazn_v14_7_1.sqlite3" if version else None
    return {
        "active_database": active,
        "active_runtime_write_database": active,
        "active_audit_database": None,
        "active_conversation_archive": None,
        "active_conversation_fts": None,
        "active_staging_database": None,
        "storage_layout": "legacy_single_sqlite",
    }


def build_active_runtime_status(root: Path, *, source_zip: Path | None = None, marker_output: Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    marker_output = Path(marker_output) if marker_output else _default_marker_output(root)
    version = _read_text(root / "VERSION.txt")
    start_file = detect_start_file(root)
    current_manifest_sha256 = manifest_hash(root)
    source_zip = Path(source_zip).resolve() if source_zip else None
    source_zip_sha256 = _sha256_file(source_zip) if source_zip else None
    existing_marker = read_active_marker(marker_output)
    cache_hit_reasons: list[str] = []
    cache_miss_reasons: list[str] = []

    if root.exists():
        cache_hit_reasons.append("active_root_exists")
    else:
        cache_miss_reasons.append("active_root_missing")
    if version:
        cache_hit_reasons.append("VERSION.txt_exists")
    else:
        cache_miss_reasons.append("VERSION.txt_missing")
    if start_file:
        cache_hit_reasons.append("start_file_exists")
    else:
        cache_miss_reasons.append("start_file_missing_main_run_jazn")
    if current_manifest_sha256:
        cache_hit_reasons.append("MANIFEST_CURRENT.json_exists")
    else:
        cache_miss_reasons.append("MANIFEST_CURRENT.json_missing")

    if existing_marker and existing_marker.get("valid", True):
        if existing_marker.get("active_root") == str(root):
            cache_hit_reasons.append("marker_active_root_matches")
        else:
            cache_miss_reasons.append("marker_active_root_differs_or_missing")
        if _runtime_versions_equivalent(existing_marker.get("version"), version):
            cache_hit_reasons.append("marker_version_matches")
        else:
            cache_miss_reasons.append("marker_version_differs_or_missing")
        if existing_marker.get("manifest_current_sha256") == current_manifest_sha256:
            cache_hit_reasons.append("marker_manifest_sha256_matches")
        else:
            cache_miss_reasons.append("marker_manifest_sha256_differs_or_missing")
        if source_zip_sha256:
            if existing_marker.get("source_zip_sha256") == source_zip_sha256:
                cache_hit_reasons.append("marker_source_zip_sha256_matches")
            else:
                cache_miss_reasons.append("marker_source_zip_sha256_differs_or_missing")
    else:
        cache_miss_reasons.append("active_marker_missing_or_invalid")

    hard_missing_reasons = {"active_root_missing", "VERSION.txt_missing", "start_file_missing_main_run_jazn", "MANIFEST_CURRENT.json_missing"}
    missing_hard_requirement = any(reason in hard_missing_reasons for reason in cache_miss_reasons)
    marker_differs = any("differs" in reason for reason in cache_miss_reasons)
    marker_refresh_required = any(reason.startswith("marker_") or reason.startswith("active_marker_") for reason in cache_miss_reasons)
    source_zip_mismatch = any(reason == "marker_source_zip_sha256_differs_or_missing" for reason in cache_miss_reasons)
    # Marker drift after a version/manifest update must not force re-extraction when the
    # current folder itself is complete. It only means the marker should be refreshed.
    should_reuse_existing_extraction = bool(
        root.exists()
        and version
        and start_file
        and current_manifest_sha256
        and not missing_hard_requirement
        and not source_zip_mismatch
    )

    marker_schema_version = active_marker_schema_version(version)
    cache_contract_version = active_cache_contract_version(version)
    storage = _active_storage_from_bootstrap(root, version)

    return {
        "schema_version": marker_schema_version,
        "cache_contract_version": cache_contract_version,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "active_root": str(root),
        "version": version,
        "start_file": start_file,
        **storage,
        "manifest_current_sha256": current_manifest_sha256,
        "source_zip": str(source_zip) if source_zip else None,
        "source_zip_sha256": source_zip_sha256,
        "marker_output": str(marker_output),
        "existing_marker_found": bool(existing_marker),
        "cache_hit_reasons": cache_hit_reasons,
        "cache_miss_reasons": cache_miss_reasons,
        "should_reuse_existing_extraction": should_reuse_existing_extraction,
        "marker_refresh_required": bool(marker_refresh_required),
        "marker_differs": bool(marker_differs),
        "must_not_extract_again_when": [
            "active_root exists",
            "VERSION.txt matches expected Jaźń version",
            "MANIFEST_CURRENT.json sha256 matches marker",
            "source ZIP sha256 matches marker when a ZIP path is provided",
        ],
        "truth_boundary": "ZIP jest źródłem importu/eksportu. Bieżące zapisy runtime i pamięci powstają w aktywnym folderze roboczym; nie wolno udawać, że zapisują się do już utworzonego ZIP-a.",
    }


def write_active_runtime_marker(root: Path, *, source_zip: Path | None = None, marker_output: Path | None = None, action: str = "reuse_existing_unpacked_folder") -> dict[str, Any]:
    root = Path(root).resolve()
    marker_output = Path(marker_output) if marker_output else _default_marker_output(root)
    status = build_active_runtime_status(root, source_zip=source_zip, marker_output=marker_output)
    # `write_active_runtime_marker` overwrites the marker atomically, so stale marker-only
    # differences observed before the write must not be reported as the post-write decision.
    marker_only_prefixes = ("active_marker_", "marker_")
    status["cache_miss_reasons"] = [
        reason for reason in status.get("cache_miss_reasons", [])
        if not reason.startswith(marker_only_prefixes)
    ]
    status.setdefault("cache_hit_reasons", []).append("active_marker_written_now")
    status["existing_marker_found"] = True
    status["marker_refresh_required"] = any(
        reason.startswith(marker_only_prefixes)
        for reason in status["cache_miss_reasons"]
    )
    status["marker_differs"] = any("differs" in reason for reason in status["cache_miss_reasons"])
    hard_missing = {"active_root_missing", "VERSION.txt_missing", "start_file_missing_main_run_jazn", "MANIFEST_CURRENT.json_missing"}
    status["should_reuse_existing_extraction"] = not any(reason in hard_missing for reason in status["cache_miss_reasons"])
    marker = {
        **status,
        "schema_version": status.get("schema_version") or active_marker_schema_version(status.get("version")),
        "written_at_utc": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "memory_write_root": str(root / "memory"),
        "workspace_runtime_root": str(root / "workspace_runtime"),
        "exports_root": str(root / "exports"),
        "visible_runtime_preview_contract": {
            "schema_version": visible_preview_contract_version(root, status.get("version")),
            "required_when_user_asks_about": ["runtime", "timestamp", "runtime preview", "aktywny folder", "pamięć", "pliki Jaźni", "uruchomienie", "fallback"],
            "required_visible_fields": ["timestamp_header", "active_root", "start_file", "runtime_answer_quality", "fallback_classification", "response_source", "one_shot_or_chat_loop_limit"],
            "forbidden_behavior": "Nie wolno schować timestampu i jakości runtime w samym JSON ani mówić ogólnie, że runtime działa, bez pokazania statusu przy pytaniu diagnostycznym.",
        },
    }
    marker_output.parent.mkdir(parents=True, exist_ok=True)
    tmp = marker_output.with_suffix(marker_output.suffix + ".tmp")
    tmp.write_text(json.dumps(marker, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, marker_output)
    return marker
