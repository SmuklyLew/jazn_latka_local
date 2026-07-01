from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import sqlite3

from latka_jazn.audit.audit_context_store import AuditContextStore
from latka_jazn.config import JaznConfig
from latka_jazn.db.shard_manifest import ensure_manifest
from latka_jazn.memory.store import MemoryStore
from latka_jazn.version import schema_version

SCHEMA_VERSION = schema_version("runtime_write_access_contract")


@dataclass(slots=True)
class RuntimeWriteAccessStatus:
    schema_version: str
    status: str
    ok: bool
    initialized: bool
    writes_enabled: bool
    active_runtime_write_database: str | None
    active_runtime_audit_database: str | None
    memory_db_exists: bool
    audit_db_exists: bool
    memory_integrity: str | None = None
    audit_integrity: str | None = None
    memory_error: str | None = None
    audit_error: str | None = None
    access_mode: str = "disabled_missing"
    weak_points_repaired: list[str] = field(default_factory=lambda: [
        "niepewny_czas_bez_trusted_timestamp",
        "brak_biezacego_runtime_write_v1_po_odchudzeniu_paczki",
        "osuwanie_glosu_Latki_w_trzecia_osobe_lub_techniczny_loader",
    ])
    truth_boundary: str = (
        "runtime_write_v1 jest bieżącą lokalną warstwą zapisu runtime. "
        "Nie jest archiwum pełnych eksportów ChatGPT, nie jest repozytorium Git i nie może być "
        "publikowane/pushowane bez osobnej zgody użytkownika."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _relative_or_none(root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def _sqlite_integrity(path: Path) -> tuple[str | None, str | None]:
    if not path.exists():
        return None, None
    try:
        con = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True, timeout=10.0)
        try:
            row = con.execute("PRAGMA integrity_check").fetchone()
            return str(row[0]) if row else None, None
        finally:
            con.close()
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def ensure_runtime_write_v1(config: JaznConfig) -> RuntimeWriteAccessStatus:
    """Create a clean runtime_write_v1 store when the release pack omitted old shards.

    This intentionally creates only the current runtime memory and audit SQLite
    files plus their shard manifests. It never restores old test/dev shards and
    never imports private exports.
    """
    root = Path(config.root).resolve()
    memory_path = Path(config.memory_db_path)
    audit_path = Path(config.audit_db_path)

    store = MemoryStore(memory_path)
    try:
        store.set_meta("runtime_write_access_contract", SCHEMA_VERSION)
        store.set_meta("runtime_write_source", "clean_runtime_write_v1_initialized_after_pack_exclusion")
    finally:
        store.close()

    audit = AuditContextStore(audit_path)
    try:
        audit.append_event(
            "runtime_write_v1_initialized",
            {
                "schema_version": SCHEMA_VERSION,
                "memory_db": _relative_or_none(root, memory_path),
                "audit_db": _relative_or_none(root, audit_path),
                "reason": "clean runtime_write_v1 recreated after excluding stale runtime_write shards from release pack",
            },
            source="RuntimeWriteAccessContract",
            actor="system",
            tags=["runtime_write", "init", "clean_store"],
        )
    finally:
        audit.close()

    ensure_manifest(
        root,
        config.conversation_shard_manifest_name,
        logical_database="chat_context",
        role="canonical_runtime_conversation_memory",
        default_db_path=config.memory_db_name,
        max_file_bytes=config.max_sqlite_file_bytes,
    )
    ensure_manifest(
        root,
        config.audit_shard_manifest_name,
        logical_database="chat_context_audit",
        role="canonical_realtime_audit",
        default_db_path=config.audit_db_name,
        max_file_bytes=config.max_sqlite_file_bytes,
    )
    return build_runtime_write_access_status(config, initialize=False, writes_enabled=True)


def build_runtime_write_access_status(
    config: JaznConfig,
    *,
    initialize: bool = False,
    writes_enabled: bool | None = None,
) -> RuntimeWriteAccessStatus:
    root = Path(config.root).resolve()
    if initialize:
        # Avoid recursion: initialization returns the post-init readonly status.
        return ensure_runtime_write_v1(config)

    memory_path = Path(config.memory_db_path_readonly)
    audit_path = Path(config.audit_db_path_readonly)
    memory_exists = memory_path.exists()
    audit_exists = audit_path.exists()
    memory_integrity, memory_error = _sqlite_integrity(memory_path)
    audit_integrity, audit_error = _sqlite_integrity(audit_path)

    ok = bool(memory_exists and audit_exists and memory_integrity == "ok" and audit_integrity == "ok")
    if ok:
        status = "ready"
        access_mode = "ready_write_capable" if writes_enabled else "ready_readonly_or_pending_approval"
    elif not memory_exists and not audit_exists:
        status = "missing_can_initialize"
        access_mode = "disabled_missing"
    else:
        status = "partial_or_integrity_failed"
        access_mode = "error_integrity_failed" if (memory_error or audit_error or memory_integrity not in {None, "ok"} or audit_integrity not in {None, "ok"}) else "partial_missing"

    return RuntimeWriteAccessStatus(
        schema_version=SCHEMA_VERSION,
        status=status,
        ok=ok,
        initialized=False,
        writes_enabled=bool(writes_enabled) and ok,
        active_runtime_write_database=_relative_or_none(root, memory_path) if memory_exists else None,
        active_runtime_audit_database=_relative_or_none(root, audit_path) if audit_exists else None,
        memory_db_exists=memory_exists,
        audit_db_exists=audit_exists,
        memory_integrity=memory_integrity,
        audit_integrity=audit_integrity,
        memory_error=memory_error,
        audit_error=audit_error,
        access_mode=access_mode,
    )
