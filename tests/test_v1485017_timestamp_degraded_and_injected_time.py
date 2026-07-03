from __future__ import annotations

from datetime import datetime, timezone

from latka_jazn.core.clock import TimeSample, WarsawClock
from latka_jazn.core.final_response_contract import FinalResponseContract
from latka_jazn.core.runtime_truth_gate import evaluate_final_response_contract
from latka_jazn.core.timestamp_policy import timestamp_runtime_policy


def test_clock_accepts_injected_trusted_time_from_chatgpt_loader(monkeypatch) -> None:
    monkeypatch.setenv("JAZN_TRUSTED_TIME_ISO", "2026-06-28T15:59:22+02:00")
    monkeypatch.setenv("JAZN_TRUSTED_TIME_SOURCE", "chatgpt_web_time_tool")
    monkeypatch.setenv("JAZN_TRUSTED_TIME_MAX_AGE_SECONDS", "999999999")

    sample = WarsawClock().now(network_first=False)

    assert sample.trusted is True
    assert sample.source == "chatgpt_web_time_tool"
    assert sample.dt.isoformat().startswith("2026-06-28T15:59:22")


def test_clock_ignores_stale_injected_time_and_uses_network(monkeypatch) -> None:
    monkeypatch.setenv("JAZN_TRUSTED_TIME_ISO", "2020-01-01T00:00:00+01:00")
    monkeypatch.setenv("JAZN_TRUSTED_TIME_SOURCE", "chatgpt_web_time_tool")
    monkeypatch.setenv("JAZN_TRUSTED_TIME_MAX_AGE_SECONDS", "1")
    clock = WarsawClock()
    fixed = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)

    def fake_network_time(*, timeout_seconds=1.5, urls_tried=None):
        return TimeSample(fixed, "test_network_time", True)

    monkeypatch.setattr(clock, "_network_time", fake_network_time)

    sample = clock.now(network_first=True)

    assert sample.trusted is True
    assert sample.source == "test_network_time"
    assert sample.dt.astimezone(timezone.utc) == fixed


def test_clock_ignores_invalid_injected_time_and_uses_local_fallback(monkeypatch) -> None:
    monkeypatch.setenv("JAZN_TRUSTED_TIME_ISO", "not-a-date")
    monkeypatch.setenv("JAZN_TRUSTED_TIME_SOURCE", "chatgpt_web_time_tool")
    clock = WarsawClock()

    sample = clock.now(network_first=False)

    assert sample.trusted is False
    assert sample.source == "local_fallback"


def test_clock_sample_contract_propagates_injected_time_max_age(monkeypatch) -> None:
    monkeypatch.setenv("JAZN_TRUSTED_TIME_ISO", "2026-06-28T15:59:22+02:00")
    monkeypatch.setenv("JAZN_TRUSTED_TIME_SOURCE", "chatgpt_web_time_tool")
    monkeypatch.setenv("JAZN_TRUSTED_TIME_MAX_AGE_SECONDS", "999999999")

    clock = WarsawClock()
    sample = clock.now(network_first=False)
    contract = clock.sample_contract(sample)

    assert contract["max_age_seconds"] == 999999999
    assert contract["trusted"] is True
    assert contract["source"] == "chatgpt_web_time_tool"


def test_degraded_local_integrity_remains_strict_but_truth_gate_allows() -> None:
    header = "[🕒 2026-06-28 15:59:22 GMT+2, niedziela, Europe/Warsaw]"
    contract = FinalResponseContract.build(
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
                "source": "local_fallback",
                "trusted": False,
                "sample_iso": datetime.now(timezone.utc).isoformat(),
            }
        },
    ).to_dict()

    integrity = contract["final_visible_integrity"]
    assert integrity["timestamp_degraded_visible_ok"] is True
    assert integrity["valid"] is False

    gate = evaluate_final_response_contract(contract)

    assert gate.ok is True
    assert gate.normal_response_allowed is True
    assert gate.active_state == "active_trusted"
    assert gate.time_trust_state == "local_machine_unverified"
    assert gate.final_visible_integrity_valid is False
    assert "timestamp_untrusted" in gate.errors
    assert "timestamp_source_not_network" in gate.errors


def test_truth_gate_treats_injected_chatgpt_time_as_trusted_source() -> None:
    header = "[🕒 2026-06-28 15:59:22 GMT+2, niedziela, Europe/Warsaw]"
    contract = FinalResponseContract.build(
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
                "source": "chatgpt_web_time_tool",
                "trusted": True,
                "sample_iso": "2026-06-28T15:59:22+02:00",
                "max_age_seconds": 999999999,
            }
        },
    ).to_dict()

    gate = evaluate_final_response_contract(contract)

    assert gate.ok is True
    assert gate.normal_response_allowed is True
    assert gate.active_state == "active_trusted"
    assert gate.errors == []
