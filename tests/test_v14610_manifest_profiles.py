from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]

def test_manifest_profiles_exist():
    p = ROOT/'latka_jazn/resources/package_manifest_profiles.json'
    data = json.loads(p.read_text(encoding='utf-8'))
    assert 'static_package' in data['profiles']
    assert 'runtime_dynamic' in data['profiles']
    assert 'memory_dynamic' in data['profiles']
