from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.core.final_response_contract import FinalResponseContract


def test_v14825_validator_does_not_treat_v14610_schema_as_v1461_legacy_route():
    validator = RuntimeAnswerValidator()
    body = (
        "Działam w aktywnym folderze runtime. Krótki health-check: "
        "runtime_version=v14.8.2.5-canonical-sharded-memory-bootstrap-code-contract, active_cache_version=v14.8.3, "
        "active_root=D:\\.AI\\latka_jazn_v14_8_3, start_file=main.py, active_database=memory/sqlite/chat_context.sqlite3, "
        "should_reuse_existing_extraction=True, cache_miss_reasons=[], "
        "raw_memory_status=raw_memory_startup_status/v14.6.10. "
        "To jest pytanie o stan działania po aktualizacji, nie polecenie wykonania nowej aktualizacji kodu. "
        "Granica prawdy: tryb --runtime-preview jest jednorazowy."
    )
    result = validator.validate(
        user_text="Sprawdź krótko, czy działasz po aktualizacji.",
        body=body,
        route="runtime_health_check_after_update",
        detected_intent="runtime_health_check_after_update",
    )
    assert not result.must_regenerate
    assert result.is_topic_aligned
    assert "dedicated_handler_body_preserved_and_direct" in result.checks


def test_v14825_final_contract_keeps_direct_handler_body_visible():
    body = (
        "Działam w aktywnym folderze runtime. Krótki health-check: "
        "runtime_version=v14.8.2.5-canonical-sharded-memory-bootstrap-code-contract, active_cache_version=v14.8.3, "
        "active_root=D:\\.AI\\latka_jazn_v14_8_3, active_database=memory/sqlite/chat_context.sqlite3, cache_miss_reasons=[]. "
        "Granica prawdy: runtime-preview jest jednorazowy."
    )
    contract = FinalResponseContract.build(
        turn_id="turn",
        trace_id="trace",
        runtime_version="v14.8.2.5-canonical-sharded-memory-bootstrap-code-contract",
        timestamp_header="[🕒 2026-06-12 04:46:27 GMT+2, piątek, Europe/Warsaw]",
        timezone="Europe/Warsaw",
        state_emoticon="🛠️",
        body=body,
        conversation_decision={
            "route": "runtime_health_check_after_update",
            "detected_user_intent": "runtime_health_check_after_update",
            "handler_name": "CapabilityStatusHandler",
            "handler_generation_mode": "handler_generated",
            "preserve_handler_body": True,
            "runtime_answer_quality": "topic_aligned",
        },
    )
    assert "Działam w aktywnym folderze runtime" in contract.final_visible_text
    assert "Nie będę przenosiła starej trasy" not in contract.final_visible_text
    assert contract.runtime_answer_quality == "topic_aligned"


def test_v14825_true_legacy_marker_still_detected():
    validator = RuntimeAnswerValidator()
    result = validator.validate(
        user_text="Sprawdź krótko, czy działasz po aktualizacji.",
        body="To jest odpowiedź z v14.6.1 i starej trasy positive_continuation.",
        route="runtime_health_check_after_update",
        detected_intent="runtime_health_check_after_update",
    )
    assert result.must_regenerate
