from __future__ import annotations

from latka_jazn.core.clock import WarsawClock
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
