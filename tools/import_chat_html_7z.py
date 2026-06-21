#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "memory" / "raw"
DEFAULT_ARCHIVE = RAW_DIR / "chat.html.7z"
DEFAULT_OUTPUT = RAW_DIR / "chat.html"
MANIFEST = ROOT / "memory" / "raw" / "CHAT_HTML_IMPORT_MANIFEST.json"


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_py7zr():
    try:
        import py7zr  # type: ignore
        return py7zr
    except Exception:
        subprocess.run([sys.executable, "-m", "pip", "install", "py7zr"], check=True)
        import py7zr  # type: ignore
        return py7zr


def extract_7z_archive(archive: Path, temp_dir: Path) -> str:
    """Rozpakowuje 7z najpierw przez lokalny program 7z/7za/7zr, potem przez py7zr.

    Dzięki temu importer działa również tam, gdzie pip nie ma internetu, ale system ma 7-Zip.
    """
    for exe in ("7z", "7za", "7zr"):
        path = shutil.which(exe)
        if path:
            subprocess.run([path, "x", str(archive), f"-o{temp_dir}", "-y"], check=True)
            return f"cli:{exe}"
    py7zr = ensure_py7zr()
    with py7zr.SevenZipFile(archive, "r") as z:
        z.extractall(temp_dir)
    return "python:py7zr"


def load_manifest() -> dict:
    if not MANIFEST.exists():
        return {}
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"previous_manifest_type": type(data).__name__, "previous_manifest_preserved": False}
    except Exception as exc:
        return {"previous_manifest_parse_error": repr(exc)}


def save_manifest(data: dict) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_chat_html(folder: Path) -> Path:
    exact = sorted(folder.rglob("chat.html"), key=lambda p: p.stat().st_size, reverse=True)
    if exact:
        return exact[0]
    html = sorted(folder.rglob("*.html"), key=lambda p: p.stat().st_size, reverse=True)
    if html:
        return html[0]
    raise FileNotFoundError("W archiwum nie znaleziono chat.html ani żadnego pliku .html.")


def import_archive(archive: Path = DEFAULT_ARCHIVE, output: Path = DEFAULT_OUTPUT, force: bool = False) -> dict:
    archive = archive.resolve()
    output = output.resolve()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if not archive.exists():
        raise FileNotFoundError(f"Nie znaleziono archiwum: {archive}")

    if output.exists() and not force:
        return {
            "status": "already_present",
            "message": "memory/raw/chat.html już istnieje. Użyj --force, żeby nadpisać.",
            "chat_html": str(output),
            "chat_html_size_bytes": output.stat().st_size,
        }

    temp_dir = RAW_DIR / "_chat_html_7z_extract_tmp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    try:
        extractor = extract_7z_archive(archive, temp_dir)

        found = find_chat_html(temp_dir)
        if output.exists():
            output.unlink()
        shutil.copy2(found, output)

        data = load_manifest()
        data.update({
            "raw_chat_html_present": True,
            "chat_html_path": "memory/raw/chat.html",
            "chat_html_size_bytes": output.stat().st_size,
            "chat_html_sha256": sha256_file(output),
            "source_archive_path": str(archive),
            "source_archive_name": archive.name,
            "source_archive_size_bytes": archive.stat().st_size,
            "source_archive_sha256": sha256_file(archive),
            "imported_at_unix": int(time.time()),
            "importer": "tools/import_chat_html_7z.py",
            "extractor": extractor,
            "note": "chat.html został lokalnie rozpakowany z chat.html.7z. Pełna paczka eksportowa zachowuje chat.html.7z i pomija rozpakowany chat.html, żeby nie dublować około 896 MB danych. RAW_MEMORY_MANIFEST.json pozostaje manifestem źródeł wersjonowanych i nie jest nadpisywany przez ten importer."
        })
        save_manifest(data)

        return {
            "status": "ok",
            "chat_html": str(output),
            "chat_html_size_bytes": output.stat().st_size,
            "manifest": str(MANIFEST),
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main(argv: list[str]) -> int:
    archive = DEFAULT_ARCHIVE
    force = False

    for arg in argv:
        if arg == "--force":
            force = True
        else:
            archive = Path(arg)

    try:
        result = import_archive(archive=archive, force=force)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": repr(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
