from pathlib import Path
from latka_jazn.tools.version_consistency_audit import scan_version_mentions
ROOT = Path(__file__).resolve().parents[1]
VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"

def test_active_version_files_are_consistent():
    assert (ROOT/'VERSION.txt').read_text(encoding='utf-8').strip() == VERSION
    assert 'version = "14.8.2.4"' in (ROOT/'pyproject.toml').read_text(encoding='utf-8')
    assert VERSION in (ROOT/'latka_jazn/__init__.py').read_text(encoding='utf-8')
    assert VERSION in (ROOT/'latka_jazn/config.py').read_text(encoding='utf-8')
    assert VERSION in (ROOT/'README.md').read_text(encoding='utf-8')
    assert VERSION in (ROOT/'START_CHATGPT_FROM_HERE.txt').read_text(encoding='utf-8')

def test_old_active_versions_are_not_active_outside_history():
    errors=[m for m in scan_version_mentions(ROOT) if m['classification']=='error']
    assert errors == []
