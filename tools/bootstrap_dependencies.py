#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from latka_jazn.core.runtime_status import display_path
from latka_jazn.memory.raw_archive import chat_archive_diagnostics, system_7z_executable


def _py7zr_available() -> bool:
    return importlib.util.find_spec("py7zr") is not None


def dependency_report(root: Path, *, install: bool = False) -> dict:
    before_py7zr = _py7zr_available()
    install_result: dict | None = None
    if install and not before_py7zr and not system_7z_executable():
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(root / "requirements.txt")],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        install_result = {
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        }
    diag = chat_archive_diagnostics(root)
    diag["chat_html_path"] = display_path(root, diag.get("chat_html_path"))
    diag["archive_path"] = display_path(root, diag.get("archive_path"))
    return {
        "root": ".",
        "py7zr_before": before_py7zr,
        "py7zr_after": _py7zr_available(),
        "system_7z": system_7z_executable(),
        "install_requested": install,
        "install_result": install_result,
        "raw_archive_diagnostics": diag,
        "next_step": "python tools/memory_repair.py --import-chat-html" if diag.get("archive_present") else "dodaj memory/raw/chat.html.7z albo memory/raw/chat.html",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprawdzenie/instalacja zależności potrzebnych do aktywacji chat.html.7z.")
    parser.add_argument("--root", default=str(ROOT), help="Katalog systemu Jaźni")
    parser.add_argument("--install", action="store_true", help="Jeżeli brakuje py7zr i systemowego 7z, uruchom pip install -r requirements.txt")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = dependency_report(root, install=args.install)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report.get("install_result") or report["install_result"]["returncode"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
