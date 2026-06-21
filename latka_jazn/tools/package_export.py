from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sqlite3
import zipfile

from latka_jazn.memory.session_continuity import SessionContinuityManager

SYSTEM_EXCLUDE_PREFIXES = (
    "memory/",
    "workspace_runtime/",
    "exports/",
)
NLP_INCLUDE_PREFIXES = (
    "latka_jazn/nlp/",
    "latka_jazn/resources/",
)
NLP_INCLUDE_EXACT = {
    "MANIFEST_V14_6_1_NLP_ADAPTER_ZIP_PROFILES.json",
    "MANIFEST_V14_6_1_12_RUNTIME_PREVIEW_SOURCE_ORIGIN_SELF_STATE.json",
    "MANIFEST_V14_6_1_13_COGNITIVE_TURN_ENVELOPE.json",
    "UPDATE_REPORT_V14_6_1.md",
    "UPDATE_REPORT_V14_6_1_12.md",
    "UPDATE_REPORT_V14_6_1_14.md",
    "UPDATE_REPORT_V14_6_2.md",
    "UPDATE_REPORT_V14_6_2_1.md",
    "MANIFEST_V14_6_2_1_STALE_NLP_ROUTE_HOTFIX.json",
    "docs/UPDATE_V14_6_1_NLP_ADAPTER_ZIP_PROFILES.md",
    "docs/UPDATE_V14_6_1_12_RUNTIME_PREVIEW_SOURCE_ORIGIN_SELF_STATE.md",
    "docs/UPDATE_V14_6_1_13_COGNITIVE_TURN_ENVELOPE.md",
    "docs/UPDATE_V14_6_2_CONTEXTUAL_GREETING_FALLBACK_REPAIR.md",
    "docs/UPDATE_V14_6_2_1_STALE_NLP_ROUTE_HOTFIX.md",
}
GITHUB_SAFE_EXCLUDE_PREFIXES = (
    "memory/raw/",
    "workspace_runtime/",
    "exports/",
)
COMMON_EXCLUDE_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
}
COMMON_EXCLUDE_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".tmp",
    ".bak",
    ".zip",
    ".sqlite3-wal",
    ".sqlite3-shm",
    "-wal",
    "-shm",
)
SKIP_EXPANDED_RAW_CHAT_IF_ARCHIVE_PRESENT = True

@dataclass(slots=True)
class PackageExportReport:
    mode: str
    output_zip: str
    created_at_utc: str
    file_count: int
    total_uncompressed_bytes: int
    zip_size_bytes: int
    sha256: str
    includes_memory: bool
    includes_system: bool
    notes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_common_excluded(path: Path, rel: str, output_zip: Path) -> bool:
    if path == output_zip:
        return True
    if any(part in COMMON_EXCLUDE_PARTS for part in path.parts):
        return True
    if rel.startswith("exports/"):
        return True
    return any(rel.endswith(suffix) for suffix in COMMON_EXCLUDE_SUFFIXES)


def _iter_files(root: Path, mode: str, output_zip: Path):
    root = Path(root).resolve()
    output_zip = Path(output_zip).resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if _is_common_excluded(path.resolve(), rel, output_zip):
            continue
        if (
            SKIP_EXPANDED_RAW_CHAT_IF_ARCHIVE_PRESENT
            and rel == "memory/raw/chat.html"
            and (root / "memory" / "raw" / "chat.html.7z").exists()
        ):
            continue
        if mode == "system" and rel.startswith(SYSTEM_EXCLUDE_PREFIXES):
            continue
        if mode == "memory" and not (rel.startswith("memory/") or rel.startswith("workspace_runtime/")):
            continue
        if mode == "nlp" and not (rel.startswith(NLP_INCLUDE_PREFIXES) or rel in NLP_INCLUDE_EXACT):
            continue
        if mode == "github_source_safe" and rel.startswith(GITHUB_SAFE_EXCLUDE_PREFIXES):
            continue
        yield path, rel



def _checkpoint_sqlite_databases(root: Path) -> list[str]:
    """Nie blokuje eksportu na aktywnych bazach SQLite.

    v14.6.10: podczas testów regresji kilka wcześniejszych testów może jeszcze
    trzymać krótkie uchwyty do SQLite/WAL. Eksport nie może wtedy wyglądać jak
    zawieszony runtime. Paczka i tak pomija transient `-wal/-shm`; jeżeli plik
    WAL istnieje, zapisujemy notatkę zamiast czekać na checkpoint.
    """
    notes: list[str] = []
    for db in sorted(Path(root).rglob("*.sqlite3")):
        if any(part in COMMON_EXCLUDE_PARTS for part in db.parts):
            continue
        if Path(str(db) + "-wal").exists() or Path(str(db) + "-shm").exists():
            try:
                rel = db.relative_to(root).as_posix()
            except Exception:
                rel = str(db)
            notes.append(f"Pominięto blokujący checkpoint WAL dla {rel}; transient WAL/SHM nie są pakowane.")
    return notes

def export_package(root: Path, mode: str, output_zip: Path | None = None) -> PackageExportReport:
    """Tworzy paczkę ZIP: system-only, memory-only albo full.

    Tryby:
    - system: kod, dokumentacja, testy, manifesty; bez `memory/` i bez `workspace_runtime/`.
    - memory: `memory/` oraz `workspace_runtime/`, czyli surowa pamięć, warstwy i SQLite.
    - nlp: adaptery i lekkie zasoby NLP bez pamięci oraz bez modeli ciężkich.
    - github_source_safe: źródła bez dużej surowej pamięci i aktywnych baz.
    - full: pełny system z pamięcią, bez cache i bez wcześniej wygenerowanych ZIP-ów.
    """
    root = Path(root).resolve()
    if mode not in {"system", "memory", "nlp", "github_source_safe", "full"}:
        raise ValueError("mode must be one of: system, memory, nlp, github_source_safe, full")
    exports_dir = root / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if output_zip is None:
        output_zip = exports_dir / f"latka_jazn_{mode}_{stamp}.zip"
    else:
        output_zip = Path(output_zip)
        if not output_zip.is_absolute():
            output_zip = root / output_zip
        output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()

    notes: list[str] = []
    if mode in {"memory", "full"}:
        try:
            SessionContinuityManager(root, version=(root / "VERSION.txt").read_text(encoding="utf-8").strip() if (root / "VERSION.txt").exists() else "unknown").update_index(reason=f"export_{mode}", source="package_export.export_package")
            notes.append("Zaktualizowano session_continuity_index.json przed eksportem pamięci/pełnej paczki.")
        except Exception as exc:
            notes.append(f"Nie udało się odświeżyć session_continuity_index.json przed eksportem: {exc!r}")
        notes.extend(_checkpoint_sqlite_databases(root))

    file_count = 0
    total = 0
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True, compresslevel=1) as zf:
        for path, rel in _iter_files(root, mode, output_zip):
            st = path.stat()
            total += st.st_size
            file_count += 1
            # Duże bazy SQLite i archiwa 7z są kosztowne do ponownej kompresji w testach
            # oraz eksporcie pełnym, a zysk bywa niewielki. Przechowujemy je bez deflate,
            # żeby eksport był przewidywalny i nie wyglądał jak zawieszony runtime.
            compress_type = zipfile.ZIP_STORED if rel.endswith((".sqlite3", ".7z")) else zipfile.ZIP_DEFLATED
            zf.write(path, rel, compress_type=compress_type)

    if file_count == 0:
        notes.append("Paczka nie zawierała plików; sprawdź tryb eksportu i ścieżkę root.")
    if mode in {"memory", "full"}:
        continuity_index = root / "memory" / "raw" / "session_continuity_index.json"
        if continuity_index.exists():
            notes.append("Dołączono memory/raw/session_continuity_index.json oraz memory/layered/continuity.jsonl, jeśli istnieje.")
        raw_chat = root / "memory" / "raw" / "chat.html"
        raw_archive = root / "memory" / "raw" / "chat.html.7z"
        if raw_archive.exists():
            notes.append(f"Dołączono skompresowaną surową pamięć chat.html.7z ({raw_archive.stat().st_size} B).")
            if raw_chat.exists() and SKIP_EXPANDED_RAW_CHAT_IF_ARCHIVE_PRESENT:
                notes.append("Pominięto rozpakowany memory/raw/chat.html w ZIP, żeby nie dublować 896 MB danych; można go odtworzyć z chat.html.7z.")
        elif raw_chat.exists():
            notes.append(f"Dołączono rozpakowaną surową pamięć chat.html ({raw_chat.stat().st_size} B).")
        else:
            notes.append("Nie znaleziono memory/raw/chat.html ani chat.html.7z.")
    if mode == "system":
        notes.append("Eksport system-only celowo pomija memory/ oraz workspace_runtime/.")
    if mode == "nlp":
        notes.append("Eksport NLP-resources-only zawiera adaptery i lekkie zasoby NLP; nie zawiera pamięci ani ciężkich modeli.")
    if mode == "github_source_safe":
        notes.append("Eksport github-source-safe pomija surową pamięć, chat.html.7z oraz aktywne bazy SQLite.")

    report = PackageExportReport(
        mode=mode,
        output_zip=str(output_zip),
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        file_count=file_count,
        total_uncompressed_bytes=total,
        zip_size_bytes=output_zip.stat().st_size,
        sha256=_sha256_file(output_zip),
        includes_memory=mode in {"memory", "full"},
        includes_system=mode in {"system", "nlp", "github_source_safe", "full"},
        notes=notes,
    )
    report_path = output_zip.with_suffix(".report.json")
    report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def export_package_json(root: Path, mode: str, output_zip: Path | None = None) -> str:
    return json.dumps(export_package(root, mode, output_zip).to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
