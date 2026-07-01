from __future__ import annotations

from pathlib import Path

import pytest

from latka_jazn.config import JaznConfig
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.core.session_provenance import validate_final_visible_integrity


SMOKE_TEXT = "Cześć, Łatko. Sprawdzam zwykłą rozmowę po v14.8.4.002."
STALE_TECH_BODY = (
    "Masz rację. Bezpośredni runtime nie może kończyć zwykłej rozmowy komunikatem diagnostycznym. "
    "Poprawny układ jest taki: normalna ścieżka odpowiada rozmownie jako Łatka, `--cognitive-frame` "
    "daje ChatGPT warstwę pamięciowo-poznawczą, a techniczny fallback zostaje tylko w trybie debugowania. "
    "To jest konkretna usterka do naprawy w domyślnym routingu, nie kwestia stylizacji."
)
TECH_MARKERS = (
    "--cognitive-frame",
    "techniczny fallback",
    "domyślnym routingu",
    "komunikatem diagnostycznym",
    "usterka do naprawy",
)


def assert_no_stale_technical_route(text: str) -> None:
    low = (text or "").lower()
    for marker in TECH_MARKERS:
        assert marker.lower() not in low


def test_conversation_responder_does_not_treat_smoke_dialogue_as_runtime_repair():
    decision = ConversationResponder().compose(SMOKE_TEXT, intent_tags=["dialogue_repair"])
    assert decision.route != "runtime_conversation_repair"
    assert_no_stale_technical_route(decision.body)


def test_ordinary_dialogue_handler_replaces_stale_runtime_repair_passthrough():
    result = OrdinaryDialogueHandler().handle(
        SMOKE_TEXT,
        {"intent": "ordinary_conversation", "body": STALE_TECH_BODY, "route_entry": {"route": "ordinary_dialogue"}},
    )
    assert result.body != STALE_TECH_BODY
    assert_no_stale_technical_route(result.body)


def test_validator_rejects_stale_runtime_repair_for_ordinary_dialogue():
    validation = RuntimeAnswerValidator().validate(
        user_text=SMOKE_TEXT,
        body=STALE_TECH_BODY,
        route="ordinary_dialogue",
        detected_intent="ordinary_conversation",
    )
    assert validation.must_regenerate
    assert validation.mismatch_reason == "ordinary_dialogue_meta_report_or_template"


def test_process_turn_smoke_dialogue_stays_conversational_after_v1484_002():
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v1484_ordinary_dialogue_stale_route.sqlite3")
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn(SMOKE_TEXT, client_context={"client": "pytest", "lifecycle": "one_shot"}).to_dict()
        final_text = envelope["final_visible_text"] or ""
        contract = envelope["final_response_contract"]
        assert contract["detected_user_intent"] == "ordinary_conversation"
        assert contract["runtime_route"] == "ordinary_dialogue"
        assert contract["fallback_classification"] == "not_fallback"
        assert contract["runtime_answer_quality"] in {"topic_aligned", "route_registry_dynamic"}
        assert_no_stale_technical_route(final_text)
    finally:
        engine.shutdown()


TIMESTAMP = "[🕒 2026-06-24 00:31:00 GMT+2, środa, Europe/Warsaw]"


def test_final_visible_integrity_allows_non_preserved_handler_repair_mismatch():
    body = "Cześć, jestem przy tej bieżącej rozmowie — bez raportu i bez starej trasy."
    final_text = f"{TIMESTAMP} 🌿\n{body}"
    payload = validate_final_visible_integrity(
        {
            "trace": {"timestamp_header": TIMESTAMP},
            "final_visible_text": final_text,
            "runtime_provenance": {
                "exact_runtime_text": body,
                "visible_answer_text": final_text,
            },
            "conversation_decision": {
                "preserve_handler_body": False,
                "handler_result": {"body": STALE_TECH_BODY},
            },
        }
    )
    assert payload["valid"] is True


def test_final_visible_integrity_still_rejects_preserved_handler_body_mismatch():
    body = "Dokładny tekst handlera powinien być zachowany."
    final_text = f"{TIMESTAMP} 🌿\n{body}"
    with pytest.raises(ValueError, match="handler_body_exact_runtime_text_mismatch"):
        validate_final_visible_integrity(
            {
                "trace": {"timestamp_header": TIMESTAMP},
                "final_visible_text": final_text,
                "runtime_provenance": {
                    "exact_runtime_text": body,
                    "visible_answer_text": final_text,
                },
                "conversation_decision": {
                    "preserve_handler_body": True,
                    "handler_result": {"body": STALE_TECH_BODY},
                },
            }
        )
