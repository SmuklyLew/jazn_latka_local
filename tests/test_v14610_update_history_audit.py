from pathlib import Path
import json
from latka_jazn.tools.update_history_audit import write_index_json, collect_manifest_files
ROOT = Path(__file__).resolve().parents[1]

def test_update_history_index_exists_and_covers_manifests():
    index_path = write_index_json(ROOT)
    data = json.loads(index_path.read_text(encoding='utf-8'))
    files = collect_manifest_files(ROOT)
    indexed = {e['path'] for e in data['entries']}
    assert index_path.exists()
    assert all(p.relative_to(ROOT).as_posix() in indexed for p in files)
    assert (ROOT/'MANIFEST_CURRENT.json').exists()
    assert not list(ROOT.glob('MANIFEST_V*.json'))
    assert not list(ROOT.glob('MANIFEST_v*.json'))
