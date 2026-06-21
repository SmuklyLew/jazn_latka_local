from __future__ import annotations

import builtins
from pathlib import Path

from latka_jazn.memory import raw_archive


def test_raw_archive_diagnostics_reports_present_archive_and_missing_extractor(tmp_path: Path, monkeypatch):
    archive = tmp_path / "memory" / "raw" / "chat.html.7z"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"not-a-real-7z")

    monkeypatch.setattr(raw_archive, "py7zr_available", lambda: False)
    monkeypatch.setattr(raw_archive, "system_7z_executable", lambda: None)

    diag = raw_archive.chat_archive_diagnostics(tmp_path)

    assert diag["archive_present"] is True
    assert diag["chat_html_present"] is False
    assert diag["py7zr_available"] is False
    assert diag["system_7z"] is None
    assert diag["can_unpack"] is False


def test_unpack_reports_missing_py7zr_when_archive_exists(tmp_path: Path, monkeypatch):
    archive = tmp_path / "memory" / "raw" / "chat.html.7z"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"not-a-real-7z")

    monkeypatch.setattr(raw_archive, "system_7z_executable", lambda: None)
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "py7zr":
            raise ModuleNotFoundError("No module named 'py7zr'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    report = raw_archive.unpack_chat_html_archive(tmp_path)

    assert report.status == "missing_py7zr"
    assert report.archive == str(archive)
    assert "py7zr" in (report.error or "")
    assert "pip install -r requirements.txt" not in (report.error or "")  # runtime status daje komendę; moduł zwraca przyczynę.
