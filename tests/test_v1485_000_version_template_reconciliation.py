from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from latka_jazn.version import PACKAGE_VERSION, generation_mode, schema_version
from latka_jazn.config import JaznConfig
from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler
from latka_jazn.core.runtime_response_synthesizer import SCHEMA_VERSION as SYNTH_SCHEMA
from latka_jazn.nlp.dialogue_intent_classifier import SCHEMA_VERSION as CLASSIFIER_SCHEMA
from latka_jazn.tools import active_extraction_cache as active_cache

ROOT = Path(__file__).resolve().parents[1]


def test_version_single_source_of_truth_core_files() -> None:
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == PACKAGE_VERSION
    assert JaznConfig(root=ROOT, network_time_first=False).version == PACKAGE_VERSION
    assert active_cache.FALLBACK_PACKAGE_VERSION.startswith(PACKAGE_VERSION)
    assert active_cache.SCHEMA_VERSION.endswith(PACKAGE_VERSION)


def test_active_schema_versions_are_current() -> None:
    assert SYNTH_SCHEMA == schema_version("runtime_response_synthesizer")
    assert CLASSIFIER_SCHEMA == schema_version("dialogue_intent_classifier")
    result = OrdinaryDialogueHandler().handle("Dzień dobry", {"intent": "standalone_greeting"})
    assert result.generation_mode == generation_mode("ordinary_dialogue")
    assert result.source_origin_detail == schema_version("ordinary_dialogue_handler")


def test_legacy_literal_audit_has_no_active_runtime_blockers() -> None:
    proc = subprocess.run(
        [sys.executable, "tools/audit_legacy_literals_v1485.py", "--fail-on-active-runtime-blockers"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
