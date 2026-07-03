from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import main
from latka_jazn.version import PACKAGE_VERSION, PACKAGE_VERSION_FULL


def _fake_envelope_dict() -> dict:
    return {
        "trace": {"timestamp_header": "[czas testowy]"},
        "final_visible_text": "[czas testowy] Działam testowo.",
        "final_response_contract": {
            "runtime_route": "runtime_health_check_after_update",
            "fallback_classification": "not_fallback",
            "runtime_answer_quality": "topic_aligned",
            "final_visible_integrity": {
                "valid": True,
                "timestamp_present": True,
                "timestamp_source": "test_network_time",
                "timestamp_trusted": True,
                "timestamp_freshness_ok": True,
            },
        },
        "cognitive_frame": {
            "dialogue_intent_classifier": {
                "primary_intent": "runtime_health_check_after_update",
                "diagnostic_request": True,
            },
            "source_origin": {"schema_version": "source_origin/test"},
            "self_state_runtime": {"schema_version": "self_state_runtime/test"},
        },
        "conversation_decision": {
            "detected_user_intent": "runtime_health_check_after_update",
            "selected_route": "runtime_health_check_after_update",
        },
        "affect_mix": {},
        "dialogue_state": {},
        "normal_response_blocked": False,
        "runtime_response_status": "normal_response_allowed",
    }


class _FakeEnvelope:
    final_visible_text = "[czas testowy] Działam testowo."
    final_response_contract = _fake_envelope_dict()["final_response_contract"]

    def to_dict(self) -> dict:
        return _fake_envelope_dict()


class _FakeEngine:
    def __init__(self, config=None) -> None:
        self.config = SimpleNamespace(version=PACKAGE_VERSION, root=Path("/tmp/fake-jazn-root"))
        self.client_context = None

    def process_turn(self, text: str, client_context: dict) -> _FakeEnvelope:
        self.client_context = client_context
        return _FakeEnvelope()

    def shutdown(self) -> None:
        return None


def _patch_runtime(monkeypatch) -> None:
    monkeypatch.setattr(main, "JaznEngine", _FakeEngine)
    monkeypatch.setattr(main, "build_active_runtime_status", lambda root: {"active_root": str(root)})
    monkeypatch.setattr(main, "build_startup_summary", lambda cfg: {"runtime_version": cfg.version})
    monkeypatch.setattr(main, "visible_preview_contract_version", lambda root: "visible_preview_contract/test")


def test_runtime_preview_stdout_is_compact_not_full_cognitive_dump(monkeypatch, capsys) -> None:
    _patch_runtime(monkeypatch)

    assert main.main(["--runtime-preview", "Sprawdź krótko, czy działasz po aktualizacji."]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == f"runtime_preview_compact/{PACKAGE_VERSION_FULL}"
    assert payload["mode"] == "runtime_preview_compact_not_user_visible_latka_reply"
    assert payload["final_visible_text"] == "[czas testowy] Działam testowo."
    assert payload["runtime_route"] == "runtime_health_check_after_update"
    assert payload["primary_intent"] == "runtime_health_check_after_update"
    assert payload["diagnostic_request"] is True
    assert payload["runtime_truth_gate"]["active_state"] == "active_trusted"
    assert payload["runtime_truth_gate"]["ok"] is True
    assert payload["full_payload_written_to"] is None
    assert "cognitive_turn_envelope" not in payload
    assert "cognitive_frame" not in payload
    assert len(json.dumps(payload, ensure_ascii=False)) < 10_000


def test_runtime_preview_output_writes_full_payload_but_keeps_stdout_compact(monkeypatch, capsys, tmp_path: Path) -> None:
    _patch_runtime(monkeypatch)
    output_path = tmp_path / "runtime-preview-full.json"

    assert main.main([
        "--runtime-preview",
        "--runtime-preview-output",
        str(output_path),
        "Sprawdź krótko, czy działasz po aktualizacji.",
    ]) == 0
    stdout_payload = json.loads(capsys.readouterr().out)
    full_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert stdout_payload["schema_version"] == f"runtime_preview_compact/{PACKAGE_VERSION_FULL}"
    assert stdout_payload["full_payload_written_to"] == str(output_path)
    assert "cognitive_turn_envelope" not in stdout_payload
    assert "cognitive_frame" not in stdout_payload

    assert full_payload["schema_version"] == f"runtime_preview_full_payload/{PACKAGE_VERSION_FULL}"
    assert full_payload["mode"] == "diagnostic_dev_preview_full_payload_single_process_turn_not_background_daemon"
    assert "cognitive_turn_envelope" in full_payload
    assert "cognitive_frame" in full_payload
    assert full_payload["runtime_text"] == stdout_payload["final_visible_text"]


def test_dev_preview_is_explicit_full_payload_mode(monkeypatch, capsys) -> None:
    _patch_runtime(monkeypatch)

    assert main.main(["--dev-preview", "Sprawdź krótko, czy działasz po aktualizacji."]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == f"runtime_preview_full_payload/{PACKAGE_VERSION_FULL}"
    assert payload["mode"] == "diagnostic_dev_preview_full_payload_single_process_turn_not_background_daemon"
    assert "cognitive_turn_envelope" in payload
    assert "cognitive_frame" in payload
