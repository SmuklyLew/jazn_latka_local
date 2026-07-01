from __future__ import annotations

from latka_jazn.core.chat_command_contract import (
    build_chatgpt_host_bridge_turn_contract,
    chatgpt_result_requires_host_visible_reply,
    extract_chatgpt_host_visible_reply_payload,
    is_chatgpt_host_visible_reply_payload,
)


def _runtime_result(*, requires_host: bool) -> dict:
    return {
        "trace": {
            "turn_id": "turn-1",
            "trace_id": "trace-1",
            "timestamp_header": "[🕒 2026-07-01 20:00:00 GMT+2, środa, Europe/Warsaw]",
        },
        "conversation_decision": {
            "route": "ordinary_dialogue",
            "handler_name": "RuntimeTurnTruthGate" if requires_host else "DirectLatkaVoiceHandler",
            "requires_host_model": requires_host,
            "response_generation_mode": "truthful_degraded" if requires_host else "handler_body",
        },
        "runtime_turn_contract": {
            "requires_host_model": requires_host,
            "fallback_classification": "cannot_answer_directly" if requires_host else "not_fallback",
            "runtime_answer_quality": "truthful_degraded_cannot_answer_directly" if requires_host else "topic_aligned",
            "can_generate_model_guided_speech": False,
        },
        "final_response_contract": {
            "fallback_classification": "cannot_answer_directly" if requires_host else "not_fallback",
        },
    }


def test_chatgpt_host_bridge_marks_runtime_turn_that_needs_host_visible_generation() -> None:
    result = _runtime_result(requires_host=True)

    assert chatgpt_result_requires_host_visible_reply(result) is True

    contract = build_chatgpt_host_bridge_turn_contract(
        result,
        user_text="Witam. Co tam słychać?",
        chat_bridge_meta={"command": "--chat-gpt", "client": "chatgpt_bridge"},
    )

    assert contract["phase"] == "host_visible_generation_requested"
    assert contract["host_must_generate_visible_reply"] is True
    assert contract["status"] == "requires_host_chatgpt_visible_response"
    assert contract["host_reply_jsonl_shape"]["type"] == "host_visible_reply"
    assert contract["host_reply_jsonl_shape"]["turn_id"] == "turn-1"
    assert contract["host_reply_jsonl_shape"]["trace_id"] == "trace-1"
    assert contract["truth_boundary"].startswith("--chat-gpt nie wywołuje lokalnie modelu ChatGPT")


def test_chatgpt_host_bridge_keeps_runtime_final_when_no_host_generation_needed() -> None:
    result = _runtime_result(requires_host=False)

    assert chatgpt_result_requires_host_visible_reply(result) is False

    contract = build_chatgpt_host_bridge_turn_contract(
        result,
        user_text="Chcę rozmawiać z Łatką.",
        chat_bridge_meta={"command": "--chat-gpt", "client": "chatgpt_bridge"},
    )

    assert contract["phase"] == "runtime_final_available"
    assert contract["host_must_generate_visible_reply"] is False
    assert contract["status"] == "runtime_final_visible_text_available"


def test_chatgpt_host_visible_reply_jsonl_is_detected_and_validated() -> None:
    payload = {
        "type": "host_visible_reply",
        "turn_id": "turn-1",
        "trace_id": "trace-1",
        "timestamp_header": "[🕒 2026-07-01 20:00:00 GMT+2, środa, Europe/Warsaw]",
        "final_text": "[🕒 2026-07-01 20:00:00 GMT+2, środa, Europe/Warsaw] 🌿\nCześć, jestem tu.",
    }

    assert is_chatgpt_host_visible_reply_payload(payload) is True
    extracted, missing = extract_chatgpt_host_visible_reply_payload(payload)

    assert missing == []
    assert extracted["final_text_field"] == "final_text"
    assert extracted["turn_id"] == "turn-1"
    assert extracted["trace_id"] == "trace-1"
    assert extracted["state_emoticon"] == "🌿"


def test_chatgpt_host_visible_reply_requires_trace_and_text() -> None:
    payload = {"type": "host_visible_reply", "final_text": "gotowe"}

    assert is_chatgpt_host_visible_reply_payload(payload) is True
    _, missing = extract_chatgpt_host_visible_reply_payload(payload)

    assert "turn_id" in missing
    assert "trace_id" in missing
    assert "timestamp_header" in missing
