#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_zip_sha.py

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

    py split_zip_sha.py "D:\\.AI\\jazn_v14.8.3.1" --part-size-mb 500

    py split_zip_sha.py "D:\\.AI\\jazn_latka_local" --out "D:\\Desktop\\pakiet" --name jazn_latka_14.8.4.006 --part-size-mb 480 --force

Konfiguracja bez argumentów CLI jest niżej w sekcji USTAWIENIA DOMYŚLNE.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import time
import zipfile
from typing import BinaryIO, Iterable

# =============================================================================
# USTAWIENIA DOMYŚLNE - możesz zmienić tutaj i uruchamiać skrypt bez argumentów
# =============================================================================

SOURCE_FOLDER = r""          # np. r"D:\.AI\latka_jazn_v14_8_2_work"
OUTPUT_DIR = r""             # puste = folder nadrzędny SOURCE_FOLDER
ARCHIVE_BASENAME = r""       # puste = nazwa folderu źródłowego; wynik: <nazwa>.zip.001
PART_SIZE_MB = 500            # rozmiar jednej części w MiB
COMPRESSION_LEVEL = 6         # 0-9 dla ZIP_DEFLATED; 0 szybciej/słabiej, 9 wolniej/mocniej
FORCE_OVERWRITE = False       # True = nadpisuje wcześniejsze części/manifesty
INCLUDE_EMPTY_DIRS = True      # zapisuje też puste katalogi
EXCLUDE_PATTERNS: list[str] = [
    # Przykłady, domyślnie wyłączone. Odkomentuj, jeśli chcesz pomijać:
    # ".git/*",
    # "__pycache__/*",
    # "*.pyc",
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
    rel = rel.replace("\\", "/")
    for pat in patterns:
        p = pat.strip().replace("\\", "/")
        if not p:
            continue
        if fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(Path(rel).name, p):
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
        self.current_hash: hashlib._Hash | None = None
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
    if hasattr(zi, "compress_level"):
        try:
            zi.compress_level = compresslevel  # type: ignore[attr-defined]
        except Exception:
            pass
    zi._compresslevel = compresslevel  # zgodne ze starszym zipfile
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

    if archive_basename.lower().endswith(".zip"):
        base_zip_name = archive_basename
    else:
        base_zip_name = f"{archive_basename}.zip"

    part_size = part_size_mb * 1024 * 1024
    files, dirs, source_total_size = discover_entries(source_folder, include_empty_dirs, exclude_patterns)

    writer = SplitPartWriter(out_dir, base_zip_name, part_size, force=force)
    source_hash_lines: list[str] = []
    added_files: list[dict[str, object]] = []

    compression = zipfile.ZIP_DEFLATED

    print(f"Źródło: {source_folder}")
    print(f"Wyjście: {out_dir}")
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
    parser.add_argument("--name", help="Nazwa bazowa archiwum, np. latka_jazn_v14_8_2_6_0 albo latka.zip")
    parser.add_argument("--part-size-mb", type=int, default=PART_SIZE_MB, help="Rozmiar części w MiB")
    parser.add_argument("--compresslevel", type=int, default=COMPRESSION_LEVEL, choices=range(0, 10), metavar="0-9", help="Poziom kompresji ZIP_DEFLATED")
    parser.add_argument("--force", action="store_true", default=FORCE_OVERWRITE, help="Nadpisz istniejące pliki wyjściowe")
    parser.add_argument("--no-empty-dirs", action="store_true", help="Nie zapisuj pustych katalogów")
    parser.add_argument("--exclude", action="append", default=[], help="Wzorzec do pominięcia, np. .git/*; można podać wiele razy")
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
    archive_basename = args.name or ARCHIVE_BASENAME or source_folder.resolve().name
    exclude_patterns = list(EXCLUDE_PATTERNS) + list(args.exclude or [])

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
