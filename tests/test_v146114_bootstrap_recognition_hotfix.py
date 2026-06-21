from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.runtime_status import build_runtime_status

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def test_current_bootstrap_files_identify_latest_package() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION

    start = (root / "START_CHATGPT_FROM_HERE.txt").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    bootstrap = json.loads((root / "BOOTSTRAP_JAZN_CURRENT.json").read_text(encoding="utf-8"))
    current = json.loads((root / "MANIFEST_CURRENT.json").read_text(encoding="utf-8"))

    assert VERSION in start
    assert "v14.5.29-conversation-runtime" not in start
    assert VERSION in readme
    assert bootstrap["version"] == VERSION
    assert bootstrap["start_file"] == "main.py"
    assert current["version"] == VERSION
    assert current["start_file"] == "main.py"


def test_status_does_not_mark_missing_expanded_chat_as_critical_when_sqlite_is_indexed(tmp_path: Path) -> None:
    # Symuluje świeżo rozpakowany ZIP: jest chat.html.7z i indeks SQLite,
    # ale nie ma ciężkiego memory/raw/chat.html, bo pełna paczka go nie dubluje.
    raw = tmp_path / "memory" / "raw"
    raw.mkdir(parents=True)
    (raw / "chat.html.7z").write_bytes(b"fake-archive-marker-for-status-only")
    db = tmp_path / "workspace_runtime" / "latka_jazn_v14_8_2.sqlite3"
    db.parent.mkdir(parents=True)
    con = sqlite3.connect(db)
    try:
        con.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)")
        con.execute("CREATE TABLE legacy_messages(id INTEGER PRIMARY KEY)")
        con.execute("INSERT INTO meta(key,value) VALUES('chat_html_import_sha256','abc123')")
        con.execute("INSERT INTO legacy_messages(id) VALUES(1)")
        con.commit()
    finally:
        con.close()

    cfg = JaznConfig(root=tmp_path, network_time_first=False)
    status = build_runtime_status(cfg, store=None, readonly=True)
    assert "memory/raw/chat.html nie jest jeszcze aktywny" not in status
    assert "nie jest jeszcze rozpakowany ani zaindeksowany" not in status
    assert "brak krytycznych braków" in status
    assert "SQLite ma aktywny indeks surowej pamięci" in status
