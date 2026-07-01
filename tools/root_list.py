#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
tools/root_list.py

Inventory / audit helper for the root folder of Łatka / Jaźń.

Run from repository root, for example:
  py -X utf8 .\tools\root_list.py --help
  py -X utf8 .\tools\root_list.py --mode all --csv

Reports are written to:
  .\docs\.root\list_from_<repo>_<YYYYMMDD>_<HHMMSS>_<mode>.txt

No external dependencies required.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

SPINNER_FRAMES = "|/-\\"


@dataclass(frozen=True)
class Entry:
    kind: str
    path: str
    size: str
    modified_utc: str


@dataclass(frozen=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str


def safe_print(text: str = "", *, end: str = "\n") -> None:
    try:
        print(text, end=end, flush=True)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"), end=end, flush=True)


def clean_name(value: str) -> str:
    value = value.strip() or "repo"
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return value.strip("._-") or "repo"


def progress_bar(done: int, total: int, width: int = 30) -> str:
    if total <= 0:
        filled = width
        percent = 100
    else:
        filled = max(0, min(width, int(width * done / total)))
        percent = max(0, min(100, int(100 * done / total)))
    return "█" * filled + "░" * (width - filled) + f" {percent:3d}%"


class Spinner:
    def __init__(self, message: str, enabled: bool = True) -> None:
        self.message = message
        self.enabled = enabled and sys.stdout.isatty()
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None

    def __enter__(self) -> "Spinner":
        if self.enabled:
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
        else:
            safe_print(self.message)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=1)
        if self.enabled:
            safe_print("\r" + " " * (len(self.message) + 8) + "\r", end="")

    def _run(self) -> None:
        idx = 0
        while not self.stop.is_set():
            safe_print(f"\r{SPINNER_FRAMES[idx % len(SPINNER_FRAMES)]} {self.message}", end="")
            idx += 1
            time.sleep(0.10)


def resolve_root(raw: str | None) -> Path:
    root = Path(raw or ".").expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"[ABORT] Root path is not a directory: {root}")
    return root


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def is_git_repo(root: Path) -> bool:
    return (root / ".git").is_dir()


def run_cmd(args: Sequence[str], cwd: Path, *, spinner: bool = True) -> CommandResult:
    msg = "Uruchamiam: " + " ".join(args)
    try:
        with Spinner(msg, spinner):
            proc = subprocess.run(
                list(args),
                cwd=str(cwd),
                shell=False,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        return CommandResult(list(args), proc.returncode, proc.stdout, proc.stderr)
    except FileNotFoundError as exc:
        return CommandResult(list(args), 127, "", f"Command not found: {args[0]} ({exc})")


def repo_name(root: Path) -> str:
    if is_git_repo(root):
        res = run_cmd(["git", "rev-parse", "--show-toplevel"], root, spinner=False)
        if res.returncode == 0 and res.stdout.strip():
            return clean_name(Path(res.stdout.strip()).name)
    return clean_name(root.name)


def ignored(rel_path: str, excludes: Sequence[str], include_git: bool) -> bool:
    norm = rel_path.replace("\\", "/")
    parts = set(norm.split("/"))
    if not include_git and ".git" in parts:
        return True
    for item in excludes:
        item = item.strip().replace("\\", "/")
        if not item:
            continue
        if norm == item or norm.startswith(item.rstrip("/") + "/") or item in parts:
            return True
    return False


def count_entries(root: Path, excludes: Sequence[str], include_git: bool) -> int:
    total = 0
    for current, dirs, files in os.walk(root, topdown=True):
        here = Path(current)
        kept: list[str] = []
        for d in dirs:
            if not ignored(rel(root, here / d), excludes, include_git):
                kept.append(d)
        dirs[:] = kept
        total += len(dirs)
        total += sum(1 for f in files if not ignored(rel(root, here / f), excludes, include_git))
    return total


def scan(root: Path, excludes: Sequence[str], include_git: bool, dirs_only: bool, animations: bool) -> list[Entry]:
    total = count_entries(root, excludes, include_git)
    entries: list[Entry] = []
    done = 0
    last_draw = 0.0
    safe_print(f"Skanuję folder root: {root}")

    for current, dirs, files in os.walk(root, topdown=True):
        here = Path(current)
        kept: list[str] = []
        for d in dirs:
            p = here / d
            if not ignored(rel(root, p), excludes, include_git):
                kept.append(d)
        dirs[:] = kept

        for d in dirs:
            p = here / d
            try:
                st = p.stat()
                mtime = dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat()
            except OSError:
                mtime = "ERROR"
            entries.append(Entry("DIR", rel(root, p), "", mtime))
            done += 1
            now = time.monotonic()
            if animations and sys.stdout.isatty() and now - last_draw > 0.05:
                safe_print("\r" + progress_bar(done, total) + f"  {done}/{total}", end="")
                last_draw = now

        if dirs_only:
            continue
        for f in files:
            p = here / f
            r = rel(root, p)
            if ignored(r, excludes, include_git):
                continue
            try:
                st = p.stat()
                size = str(st.st_size)
                mtime = dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat()
            except OSError:
                size = "ERROR"
                mtime = "ERROR"
            entries.append(Entry("FILE", r, size, mtime))
            done += 1
            now = time.monotonic()
            if animations and sys.stdout.isatty() and now - last_draw > 0.05:
                safe_print("\r" + progress_bar(done, total) + f"  {done}/{total}", end="")
                last_draw = now

    if animations and sys.stdout.isatty():
        safe_print("\r" + progress_bar(total, total) + f"  {total}/{total}")
    entries.sort(key=lambda e: (e.path.lower(), e.kind))
    safe_print(f"[OK] Zeskanowano wpisów: {len(entries)}")
    return entries


def out_path(root: Path, out_dir: str | None, mode: str) -> Path:
    date = dt.datetime.now().strftime("%Y%m%d")
    tm = dt.datetime.now().strftime("%H%M%S")
    base = Path(out_dir).expanduser().resolve() if out_dir else root / "docs" / ".root"
    return base / f"list_from_{repo_name(root)}_{date}_{tm}_{clean_name(mode)}.txt"


def header(root: Path, path: Path, mode: str, excludes: Sequence[str], include_git: bool) -> str:
    return "\n".join([
        "# ROOT LIST REPORT",
        "",
        f"generated_at: {dt.datetime.now().astimezone().isoformat()}",
        f"root: {root}",
        f"repo_name: {repo_name(root)}",
        f"mode: {mode}",
        f"output_file: {path}",
        f"include_git: {include_git}",
        "excludes: " + (", ".join(excludes) if excludes else "[none]"),
        "",
    ])


def entries_text(entries: Sequence[Entry], title: str) -> str:
    lines = [f"# {title}", "", f"entries: {len(entries)}", ""]
    for e in entries:
        if e.kind == "FILE":
            lines.append(f"FILE {e.path}\t{e.size}\t{e.modified_utc}")
        else:
            lines.append(f"DIR  {e.path}")
    return "\n".join(lines)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, entries: Sequence[Entry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["type", "path", "size_bytes", "last_write_utc"])
        for e in entries:
            writer.writerow([e.kind, e.path, e.size, e.modified_utc])


def git_report(root: Path, animations: bool) -> str:
    lines = ["# GIT STATUS / DIFF", ""]
    if not is_git_repo(root):
        lines.append("[WARN] Root does not contain .git. Git section skipped.")
        return "\n".join(lines)
    checks = [
        ["git", "status", "--short", "--branch", "--untracked-files=all"],
        ["git", "diff", "--name-status", "--find-renames"],
        ["git", "diff", "--cached", "--name-status", "--find-renames"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    for cmd in checks:
        res = run_cmd(cmd, root, spinner=animations)
        lines.append("## " + " ".join(cmd))
        lines.append(f"returncode: {res.returncode}")
        lines.append(res.stdout.rstrip() if res.stdout.strip() else "[empty]")
        if res.stderr.strip():
            lines.extend(["", "stderr:", res.stderr.rstrip()])
        lines.append("")
    return "\n".join(lines)


def snapshot_lines(entries: Sequence[Entry]) -> list[str]:
    return sorted(e.path for e in entries)


def compare_snapshots(before: Path, after: Path) -> str:
    b = set(before.read_text(encoding="utf-8", errors="replace").splitlines())
    a = set(after.read_text(encoding="utf-8", errors="replace").splitlines())
    added = sorted(a - b)
    removed = sorted(b - a)
    lines = ["# SNAPSHOT COMPARE", "", f"before: {before}", f"after: {after}", "", f"added: {len(added)}", f"removed: {len(removed)}", ""]
    lines.append("## ADDED")
    lines.extend(added if added else ["[none]"])
    lines.append("")
    lines.append("## REMOVED")
    lines.extend(removed if removed else ["[none]"])
    return "\n".join(lines)


MENU = """
tools/root_list.py — lista folderu root Jaźni

Wybierz akcję:
  1. Lista samych folderów
  2. Pełny inventory: pliki + foldery + rozmiary + daty
  3. Git status / diff / rename detection
  4. Wszystko: inventory + Git
  5. Snapshot BEFORE / przed przenoszeniem
  6. Snapshot AFTER / po przenoszeniu
  7. Porównaj dwa snapshoty
  8. Pokaż przykładowe komendy
  0. Wyjście
""".strip()


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def examples() -> None:
    safe_print(r"""
Przykłady:
  py -X utf8 .\tools\root_list.py --help
  py -X utf8 .\tools\root_list.py --mode all --csv
  py -X utf8 .\tools\root_list.py --mode dirs
  py -X utf8 .\tools\root_list.py --mode inventory --csv
  py -X utf8 .\tools\root_list.py --mode git
  py -X utf8 .\tools\root_list.py --mode snapshot --snapshot-name before
  py -X utf8 .\tools\root_list.py --mode snapshot --snapshot-name after
  py -X utf8 .\tools\root_list.py --mode compare --compare <before_file> <after_file>

Praktyczny audyt bez szumu lokalnego:
  py -X utf8 .\tools\root_list.py --mode all --csv --exclude .venv --exclude .pytest-tmp --exclude .pytest_cache --exclude __pycache__ --exclude workspace_runtime --exclude memory --exclude docs/.root
""".strip())


def run(args: argparse.Namespace) -> Path:
    root = resolve_root(args.root)
    animations = not args.no_animation
    output = out_path(root, args.out_dir, args.mode)
    chunks: list[str] = [header(root, output, args.mode, args.exclude, args.include_git)]

    if args.mode == "dirs":
        entries = scan(root, args.exclude, args.include_git, True, animations)
        chunks.append(entries_text(entries, "DIRECTORIES ONLY"))
    elif args.mode == "inventory":
        entries = scan(root, args.exclude, args.include_git, False, animations)
        chunks.append(entries_text(entries, "FULL INVENTORY"))
    elif args.mode == "git":
        chunks.append(git_report(root, animations))
        entries = []
    elif args.mode == "all":
        entries = scan(root, args.exclude, args.include_git, False, animations)
        chunks.append(entries_text(entries, "FULL INVENTORY"))
        chunks.append("\n" + git_report(root, animations))
    elif args.mode == "snapshot":
        entries = scan(root, args.exclude, args.include_git, False, animations)
        name = clean_name(args.snapshot_name)
        snap = output.parent / f"snapshot_{name}_from_{repo_name(root)}_{dt.datetime.now():%Y%m%d_%H%M%S}.txt"
        write_text(snap, "\n".join(snapshot_lines(entries)))
        chunks.extend(["# SNAPSHOT", "", f"snapshot_name: {name}", f"snapshot_file: {snap}", f"paths: {len(entries)}"])
    elif args.mode == "compare":
        if not args.compare or len(args.compare) != 2:
            raise SystemExit("[ABORT] --mode compare requires --compare BEFORE AFTER")
        chunks.append(compare_snapshots(Path(args.compare[0]).resolve(), Path(args.compare[1]).resolve()))
        entries = []
    else:
        raise SystemExit(f"[ABORT] Unknown mode: {args.mode}")

    if args.csv and args.mode in {"dirs", "inventory", "all"}:
        csv_path = output.with_suffix(".csv")
        write_csv(csv_path, entries)
        chunks.append(f"\nCSV: {csv_path}")

    write_text(output, "\n".join(chunks))
    safe_print(f"[OK] Zapisano raport: {output}")
    return output


def interactive(args: argparse.Namespace) -> None:
    while True:
        safe_print("\n" + MENU + "\n")
        choice = ask("Opcja", "4")
        if choice == "0":
            return
        if choice == "8":
            examples()
            continue
        mapping = {"1": "dirs", "2": "inventory", "3": "git", "4": "all", "5": "snapshot", "6": "snapshot", "7": "compare"}
        if choice not in mapping:
            safe_print("[WARN] Nieznana opcja.")
            continue
        args.mode = mapping[choice]
        if choice == "5":
            args.snapshot_name = ask("Nazwa snapshotu", "before")
        elif choice == "6":
            args.snapshot_name = ask("Nazwa snapshotu", "after")
        elif choice == "7":
            args.compare = [ask("Ścieżka do snapshotu BEFORE"), ask("Ścieżka do snapshotu AFTER")]
        run(args)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools/root_list.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Listuje root folderu Jaźni i zapisuje raporty do .\\docs\\.root\\.",
        epilog=r"""
Tryby:
  menu       Menu interaktywne.
  dirs       Lista samych folderów.
  inventory  Pełny inventory: FILE/DIR, ścieżka, rozmiar, last_write_utc.
  git        Git status, diff, cached diff, untracked files.
  all        Pełny inventory + Git.
  snapshot   Snapshot ścieżek przed/po ręcznym przenoszeniu.
  compare    Porównanie dwóch snapshotów.

Przykłady:
  py -X utf8 .\tools\root_list.py --mode all --csv
  py -X utf8 .\tools\root_list.py --mode snapshot --snapshot-name before
  py -X utf8 .\tools\root_list.py --mode snapshot --snapshot-name after
  py -X utf8 .\tools\root_list.py --mode compare --compare docs\.root\snapshot_before.txt docs\.root\snapshot_after.txt

Domyślnie pomijany jest folder .git.
Raporty trafiają do:
  .\docs\.root\list_from_<repo>_<YYYYMMDD>_<HHMMSS>_<mode>.txt
""".strip(),
    )
    p.add_argument("--root", default=".", help="Root repo/folderu Jaźni. Domyślnie bieżący folder.")
    p.add_argument("--out-dir", default=None, help="Folder wynikowy. Domyślnie: .\\docs\\.root\\")
    p.add_argument("--mode", choices=["menu", "dirs", "inventory", "git", "all", "snapshot", "compare"], default="menu")
    p.add_argument("--csv", action="store_true", help="Dla inventory/all/dirs zapisuje dodatkowo CSV obok TXT.")
    p.add_argument("--include-git", action="store_true", help="Nie pomijaj .git. Zwykle bardzo dużo plików.")
    p.add_argument("--exclude", action="append", default=[], help="Ścieżka/folder do pominięcia. Można podać wiele razy.")
    p.add_argument("--snapshot-name", default="snapshot", help="Nazwa snapshotu, np. before albo after.")
    p.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"), help="Dwa pliki snapshotów dla --mode compare.")
    p.add_argument("--no-animation", action="store_true", help="Wyłącza spinner/progress.")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.mode == "menu":
            interactive(args)
        else:
            run(args)
        return 0
    except KeyboardInterrupt:
        safe_print("\n[ABORT] Przerwano przez użytkownika.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
