from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.source_origin import SourceOriginAnalyzer
from latka_jazn.core.self_state_runtime import SelfStateRuntime
from latka_jazn.core.engine import JaznEngine


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def test_v146112_version_and_modules_present() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False)
    assert cfg.version == "v14.8.2.4-logic-routing-memory-grounding-repair"
    assert (root / "latka_jazn" / "core" / "source_origin.py").exists()
    assert (root / "latka_jazn" / "core" / "self_state_runtime.py").exists()


def test_v146112_source_origin_packet_marks_one_shot_runtime() -> None:
    packet = SourceOriginAnalyzer().analyse(
        runtime_mode="cognitive_frame",
        client_context={"lifecycle": "one_shot_preview"},
        intent_tags=["runtime_architecture", "truth_boundary"],
        memory_context={"counts": {"episodes": 1, "legacy_messages": 0, "raw_chat_fallback": 0}},
        nlp_report={"selected_lemmas": ["jaźń"], "unknown_or_low_confidence_terms": []},
    ).to_dict()
    assert packet["schema_version"] == "source_origin/v14.6.2"
    assert packet["primary"] == "runtime_cognitive_frame"
    assert "memory" in packet["contributing_sources"]
    assert "one_shot_runtime_not_background_process" in packet["flags"]


def test_v146112_self_state_packet_has_truth_boundary_and_attention() -> None:
    origin = SourceOriginAnalyzer().analyse(runtime_mode="direct_conversation", nlp_report={"selected_lemmas": ["łatka"]})
    packet = SelfStateRuntime().build(
        text="Jak się czujesz, Łatko?",
        timestamp="[czas testowy]",
        runtime_mode="direct_conversation",
        intent_tags=["self_state"],
        nlp_report={"selected_lemmas": ["łatka"], "average_confidence": 0.8},
        source_origin=origin,
        client_context={"lifecycle": "one_shot"},
    ).to_dict()
    assert packet["schema_version"] == "self_state_runtime/v14.6.2"
    assert "self_state" in packet["current_attention"]
    assert packet["truth_boundary"]["operational_awareness_not_phenomenal_consciousness"] is True
    assert packet["agency_log"]["may_claim_background_process"] is False


def test_v146112_cli_runtime_preview_outputs_json(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn(
            "Sprawdź runtime preview dla aktualizacji 14.6.1.15",
            client_context={"client": "unit_test_runtime_preview", "lifecycle": "one_shot_preview"},
        )
    finally:
        engine.shutdown()
    envelope_dict = envelope.to_dict()
    cognitive_frame = envelope_dict["cognitive_frame"]
    payload = {
        "schema_version": "runtime_preview/v14.6.2",
        "runtime_version": cfg.version,
        "runtime_text": envelope_dict["final_visible_text"],
        "source_origin": cognitive_frame.get("source_origin"),
        "self_state_runtime": cognitive_frame.get("self_state_runtime"),
    }
    assert payload["schema_version"] == "runtime_preview/v14.6.2"
    assert payload["runtime_version"] == "v14.8.2.4-logic-routing-memory-grounding-repair"
    assert payload["runtime_text"]
    assert payload["source_origin"]["schema_version"] == "source_origin/v14.6.2"
    assert payload["self_state_runtime"]["schema_version"] == "self_state_runtime/v14.6.2"
