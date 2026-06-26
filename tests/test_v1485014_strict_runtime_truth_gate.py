from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from latka_jazn.config import JaznConfig
from latka_jazn.core.final_response_contract import FinalResponseContract
from latka_jazn.core.runtime_truth_gate import (
    apply_runtime_truth_gate,
    daemon_active_state,
    evaluate_final_response_contract,
)
from latka_jazn.core.timestamp_policy import timestamp_runtime_policy
from latka_jazn.core import chat_command_contract as chat_bridge


def _contract(*, trusted: bool, source: str) -> dict:
    header = "[🕒 2026-06-26 10:15:00 GMT+2, piątek, Europe/Warsaw]"
    sample_iso = datetime.now(timezone.utc).isoformat()
    return FinalResponseContract.build(
        turn_id="turn",
        trace_id="trace",
        runtime_version="test",
        timestamp_header=header,
        timezone="Europe/Warsaw",
        state_emoticon="🌿",
        body="Test zwykłej odpowiedzi.",
        conversation_decision={
            "timestamp_contract": {
                **timestamp_runtime_policy(),
                "timestamp_header": header,
                "source": source,
                "trusted": trusted,
                "sample_iso": sample_iso,
            }
        },
    ).to_dict()


def test_truth_gate_blocks_untrusted_local_timestamp() -> None:
    gate = evaluate_final_response_contract(_contract(trusted=False, source="local_fallback"))
    assert gate.ok is False
    assert gate.normal_response_allowed is False
    assert gate.error_code == "timestamp_network_unavailable"
    assert "timestamp_untrusted" in gate.errors
    assert "timestamp_source_not_network" in gate.errors


def test_truth_gate_allows_fresh_network_timestamp() -> None:
    gate = evaluate_final_response_contract(_contract(trusted=True, source="https://www.google.com/generate_204#http-date"))
    assert gate.ok is True
    assert gate.active_state == "active_trusted"
    assert gate.errors == []


def test_apply_truth_gate_replaces_visible_text_with_degraded_error() -> None:
    result = {
        "final_response_contract": _contract(trusted=False, source="local_fallback"),
        "final_visible_text": "normalna odpowiedź nie może przejść",
        "conversation_decision": {},
    }
    updated, payload = apply_runtime_truth_gate(result)
    assert payload["normal_response_allowed"] is False
    assert updated["ok"] is False
    assert updated["error_code"] == "timestamp_network_unavailable"
    assert updated["normal_response_blocked"] is True
    assert "czas lokalny niezweryfikowany" in updated["final_visible_text"]
    assert updated["blocked_final_visible_text"] == "normalna odpowiedź nie może przejść"


class _FakeSession:
    def __init__(self, *args, **kwargs):
        class State:
            session_id = "fake-session"
        self.state = State()

    def process_user_text(self, *args, **kwargs):
        return {
            "schema_version": "fake",
            "ok": False,
            "error_code": "timestamp_network_unavailable",
            "final_visible_text": "[czas lokalny niezweryfikowany] blocked",
        }

    def close(self):
        return None


def test_chat_bridge_does_not_overwrite_runtime_truth_gate_block(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(chat_bridge, "JaznRuntimeSession", _FakeSession)
    stdout = io.StringIO()
    rc = chat_bridge.run_jsonl_chat_bridge(
        config=JaznConfig(root=tmp_path),
        session_id="unit",
        no_carryover=True,
        command="--chat-gpt",
        stdin=io.StringIO('{"message":"hej"}\n'),
        stdout=stdout,
    )
    assert rc == 0
    payload = json.loads(stdout.getvalue())
    assert payload["ok"] is False
    assert payload["error_code"] == "timestamp_network_unavailable"


@pytest.mark.parametrize(
    "marker_found,pid_alive,ping_ok,timestamp_trusted,expected",
    [
        (False, False, False, None, "inactive"),
        (True, True, False, True, "inactive"),
        (True, True, True, False, "active_degraded"),
        (True, True, True, True, "active_trusted"),
    ],
)
def test_daemon_active_state_matrix(marker_found, pid_alive, ping_ok, timestamp_trusted, expected) -> None:
    assert daemon_active_state(marker_found=marker_found, pid_alive=pid_alive, ping_ok=ping_ok, timestamp_trusted=timestamp_trusted) == expected
