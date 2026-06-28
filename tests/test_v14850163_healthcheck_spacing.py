from __future__ import annotations

from latka_jazn.core.final_response_contract import FinalResponseContract


def test_final_visible_healthcheck_keeps_spacing_after_timestamp_prefix() -> None:
    contract = FinalResponseContract.build(
        turn_id="turn-test",
        trace_id="trace-test",
        runtime_version="v14.8.5.016.3",
        timestamp_header="[czas testowy]",
        timezone="Europe/Warsaw",
        state_emoticon="🌿",
        body=(
            "Działam w aktywnym folderze runtime. "
            "Krótki raport health-check: runtime_version=v14.8.5.016.3, "
            "cache_miss_reasons=[]"
        ),
        conversation_decision={
            "route": "runtime_health_check",
            "runtime_answer_quality": "topic_aligned",
            "timestamp_contract": {"trusted": True},
        },
    )

    assert "Krótki raport health-check:" in contract.final_visible_text
    assert "Krótkihealth-check" not in contract.final_visible_text
    assert "Krótkiraport" not in contract.final_visible_text
    assert contract.final_visible_integrity is not None
    assert contract.final_visible_integrity["timestamp_present"] is True
