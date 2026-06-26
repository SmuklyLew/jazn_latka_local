from __future__ import annotations

from datetime import datetime, timezone

from latka_jazn.config import JaznConfig
from latka_jazn.core.clock import TimeSample, WarsawClock
from latka_jazn.core.final_response_contract import FinalResponseContract
from latka_jazn.core.timestamp_policy import timestamp_runtime_policy


def test_timestamp_policy_defaults_are_network_first() -> None:
    cfg = JaznConfig()
    policy = timestamp_runtime_policy()
    assert cfg.network_time_first is True
    assert cfg.network_time_allowed_in_normal_turn is True
    assert policy["network_first_default"] is True
    assert policy["network_time_in_normal_turn_default"] is True


def test_clock_header_without_sample_uses_network_time(monkeypatch) -> None:
    clock = WarsawClock("Europe/Warsaw")
    fixed = datetime(2026, 6, 26, 8, 15, 0, tzinfo=timezone.utc)

    def fake_network_time(*, timeout_seconds=1.5, urls_tried=None):
        return TimeSample(fixed, "test_network_time", True)

    monkeypatch.setattr(clock, "_network_time", fake_network_time)
    header = clock.header()
    assert "2026-06-26 10:15:00" in header
    assert clock.last_sample is not None
    assert clock.last_sample.trusted is True


def test_final_visible_integrity_rejects_untrusted_timestamp() -> None:
    header = "[🕒 2026-06-26 08:15:00 GMT+2, piątek, Europe/Warsaw]"
    contract = FinalResponseContract.build(
        turn_id="t",
        trace_id="tr",
        runtime_version="test",
        timestamp_header=header,
        timezone="Europe/Warsaw",
        state_emoticon="🌿",
        body="Test",
        conversation_decision={
            "timestamp_contract": {
                **timestamp_runtime_policy(),
                "source": "local_fallback",
                "trusted": False,
                "sample_iso": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    assert contract.final_visible_integrity is not None
    assert contract.final_visible_integrity["timestamp_present"] is True
    assert contract.final_visible_integrity["timestamp_trusted"] is False
    assert contract.final_visible_integrity["valid"] is False
