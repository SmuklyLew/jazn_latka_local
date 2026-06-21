from __future__ import annotations

import sqlite3
from pathlib import Path

from latka_jazn.config import JaznConfig


def test_v14533_uses_current_primary_sqlite_and_download_safe_memory() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False)
    assert cfg.version == "v14.8.2.4-logic-routing-memory-grounding-repair"
    assert cfg.memory_db_path.name == "latka_jazn_v14_8_2.sqlite3"
    assert cfg.memory_db_path.exists()
    assert (root / "memory" / "raw" / "chat.html.7z").exists()
    assert not any(
        p.name != "latka_jazn_v14_8_2.sqlite3"
        for p in (root / "workspace_runtime").glob("latka_jazn_v14_5_*.sqlite3")
    )


def test_v14533_preserves_raw_archive_and_exact_ledgers() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "memory" / "raw" / "chat.html.7z").exists()
    assert (root / "memory" / "raw" / "runtime_events.jsonl").exists()
    assert (root / "memory" / "raw" / "conversation_turns.jsonl").exists()
    assert (root / "reports" / "PACKAGE_COMPLETENESS_AUDIT_V14_5_26.json").exists()


def test_v14533_sqlite_integrity_and_import_counts_are_present() -> None:
    root = Path(__file__).resolve().parents[1]
    db = root / "workspace_runtime" / "latka_jazn_v14_8_2.sqlite3"
    con = sqlite3.connect(db)
    try:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute("SELECT value FROM meta WHERE key='system_version'").fetchone()[0] == "v14.8.2.4-logic-routing-memory-grounding-repair"
        minimum_counts = {
            "legacy_messages": 10000,
            "episodic_memories": 700,
            "semantic_facts": 140,
            "procedural_rules": 120,
            "reflection_entries": 190,
            "truth_audits": 270,
        }
        for table, minimum in minimum_counts.items():
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert count >= minimum
    finally:
        con.close()


def test_v14533_export_full_skips_transient_sqlite_sidecars_and_expanded_chat(tmp_path: Path) -> None:
    import zipfile
    from latka_jazn.tools.package_export import export_package

    # Szybki test kontraktu eksportera na minimalnym drzewie: pełny eksport ma
    # zachować archiwum surowej pamięci, pominąć rozpakowany chat.html i nie
    # pakować transient sidecarów SQLite. Pełna paczka jest testowana osobno przez
    # integrację końcową, żeby stary test nie kompresował dużej pamięci przy każdej
    # baterii regresji.
    root = tmp_path / "mini_root"
    (root / "memory" / "raw").mkdir(parents=True)
    (root / "memory" / "layered").mkdir(parents=True)
    (root / "workspace_runtime").mkdir(parents=True)
    (root / "VERSION.txt").write_text("v14.8.2.4-logic-routing-memory-grounding-repair", encoding="utf-8")
    (root / "memory" / "raw" / "chat.html.7z").write_bytes(b"archive")
    (root / "memory" / "raw" / "chat.html").write_text("expanded chat must be skipped", encoding="utf-8")
    (root / "workspace_runtime" / "latka_jazn_v14_8_2.sqlite3").write_bytes(b"sqlite placeholder")
    (root / "workspace_runtime" / "latka_jazn_v14_8_0.sqlite3-wal").write_bytes(b"wal placeholder")
    (root / "workspace_runtime" / "latka_jazn_v14_8_0.sqlite3-shm").write_bytes(b"shm placeholder")
    out = tmp_path / "full.zip"

    report = export_package(root, "full", out)
    assert report.includes_memory is True
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    assert not any(name.endswith(("-wal", "-shm", ".sqlite3-wal", ".sqlite3-shm")) for name in names)
    assert "memory/raw/chat.html.7z" in names
    assert "memory/raw/chat.html" not in names
