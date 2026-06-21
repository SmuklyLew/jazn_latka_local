from __future__ import annotations

import json
import subprocess
import sys


def _run(*args: str) -> dict:
    proc = subprocess.run([sys.executable, "main.py", *args], check=True, text=True, capture_output=True)
    return json.loads(proc.stdout)


def test_cli_polish_morphology_reports_selected_lemma_contract():
    payload = _run("--polish-morphology", "Która jest godzina?")
    morph = payload["polish_morphology"]
    assert payload["schema_version"] == "polish_morphology_diagnostics/v14.8.4"
    assert morph["normalized_text"] == "Która jest godzina?"
    assert morph["token_analyses"]
    assert "selected_lemma jest heurystyką" in payload["truth_boundary"]


def test_cli_morfeusz_status_never_pretends_provider_is_available():
    payload = _run("--morfeusz-status")
    status = payload["provider_status"]
    assert payload["schema_version"] == "polish_provider_status/v14.8.4"
    assert status["provider"] == "morfeusz2-sgjp"
    assert "available" in status
    assert "Status providera" in payload["truth_boundary"]


def test_cli_polimorf_status_mentions_external_data_or_available_path():
    payload = _run("--polimorf-status")
    status = payload["provider_status"]
    assert status["provider"] == "polimorf"
    assert status["mode"] in {"offline_recommended_external_data", "offline_external_data"}
    if not status["available"]:
        assert "LATKA_POLIMORF_PATH" in status["reason"]
