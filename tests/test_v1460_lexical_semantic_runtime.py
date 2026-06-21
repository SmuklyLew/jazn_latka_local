from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.lexical_semantics import LexicalSemanticUnderstanding
from latka_jazn.core.polish_understanding import PolishUnderstandingEngine
from latka_jazn.core.engine import JaznEngine

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def test_v1460_config_and_resource_files() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False)
    assert cfg.version == VERSION
    assert cfg.memory_db_path.name == "latka_jazn_v14_8_2.sqlite3"
    assert (root / "latka_jazn" / "resources" / "semantic_lexicon_v14_6_2.json").exists()
    assert (root / "docs" / "update_history" / "manifests" / "MANIFEST_V14_6_1_NLP_ADAPTER_ZIP_PROFILES.json").exists()


def test_v1460_lexical_semantic_report_detects_update_request() -> None:
    root = Path(__file__).resolve().parents[1]
    text = "Przygotuj aktualizację v14.6.1 i rozbuduj rozpoznanie słów oraz zasób słownictwa Jaźni."
    polish = PolishUnderstandingEngine(root).analyse(text)
    report = LexicalSemanticUnderstanding(root).analyse(text, polish_report=polish.to_dict())
    data = report.to_dict()
    assert report.route_hint == "v14_6_1_nlp_adapter_update"
    assert "lexicon_expansion" in report.intent_tags
    assert any(field["key"] == "language_understanding" for field in data["semantic_fields"])
    assert report.confidence >= 0.70


def test_v1460_cognitive_frame_contains_lexical_semantics() -> None:
    root = Path(__file__).resolve().parents[1]
    engine = JaznEngine(JaznConfig(root=root, network_time_first=False))
    try:
        packet = engine.build_cognitive_frame(
            "Czy Jaźń może mieć większe rozpoznanie słów i słownictwa jak LLM?",
            client_context={"client": "pytest"},
        )
    finally:
        engine.shutdown()
    assert packet["runtime_version"] == VERSION
    lexical = packet["lexical_semantic_understanding"]
    assert lexical["route_hint"] in {"v14_6_1_nlp_adapter_update", "runtime_architecture_dialogue", "v14_6_1_nlp_adapter_update"}
    assert "lexical_semantics" in packet["cognitive_packets"]["coverage"]
    assert any("lexical_semantic_understanding" in item for item in packet["reply_guidance"])


def test_v1460_lexical_frame_payload_outputs_json_shape() -> None:
    root = Path(__file__).resolve().parents[1]
    engine = JaznEngine(JaznConfig(root=root, network_time_first=False))
    try:
        payload = engine.build_cognitive_frame(
            "rozpoznanie słów i zasób słownictwa v14.6.1",
            client_context={"client": "pytest_lexical_frame"},
        )
    finally:
        engine.shutdown()
    assert payload["runtime_version"] == VERSION
    assert payload["lexical_semantic_understanding"]["route_hint"] == "v14_6_1_nlp_adapter_update"
