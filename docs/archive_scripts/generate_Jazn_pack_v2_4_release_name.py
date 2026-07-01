#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
generate_Jazn_pack.py

Wersja v2: numer wersji jest czytany z version.py i dopisywany do nazw wyjściowych.
Tworzy archiwum ZIP bez zapisywania pełnego ZIP-a na dysku: strumień ZIP jest
od razu zapisywany do kolejnych części, np.:

    nazwa.zip.001
    nazwa.zip.002
    nazwa.zip.003

Jednocześnie tworzy pliki SHA256:

    nazwa.zip.parts.sha256          - SHA256 każdej części
    nazwa.zip.sha256                - SHA256 logicznego pełnego ZIP-a
    nazwa.zip.source_files.sha256   - SHA256 plików źródłowych w folderze
    nazwa.zip.manifest.json         - manifest techniczny
    nazwa.zip.join.ps1              - pomocniczy skrypt PowerShell do złożenia pełnego ZIP-a

WAŻNE:
- To NIE jest natywny wielodyskowy ZIP typu .z01/.z02/.zip.
- To jest zwykły poprawny ZIP zapisany strumieniowo do części .zip.001, .zip.002 itd.
- Aby rozpakować, najpierw połącz części w jeden plik .zip, potem rozpakuj.
- Skrypt nie tworzy tymczasowego pełnego ZIP-a, więc oszczędza miejsce na dysku.



Przykłady:

    py generate_Jazn_pack.py "D:\\.AI\\jazn_latka_local" --out "D:\\Desktop\\pakiet" --part-size-mb 450 --force

    Jeśli .\latka_jazn\version.py ma PACKAGE_VERSION = "14.8.9", wynikiem będzie m.in.:

        jazn_latka_v14.8.9.zip.001
        jazn_latka_v14.8.9.zip.parts.sha256
        jazn_latka_v14.8.9.zip.manifest.json

    Jeśli dodatkowo PACKAGE_RELEASE_NAME = "trusted-time-runtime-write-voice-gate",
    wynikiem będzie m.in.:

        jazn_latka_v14.8.9-trusted-time-runtime-write-voice-gate.zip.001
        jazn_latka_v14.8.9-trusted-time-runtime-write-voice-gate.zip.manifest.json

    py .\generate_Jazn_pack.py "D:\.AI\jazn_latka_local" `
  --out "D:\Desktop\pakiet" `  --part-size-mb 450 `  --compresslevel 6 `  --force `
  --exclude ".git/*" `  --exclude ".vscode/*" `  --exclude ".codex/.codex/log/*" `

    Od wersji v2.2 część bezpiecznych wykluczeń jest zapisana na stałe w
    EXCLUDE_PATTERNS, np. .git/, cache, raporty, runtime_write_v1 i ciężkie
    pliki processed/raw. Możesz dopisać własne:

        py .\generate_Jazn_pack.py "D:\.AI\jazn_latka_local" --exclude "docs/"

    Albo wyłączyć listę domyślną:

        py .\generate_Jazn_pack.py "D:\.AI\jazn_latka_local" --no-default-excludes
    
Konfiguracja bez argumentów CLI jest niżej w sekcji USTAWIENIA DOMYŚLNE.
"""

from __future__ import annotations

VERSION = "2.4"
import argparse
import ast
import re
import datetime as _dt
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import time
import zipfile
from typing import Any, BinaryIO, Iterable

# =============================================================================
# USTAWIENIA DOMYŚLNE - możesz zmienić tutaj i uruchamiać skrypt bez argumentów
# =============================================================================

SOURCE_FOLDER = r""          # np. r"D:\.AI\latka_jazn_v14_8_2_work"
OUTPUT_DIR = r""             # puste = folder nadrzędny SOURCE_FOLDER
ARCHIVE_BASENAME = r"jazn_latka"  # domyślnie bez --name: jazn_latka_v<WERSJA>.zip.001
PART_SIZE_MB = 500            # rozmiar jednej części w MiB
COMPRESSION_LEVEL = 6         # 0-9 dla ZIP_DEFLATED; 0 szybciej/słabiej, 9 wolniej/mocniej
FORCE_OVERWRITE = False       # True = nadpisuje wcześniejsze części/manifesty
INCLUDE_EMPTY_DIRS = True      # zapisuje też puste katalogi
APPEND_VERSION_TO_NAME = True  # True = dopisuje _v<PACKAGE_VERSION> przed .zip
VERSION_FILE = r""            # puste = auto, najpierw .\latka_jazn\version.py
VERSION_VARIABLES = ("PACKAGE_VERSION", "__version__", "VERSION")
RELEASE_NAME_VARIABLES = ("PACKAGE_RELEASE_NAME",)
PACKAGE_RELEASE_NAME = r""
# Domyślne wykluczenia dla zwykłej paczki runtime.
# Te wzorce działają zawsze, chyba że użyjesz --no-default-excludes.
#
# Reguła praktyczna:
# - folder możesz podać jako "memory/" albo "memory/*"; oba warianty wytną całą gałąź,
# - dodatkowe wykluczenia możesz nadal dopisać z CLI przez --exclude "ścieżka/*",
# - jeżeli chcesz spakować absolutnie wszystko, użyj --no-default-excludes.
EXCLUDE_PATTERNS: list[str] = [

    # Git / edytory / lokalny stan narzędzi
    ".git/",
    ".vscode/",
    ".codex/",

    # Python / test / cache
    "__pycache__/",
    ".pytest_cache/",
    ".pytest-tmp/",
    ".mypy_cache/",
    ".ruff_cache/",
    "*.pyc",
    "*.pyo",

    # Tymczasowe i odrzucone pliki
    "*.tmp",
    "*.partial",
    "*.tmp_extract_part",
    "*.bak",
    "*.bad",
    "*.corrupt",
    "*.log",

    # Paczki, backupy, raporty i artefakty patchowania
    "exports/",
    "reports/",
    "backups/",
    "backups_git/",
    "*.patch",
    "*.rej",
    "*.orig",
    "*_PATCH_REPORT.md",
    "LATKA_*_COMMANDS.ps1",
    "v14_*_sha256.txt",
    "v14_*_patch_bundle.zip",
    "v14_*_PATCH_FIXED_BUNDLE.zip",
    "v14_*_FULL_PATCH_AND_RECOVERY_BUNDLE.zip",

    # Najcięższe / niepotrzebne w paczce runtime dopóki zapis DB nie ma osobnego kontraktu
    "memory/sqlite/runtime_write_v1/",
    "memory/raw/runtime_events.jsonl",
    "workspace_runtime/test_*.sqlite3",
    "runtime-preview-*.json",
]

CHUNK_SIZE = 1024 * 1024      # 1 MiB; rozmiar bufora czytania plików

# =============================================================================


def human_size(num: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(num)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{num} B"


def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _literal_string_from_assignment(node: ast.AST) -> str | None:
    """Zwraca tekst tylko dla prostych przypisań stałych, bez wykonywania version.py."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def read_version_from_py(version_file: Path, variable_names: Iterable[str] = VERSION_VARIABLES) -> str:
    """
    Czyta wersję z pliku version.py przez AST, bez importowania i bez uruchamiania kodu.

    Obsługiwane zmienne domyślnie:
      - PACKAGE_VERSION = "14.8.9"
      - __version__ = "14.8.9"
      - VERSION = "14.8.9"
    """
    version_file = version_file.resolve()
    if not version_file.exists() or not version_file.is_file():
        raise FileNotFoundError(f"Nie znaleziono pliku wersji: {version_file}")

    text = version_file.read_text(encoding="utf-8-sig")
    tree = ast.parse(text, filename=str(version_file))
    wanted = set(variable_names)

    for node in tree.body:
        if isinstance(node, ast.Assign):
            value = _literal_string_from_assignment(node.value)
            if value is None:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    return normalize_version(value)
        elif isinstance(node, ast.AnnAssign):
            value = _literal_string_from_assignment(node.value) if node.value is not None else None
            if value is None:
                continue
            target = node.target
            if isinstance(target, ast.Name) and target.id in wanted:
                return normalize_version(value)

    raise ValueError(
        f"Nie znaleziono zmiennej wersji {sorted(wanted)} w pliku: {version_file}"
    )


def read_optional_string_from_py(version_file: Path, variable_names: Iterable[str]) -> str:
    """Czyta opcjonalną zmienną tekstową z pliku Python przez AST, bez importowania kodu."""
    version_file = version_file.resolve()
    if not version_file.exists() or not version_file.is_file():
        raise FileNotFoundError(f"Nie znaleziono pliku: {version_file}")

    text = version_file.read_text(encoding="utf-8-sig")
    tree = ast.parse(text, filename=str(version_file))
    wanted = set(variable_names)

    for node in tree.body:
        if isinstance(node, ast.Assign):
            value = _literal_string_from_assignment(node.value)
            if value is None:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    return value.strip().strip('"\'')
        elif isinstance(node, ast.AnnAssign):
            value = _literal_string_from_assignment(node.value) if node.value is not None else None
            if value is None:
                continue
            target = node.target
            if isinstance(target, ast.Name) and target.id in wanted:
                return value.strip().strip('"\'')

    return ""


def find_version_file(source_folder: Path, explicit_version_file: str | Path | None = None) -> Path:
    """Znajduje version.py dla pakowanego projektu.

    Domyślnie pierwszeństwo ma ścieżka względna wobec aktualnego katalogu pracy:
      .\\latka_jazn\\version.py

    Dzięki temu zwykłe uruchomienie z katalogu projektu nie wymaga ani importu
    pakietu, ani podawania --version-file.
    """
    if explicit_version_file:
        return Path(explicit_version_file).expanduser().resolve()

    cwd = Path.cwd().resolve()
    script_dir = Path(__file__).resolve().parent
    candidates = [
        cwd / "latka_jazn" / "version.py",
        source_folder / "latka_jazn" / "version.py",
        script_dir / "latka_jazn" / "version.py",
        cwd / "version.py",
        source_folder / "version.py",
        script_dir / "version.py",
    ]

    seen: set[Path] = set()
    unique_candidates: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_candidates.append(resolved)

    for candidate in unique_candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    pretty = "\n".join(f"  - {p}" for p in unique_candidates)
    raise FileNotFoundError(
        "Nie znaleziono version.py. Podaj --version-file albo umieść plik w jednej z lokalizacji:\n" + pretty
    )


def normalize_version(value: str) -> str:
    """Normalizuje wersję do postaci bez wiodącego v, np. v14.8.9 -> 14.8.9."""
    version = str(value).strip().strip('"\'')
    version = re.sub(r"^v", "", version, flags=re.IGNORECASE)
    if not version:
        raise ValueError("Wersja z version.py jest pusta")
    if any(ch in version for ch in '\\/?:*"<>|'):
        raise ValueError(f"Wersja zawiera znaki niedozwolone w nazwie pliku: {version!r}")
    return version


def normalize_release_name(value: str | None) -> str:
    """Normalizuje PACKAGE_RELEASE_NAME do bezpiecznego sufiksu nazwy pliku."""
    release = str(value or "").strip().strip('"\'')
    if not release:
        return ""
    if any(ch in release for ch in '\\/>:<*?"|'):
        raise ValueError(f"PACKAGE_RELEASE_NAME zawiera znaki niedozwolone w nazwie pliku: {release!r}")
    release = re.sub(r"\s+", "-", release)
    release = release.strip("-_.")
    return release


def apply_version_to_archive_name(
    archive_basename: str,
    package_version: str,
    *,
    package_release_name: str | None = None,
    enabled: bool = True,
) -> str:
    """
    Zwraca finalną nazwę ZIP-a z wersją i opcjonalną nazwą release przed .zip.

    Przykłady:
      jazn_latka + 14.8.9                  -> jazn_latka_v14.8.9.zip
      jazn_latka + 14.8.9 + hotfix         -> jazn_latka_v14.8.9-hotfix.zip
      jazn_latka.zip + 14.8.9              -> jazn_latka_v14.8.9.zip
      jazn_latka_{version}.zip             -> jazn_latka_14.8.9.zip
      jazn_latka_v{version}-{release}.zip  -> jazn_latka_v14.8.9-hotfix.zip
    """
    raw = archive_basename.strip()
    if not raw:
        raise ValueError("archive_basename nie może być pusty")

    has_zip = raw.lower().endswith(".zip")
    stem = raw[:-4] if has_zip else raw
    version = normalize_version(package_version)
    release = normalize_release_name(package_release_name)

    if "{version}" in stem:
        stem = stem.replace("{version}", version)
    elif enabled:
        suffix = f"_v{version}"
        if not stem.lower().endswith(suffix.lower()):
            stem = f"{stem}{suffix}"

    if "{release_name}" in stem or "{release}" in stem:
        stem = stem.replace("{release_name}", release).replace("{release}", release)
        stem = re.sub(r"[-_.]+$", "", stem)
    elif enabled and release:
        release_suffix = f"-{release}"
        if not version.lower().endswith(release_suffix.lower()) and not stem.lower().endswith(release_suffix.lower()):
            stem = f"{stem}{release_suffix}"

    return f"{stem}.zip"


def safe_zip_datetime(path: Path) -> tuple[int, int, int, int, int, int]:
    """ZIP central directory nie obsługuje dat < 1980 ani > 2107."""
    try:
        tm = time.localtime(path.stat().st_mtime)
        year = min(max(tm.tm_year, 1980), 2107)
        return (year, tm.tm_mon, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec)
    except Exception:
        return (1980, 1, 1, 0, 0, 0)


def rel_posix(path: Path, root: Path) -> str:
    return PurePosixPath(path.relative_to(root).as_posix()).as_posix()


def is_excluded(rel: str, patterns: Iterable[str]) -> bool:
    """Sprawdza, czy ścieżka względna ma zostać pominięta.

    Obsługiwane są zwykłe wzorce fnmatch oraz wygodne wpisy folderów:
      - "memory/" wyklucza memory i całą zawartość,
      - "memory/*" działa klasycznie przez fnmatch,
      - "*.pyc" działa po całej ścieżce i po samej nazwie pliku.
    """
    rel = rel.replace("\\", "/").lstrip("/")
    rel_name = PurePosixPath(rel).name

    for pat in patterns:
        p = pat.strip().replace("\\", "/").lstrip("/")
        if not p:
            continue

        # Wpis folderu bez gwiazdek, np. "memory/", ma ucinać całą gałąź.
        if p.endswith("/"):
            folder = p.rstrip("/")
            if rel == folder or rel.startswith(folder + "/"):
                return True
            continue

        if fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(rel_name, p):
            return True

    return False


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


class SplitPartWriter:
    """
    Nie-seekowalny obiekt plikopodobny dla zipfile.ZipFile.
    Każdy zapis trafia od razu do .zip.001, .zip.002 itd.
    """

    def __init__(self, out_dir: Path, base_zip_name: str, part_size: int, *, force: bool = False):
        if part_size <= 0:
            raise ValueError("part_size musi być większy od zera")
        self.out_dir = out_dir
        self.base_zip_name = base_zip_name
        self.part_size = part_size
        self.force = force

        self.total_written = 0
        self.current_part_no = 0
        self.current_part_written = 0
        self.current_file: BinaryIO | None = None
        self.current_hash: Any | None = None
        self.full_hash = hashlib.sha256()
        self.parts: list[dict[str, object]] = []
        self.closed = False

        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._check_existing_outputs()

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def readable(self) -> bool:
        return False

    def tell(self) -> int:
        return self.total_written

    def flush(self) -> None:
        if self.current_file:
            self.current_file.flush()

    def close(self) -> None:
        if self.closed:
            return
        self._close_current_part()
        self.closed = True

    def write(self, data) -> int:  # zipfile przekazuje bytes-like object
        if self.closed:
            raise ValueError("zapis do zamkniętego SplitPartWriter")
        if not data:
            return 0

        view = memoryview(data)
        total_len = len(view)
        offset = 0

        while offset < total_len:
            if self.current_file is None:
                self._open_next_part()

            free = self.part_size - self.current_part_written
            if free <= 0:
                self._close_current_part()
                continue

            take = min(free, total_len - offset)
            chunk = view[offset : offset + take]

            assert self.current_file is not None
            assert self.current_hash is not None
            self.current_file.write(chunk)
            self.current_hash.update(chunk)
            self.full_hash.update(chunk)

            self.current_part_written += take
            self.total_written += take
            offset += take

            if self.current_part_written >= self.part_size:
                self._close_current_part()

        return total_len

    def _part_path(self, no: int) -> Path:
        return self.out_dir / f"{self.base_zip_name}.{no:03d}"

    def _known_output_paths(self) -> list[Path]:
        patterns = [
            f"{self.base_zip_name}.*",
            f"{self.base_zip_name}.parts.sha256",
            f"{self.base_zip_name}.sha256",
            f"{self.base_zip_name}.source_files.sha256",
            f"{self.base_zip_name}.manifest.json",
            f"{self.base_zip_name}.join.ps1",
        ]
        paths: list[Path] = []
        for pat in patterns:
            paths.extend(self.out_dir.glob(pat))
        return sorted(set(paths))

    def _check_existing_outputs(self) -> None:
        existing = self._known_output_paths()
        if not existing:
            return
        if not self.force:
            sample = "\n".join(f"  - {p}" for p in existing[:20])
            more = "" if len(existing) <= 20 else f"\n  ... oraz {len(existing) - 20} więcej"
            raise FileExistsError(
                "Znaleziono wcześniejsze pliki wyjściowe. Użyj --force albo zmień --name/--out.\n"
                + sample
                + more
            )
        for p in existing:
            if p.is_file():
                p.unlink()

    def _open_next_part(self) -> None:
        self.current_part_no += 1
        self.current_part_written = 0
        part_path = self._part_path(self.current_part_no)
        self.current_file = part_path.open("xb")
        self.current_hash = hashlib.sha256()

    def _close_current_part(self) -> None:
        if self.current_file is None:
            return
        self.current_file.flush()
        self.current_file.close()
        assert self.current_hash is not None
        part_path = self._part_path(self.current_part_no)
        size = part_path.stat().st_size
        self.parts.append(
            {
                "part_no": self.current_part_no,
                "filename": part_path.name,
                "size_bytes": size,
                "sha256": self.current_hash.hexdigest(),
            }
        )
        self.current_file = None
        self.current_hash = None
        self.current_part_written = 0


def discover_entries(root: Path, include_empty_dirs: bool, exclude_patterns: list[str]) -> tuple[list[Path], list[Path], int]:
    files: list[Path] = []
    dirs: list[Path] = []
    total_size = 0

    for p in sorted(root.rglob("*"), key=lambda x: x.as_posix().lower()):
        rel = rel_posix(p, root)
        if is_excluded(rel, exclude_patterns):
            continue
        if p.is_dir():
            if include_empty_dirs:
                dirs.append(p)
            continue
        if p.is_file():
            files.append(p)
            try:
                total_size += p.stat().st_size
            except OSError:
                pass
    return files, dirs, total_size


def make_zipinfo_for_file(src: Path, arcname: str, compression: int, compresslevel: int) -> zipfile.ZipInfo:
    zi = zipfile.ZipInfo(arcname, date_time=safe_zip_datetime(src))
    zi.compress_type = compression
    # Python 3.13+ ma publiczne compress_level; starsze wersje używają _compresslevel.
    # Ustawiamy przez setattr, żeby Pylance/Pyright nie zgłaszał błędu atrybutu.
    for attr_name in ("compress_level", "_compresslevel"):
        try:
            setattr(zi, attr_name, compresslevel)
        except Exception:
            pass
    try:
        mode = src.stat().st_mode
        zi.external_attr = (mode & 0xFFFF) << 16
        if os.name == "nt":
            # Bit archiwalny/normalny dla lepszej zgodności na Windows.
            zi.external_attr |= 0x20
    except OSError:
        pass
    return zi


def make_zipinfo_for_dir(src: Path, arcname: str) -> zipfile.ZipInfo:
    if not arcname.endswith("/"):
        arcname += "/"
    zi = zipfile.ZipInfo(arcname, date_time=safe_zip_datetime(src))
    zi.external_attr = ((src.stat().st_mode if src.exists() else 0o40755) & 0xFFFF) << 16 | 0x10
    zi.compress_type = zipfile.ZIP_STORED
    return zi


def write_join_script(out_dir: Path, base_zip_name: str) -> None:
    ps1 = out_dir / f"{base_zip_name}.join.ps1"
    final_zip = base_zip_name
    content = f'''# Łączy części {base_zip_name}.001, {base_zip_name}.002, ... w pełny ZIP.
# Uruchom w PowerShell w tym samym folderze co części:
#   powershell -ExecutionPolicy Bypass -File .\\{base_zip_name}.join.ps1

$ErrorActionPreference = "Stop"
$base = "{base_zip_name}"
$out = $base
$parts = Get-ChildItem -LiteralPath . -File | Where-Object {{ $_.Name -match [regex]::Escape($base) + '\\.\\d{{3}}$' }} | Sort-Object Name
if (-not $parts -or $parts.Count -eq 0) {{ throw "Brak części dla $base" }}
if (Test-Path -LiteralPath $out) {{ Remove-Item -LiteralPath $out -Force }}
$target = [System.IO.File]::Open($out, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
try {{
    foreach ($p in $parts) {{
        Write-Host "Dodaję $($p.Name)..."
        $src = [System.IO.File]::OpenRead($p.FullName)
        try {{ $src.CopyTo($target) }} finally {{ $src.Dispose() }}
    }}
}} finally {{
    $target.Dispose()
}}
Write-Host "Gotowe: $out"
Write-Host "Sprawdź SHA256 pełnego ZIP-a:"
Write-Host "  Get-FileHash .\\{final_zip} -Algorithm SHA256"
'''
    ps1.write_text(content, encoding="utf-8")


def create_split_zip(
    source_folder: Path,
    out_dir: Path,
    archive_basename: str,
    part_size_mb: int,
    compression_level: int,
    *,
    force: bool,
    include_empty_dirs: bool,
    exclude_patterns: list[str],
    append_version_to_name: bool = APPEND_VERSION_TO_NAME,
    version_file: str | Path | None = None,
) -> dict[str, object]:
    source_folder = source_folder.resolve()
    out_dir = out_dir.resolve()

    if not source_folder.exists() or not source_folder.is_dir():
        raise NotADirectoryError(f"Folder źródłowy nie istnieje albo nie jest folderem: {source_folder}")

    if is_relative_to(out_dir, source_folder):
        raise ValueError(
            "Folder wyjściowy nie może znajdować się wewnątrz folderu źródłowego, "
            "bo archiwum mogłoby zacząć pakować własne części. Ustaw --out poza folderem źródłowym."
        )

    resolved_version_file = find_version_file(source_folder, version_file)
    package_version = read_version_from_py(resolved_version_file)
    package_release_name = read_optional_string_from_py(resolved_version_file, RELEASE_NAME_VARIABLES)
    if not package_release_name:
        package_release_name = PACKAGE_RELEASE_NAME
    package_release_name = normalize_release_name(package_release_name)
    base_zip_name = apply_version_to_archive_name(
        archive_basename,
        package_version,
        package_release_name=package_release_name,
        enabled=append_version_to_name,
    )

    part_size = part_size_mb * 1024 * 1024
    files, dirs, source_total_size = discover_entries(source_folder, include_empty_dirs, exclude_patterns)

    writer = SplitPartWriter(out_dir, base_zip_name, part_size, force=force)
    source_hash_lines: list[str] = []
    added_files: list[dict[str, object]] = []

    compression = zipfile.ZIP_DEFLATED

    print(f"Źródło: {source_folder}")
    print(f"Wyjście: {out_dir}")
    print(f"Wersja z version.py: {package_version} ({resolved_version_file})")
    if package_release_name:
        print(f"Release z version.py: {package_release_name}")
    print(f"Nazwa: {base_zip_name}.001 ...")
    print(f"Rozmiar części: {part_size_mb} MiB")
    print(f"Plików: {len(files)}; katalogów: {len(dirs)}; rozmiar źródła: {human_size(source_total_size)}")
    print("Pakuję bez tworzenia pełnego ZIP-a na dysku...")

    try:
        with zipfile.ZipFile(
            writer,
            mode="w",
            compression=compression,
            allowZip64=True,
            compresslevel=compression_level,
            strict_timestamps=False,
        ) as zf:
            if include_empty_dirs:
                for d in dirs:
                    arc = rel_posix(d, source_folder).rstrip("/") + "/"
                    if arc == "./":
                        continue
                    zf.writestr(make_zipinfo_for_dir(d, arc), b"")

            for index, src in enumerate(files, start=1):
                arc = rel_posix(src, source_folder)
                file_hash = hashlib.sha256()
                size = src.stat().st_size
                zi = make_zipinfo_for_file(src, arc, compression, compression_level)

                with src.open("rb") as rf, zf.open(zi, mode="w", force_zip64=True) as wf:
                    while True:
                        chunk = rf.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        file_hash.update(chunk)
                        wf.write(chunk)

                digest = file_hash.hexdigest()
                source_hash_lines.append(f"{digest}  {arc}")
                added_files.append({"path": arc, "size_bytes": size, "sha256": digest})

                if index % 100 == 0 or index == len(files):
                    print(f"  dodano {index}/{len(files)} plików...")
    finally:
        writer.close()

    full_zip_sha = writer.full_hash.hexdigest()

    parts_sha_path = out_dir / f"{base_zip_name}.parts.sha256"
    parts_sha_path.write_text(
        "\n".join(f"{p['sha256']}  {p['filename']}" for p in writer.parts) + "\n",
        encoding="ascii",
    )

    full_sha_path = out_dir / f"{base_zip_name}.sha256"
    full_sha_path.write_text(f"{full_zip_sha}  {base_zip_name}\n", encoding="ascii")

    source_sha_path = out_dir / f"{base_zip_name}.source_files.sha256"
    source_sha_path.write_text("\n".join(source_hash_lines) + "\n", encoding="utf-8")

    write_join_script(out_dir, base_zip_name)

    manifest = {
        "created_at": now_iso(),
        "script": Path(__file__).name,
        "script_version": f"v{VERSION}",
        "package_version": package_version,
        "package_release_name": package_release_name,
        "version_file": str(resolved_version_file),
        "archive_basename_requested": archive_basename,
        "append_version_to_name": append_version_to_name,
        "source_folder": str(source_folder),
        "output_dir": str(out_dir),
        "archive_name_after_join": base_zip_name,
        "part_size_bytes": part_size,
        "part_size_human": human_size(part_size),
        "compression": "ZIP_DEFLATED",
        "compression_level": compression_level,
        "zip64_enabled": True,
        "multipart_zip_native": False,
        "split_method": "streamed_binary_split_of_one_valid_zip; join parts before extraction",
        "source_file_count": len(files),
        "source_dir_count": len(dirs),
        "source_total_size_bytes": source_total_size,
        "logical_full_zip_size_bytes": writer.total_written,
        "logical_full_zip_sha256": full_zip_sha,
        "parts_count": len(writer.parts),
        "parts": writer.parts,
        "exclude_patterns": exclude_patterns,
        "default_exclude_patterns": EXCLUDE_PATTERNS,
        "include_empty_dirs": include_empty_dirs,
        "source_hash_file": source_sha_path.name,
        "parts_hash_file": parts_sha_path.name,
        "full_zip_hash_file": full_sha_path.name,
        "join_script": f"{base_zip_name}.join.ps1",
    }

    manifest_path = out_dir / f"{base_zip_name}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\nGotowe.")
    print(f"Części: {len(writer.parts)}")
    print(f"Rozmiar logicznego ZIP-a: {human_size(writer.total_written)}")
    print(f"SHA256 pełnego ZIP-a: {full_zip_sha}")
    print(f"SHA części: {parts_sha_path}")
    print(f"SHA plików źródłowych: {source_sha_path}")
    print(f"Manifest: {manifest_path}")
    print(f"Skrypt łączenia: {out_dir / (base_zip_name + '.join.ps1')}")

    return manifest


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Spakuj folder do ZIP-a zapisywanego od razu w częściach .zip.001/.zip.002 z SHA256.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("source", nargs="?", help="Folder do spakowania")
    parser.add_argument("--out", help="Folder wyjściowy; domyślnie folder nadrzędny źródła")
    parser.add_argument("--name", help="Opcjonalna nazwa bazowa archiwum bez wersji, np. jazn_latka; jeśli pominiesz, użyte będzie jazn_latka_vX.Y.Z.zip")
    parser.add_argument("--version-file", default=VERSION_FILE or None, help="Ścieżka do version.py; domyślnie auto, najpierw .\\latka_jazn\\version.py")
    parser.add_argument("--no-version-suffix", action="store_true", help="Nie dopisuj automatycznie _v<wersja> do nazwy ZIP-a")
    parser.add_argument("--part-size-mb", type=int, default=PART_SIZE_MB, help="Rozmiar części w MiB")
    parser.add_argument("--compresslevel", type=int, default=COMPRESSION_LEVEL, choices=range(0, 10), metavar="0-9", help="Poziom kompresji ZIP_DEFLATED")
    parser.add_argument("--force", action="store_true", default=FORCE_OVERWRITE, help="Nadpisz istniejące pliki wyjściowe")
    parser.add_argument("--no-empty-dirs", action="store_true", help="Nie zapisuj pustych katalogów")
    parser.add_argument("--exclude", action="append", default=[], help="Dodatkowy wzorzec do pominięcia, np. docs/ albo memory/*; można podać wiele razy")
    parser.add_argument("--no-default-excludes", action="store_true", help="Nie używaj EXCLUDE_PATTERNS z sekcji ustawień domyślnych; zostaw tylko --exclude z CLI")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    source_raw = args.source or SOURCE_FOLDER
    if not source_raw:
        source_raw = input("Podaj folder do spakowania: ").strip().strip('"')

    source_folder = Path(source_raw)
    if not source_folder.exists():
        print(f"BŁĄD: folder nie istnieje: {source_folder}", file=sys.stderr)
        return 2

    out_dir = Path(args.out or OUTPUT_DIR or source_folder.resolve().parent)
    archive_basename = args.name or ARCHIVE_BASENAME or "jazn_latka"
    exclude_patterns = ([] if args.no_default_excludes else list(EXCLUDE_PATTERNS)) + list(args.exclude or [])

    try:
        create_split_zip(
            source_folder=source_folder,
            out_dir=out_dir,
            archive_basename=archive_basename,
            part_size_mb=args.part_size_mb,
            compression_level=args.compresslevel,
            force=bool(args.force),
            include_empty_dirs=not args.no_empty_dirs,
            exclude_patterns=exclude_patterns,
            append_version_to_name=not args.no_version_suffix,
            version_file=args.version_file,
        )
        return 0
    except KeyboardInterrupt:
        print("\nPrzerwano przez użytkownika.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
