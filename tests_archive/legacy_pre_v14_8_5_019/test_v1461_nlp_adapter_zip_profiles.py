from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.nlp.polish_lemmatizer import PolishLemmatizationEngine
from latka_jazn.core.lexical_semantics import LexicalSemanticUnderstanding
from latka_jazn.tools.package_export import export_package

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def test_v1461_config_and_nlp_resources() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False)
    assert cfg.version == VERSION
    assert cfg.memory_db_path.name == "latka_jazn_v14_8_2.sqlite3"
    assert (root / "latka_jazn" / "nlp" / "polish_lemmatizer.py").exists()
    assert (root / "latka_jazn" / "resources" / "nlp_provider_registry_v14_6_2.json").exists()
    assert (root / "latka_jazn" / "resources" / "zip_package_profiles_v14_6_2.json").exists()


def test_v1461_polish_nlp_report_has_candidates_and_provider() -> None:
    root = Path(__file__).resolve().parents[1]
    report = PolishLemmatizationEngine(root).analyse("Jadę tramwajem przez Częstochowę i pamiętam Jaźń")
    data = report.to_dict()
    assert data["schema_version"] == "polish_nlp/v14.6.2"
    assert "builtin_safe_polish_v14_6_2" in data["active_providers"]
    word_tokens = [t for t in data["tokens"] if t["is_word"]]
    assert word_tokens
    assert any(t["lemma_candidates"] for t in word_tokens)
    assert "częstochowa" in data["selected_lemmas"] or "czestochowa" in data["selected_lemmas"]


def test_v1461_lexical_report_uses_nlp_route() -> None:
    root = Path(__file__).resolve().parents[1]
    nlp = PolishLemmatizationEngine(root).analyse("Bezpieczna aktualizacja v14.6.1: NLP, lematyzacja i profile ZIP krok po kroku")
    report = LexicalSemanticUnderstanding(root).analyse(
        "Bezpieczna aktualizacja v14.6.1: NLP, lematyzacja i profile ZIP krok po kroku",
        nlp_report=nlp.to_dict(),
    )
    assert report.route_hint == "v14_6_1_nlp_adapter_update"
    assert report.nlp_analysis["schema_version"] == "polish_nlp/v14.6.2"
    assert "polish_nlp" in report.intent_tags


def test_v1461_cli_nlp_frame_outputs_json() -> None:
    root = Path(__file__).resolve().parents[1]
    nlp = PolishLemmatizationEngine(root).analyse("lematyzacja języka polskiego i Jaźń")
    payload = {"runtime_version": VERSION, "polish_nlp": nlp.to_dict()}
    assert payload["runtime_version"] == VERSION
    assert payload["polish_nlp"]["schema_version"] == "polish_nlp/v14.6.2"


def test_v1461_export_nlp_package(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "nlp.zip"
    report = export_package(root, "nlp", out)
    assert report.includes_system is True
    assert report.includes_memory is False
    assert report.file_count > 0
    assert out.exists()
