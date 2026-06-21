from __future__ import annotations
import json, re
from pathlib import Path

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"
SHORT = "v14.8.2.4"
PEP440 = "14.8.2.4"
CURRENT_CONTROL_FILES = [
    "VERSION.txt",
    "pyproject.toml",
    "latka_jazn/config.py",
    "main.py",
    "README.md",
    "START_CHATGPT_FROM_HERE.txt",
    "BOOTSTRAP_JAZN_CURRENT.json",
    "MANIFEST_CURRENT.json",
    "docs/update_history/INDEX.json",
    "docs/update_history/README.md",
    "latka_jazn/resources/package_manifest_profiles.json",
    "latka_jazn/tools/active_extraction_cache.py",
    "latka_jazn/resources/startup_contract_v14_8_2_4.json",
    "reports/VERSION_CONSISTENCY_AUDIT_V14_8_2_4.json",
]
FORBIDDEN_ACTIVE_OLD_MARKERS = [
    "v14.5.29-conversation-runtime",
    "v14.6.1.14-runtime-preview-source-origin",
    "v14.6.1.15-contextual-greeting-fallback-repair",
]

def test_current_control_files_use_current_version_or_pep440_project_version() -> None:
    root = Path(__file__).resolve().parents[1]
    for rel in CURRENT_CONTROL_FILES:
        text = (root / rel).read_text(encoding="utf-8")
        assert (VERSION in text) or (SHORT in text) or (PEP440 in text), rel
        if not rel.startswith("docs/update_history/"):
            for forbidden in FORBIDDEN_ACTIVE_OLD_MARKERS:
                assert forbidden not in text, rel

def test_pyproject_version_matches_current_package_lineage() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'^version = "14\.8\.2\.4"$', text, flags=re.MULTILINE)

def test_current_manifest_and_bootstrap_agree() -> None:
    root = Path(__file__).resolve().parents[1]
    bootstrap = json.loads((root / "BOOTSTRAP_JAZN_CURRENT.json").read_text(encoding="utf-8"))
    current = json.loads((root / "MANIFEST_CURRENT.json").read_text(encoding="utf-8"))
    audit = json.loads((root / "reports/VERSION_CONSISTENCY_AUDIT_V14_8_2_4.json").read_text(encoding="utf-8"))
    assert bootstrap["version"] == VERSION
    assert current["version"] == VERSION
    assert audit["active_version"] == VERSION
    assert bootstrap["start_file"] == current["start_file"] == "main.py"
