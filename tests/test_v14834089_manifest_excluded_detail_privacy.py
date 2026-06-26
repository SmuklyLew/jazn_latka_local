from __future__ import annotations

import json
from pathlib import Path

from tools.refresh_current_manifest import build


def test_manifest_does_not_record_git_or_cache_paths_in_excluded_details(tmp_path: Path) -> None:
    (tmp_path / "VERSION.txt").write_text("v14.8.3.4.089\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")

    git_log = tmp_path / ".git" / "logs" / "HEAD"
    git_log.parent.mkdir(parents=True)
    git_log.write_text("private git log\n", encoding="utf-8")

    pycache = tmp_path / "tests" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "test_dummy.pyc").write_bytes(b"pyc")

    manifest, _mutable = build(tmp_path)
    serialized = json.dumps(manifest, ensure_ascii=False)

    assert manifest["excluded_file_count"] >= 2
    assert manifest["excluded_file_detail_suppressed_count"] >= 2
    normalized = serialized.replace("\\", "/")

    assert ".git/logs/HEAD" not in normalized
    assert "private git log" not in normalized
    assert "tests/__pycache__" not in normalized
    assert "test_dummy.pyc" not in normalized
