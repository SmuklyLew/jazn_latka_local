from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import main
from latka_jazn.version import PACKAGE_VERSION


def _envelope_dict(*, trusted: bool, source: str, present: bool = True) -> dict:
    integrity = {
        "valid": bool(trusted and present),
        "timestamp_present": present,
        "timestamp_source": source,
        "timestamp_trusted": trusted,
        "timestamp_freshness_ok": True,
    }
    return {
        "trace": {"timestamp_header": "[czas testowy]"},
        "final_visible_text": "[czas testowy] Odpowiedź testowa.",
        "final_response_contract": {
            "runtime_route": "runtime_health_check",
            "fallback_classification": "not_fallback",
            "runtime_answer_quality": "topic_aligned",
            "timestamp_source": source,
            "timestamp_trusted": trusted,
            "final_visible_integrity": integrity,
        },
        "cognitive_frame": {
            "dialogue_intent_classifier": {
                "primary_intent": "runtime_health_check",
                "diagnostic_request": True,
            },
        },
        "conversation_decision": {
            "detected_user_intent": "runtime_health_check",
            "selected_route": "runtime_health_check",
        },
    }


class _FakeEnvelope:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.final_visible_text = payload["final_visible_text"]
        self.final_response_contract = payload["final_response_contract"]

    def to_dict(self) -> dict:
        return dict(self._payload)


class _FakeEngine:
    payload = _envelope_dict(trusted=False, source="local_fallback")

    def __init__(self, config=None) -> None:
        self.config = SimpleNamespace(version=PACKAGE_VERSION, root=Path("/tmp/fake-jazn-root"))

    def process_turn(self, text: str, client_context: dict) -> _FakeEnvelope:
        return _FakeEnvelope(self.payload)

    def shutdown(self) -> None:
        return None


def _patch_runtime(monkeypatch, payload: dict) -> None:
    _FakeEngine.payload = payload
    monkeypatch.setattr(main, "JaznEngine", _FakeEngine)
    monkeypatch.setattr(main, "build_active_runtime_status", lambda root: {"active_root": str(root)})
    monkeypatch.setattr(main, "build_startup_summary", lambda cfg: {"runtime_version": cfg.version})
    monkeypatch.setattr(main, "visible_preview_contract_version", lambda root: "visible_preview_contract/test")


def test_runtime_preview_exposes_degraded_truth_gate(monkeypatch, capsys) -> None:
    _patch_runtime(monkeypatch, _envelope_dict(trusted=False, source="local_fallback"))

    assert main.main(["--runtime-preview", "Działasz?"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["runtime_truth_gate"]["active_state"] == "active_degraded"
    assert payload["runtime_truth_gate"]["ok"] is True
    assert payload["normal_response_blocked"] is False
    assert payload["runtime_response_status"] == "normal_response_allowed_degraded_timestamp"
    assert payload["final_visible_integrity_valid"] is False
    assert payload["timestamp_trusted"] is False


def test_dev_preview_contains_gate_and_updated_cognitive_envelope(monkeypatch, capsys) -> None:
    _patch_runtime(monkeypatch, _envelope_dict(trusted=False, source="local_fallback"))

    assert main.main(["--dev-preview", "Działasz?"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["runtime_truth_gate"]["active_state"] == "active_degraded"
    assert payload["normal_response_blocked"] is False
    assert payload["runtime_response_status"] == "normal_response_allowed_degraded_timestamp"
    assert payload["runtime_text"] == payload["final_visible_text"]
    assert payload["cognitive_turn_envelope"]["runtime_truth_gate"] == payload["runtime_truth_gate"]
    assert payload["cognitive_turn_envelope"]["runtime_response_status"] == payload["runtime_response_status"]


def test_direct_one_shot_prints_post_gate_visible_text(monkeypatch, capsys) -> None:
    raw_text = "[czas testowy] Tekst przed bramką."
    payload = _envelope_dict(trusted=False, source="local_fallback", present=False)
    payload["final_visible_text"] = raw_text
    _patch_runtime(monkeypatch, payload)

    assert main.main(["Działasz?"]) == 0
    output = capsys.readouterr().out

    assert raw_text not in output
    assert "brama prawdy runtime" in output
    assert "timestamp_missing" in output


def test_runtime_preview_keeps_trusted_timestamp_active(monkeypatch, capsys) -> None:
    _patch_runtime(monkeypatch, _envelope_dict(trusted=True, source="test_network_time"))

    assert main.main(["--runtime-preview", "Działasz?"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["runtime_truth_gate"]["active_state"] == "active_trusted"
    assert payload["runtime_truth_gate"]["ok"] is True
    assert payload["normal_response_blocked"] is False
    assert payload["runtime_response_status"] == "normal_response_allowed"
    assert payload["final_visible_integrity_valid"] is True
    assert payload["timestamp_trusted"] is True
