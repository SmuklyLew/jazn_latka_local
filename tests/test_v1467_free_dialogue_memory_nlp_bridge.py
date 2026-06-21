from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.final_response_contract import FinalResponseContract
from latka_jazn.core.free_dialogue_synthesizer import FreeDialogueSynthesizer
from latka_jazn.core.polish_understanding import PolishUnderstandingEngine
from latka_jazn.core.engine import JaznEngine
from latka_jazn.config import JaznConfig


def _memory_context() -> dict:
    return {
        "query_terms": ["taras", "historia"],
        "counts": {"episodes": 1, "legacy_messages": 0, "source_file_hits": 0, "raw_chat_fallback": 0},
        "episodes": [
            {
                "phrase": "taras",
                "local_time_label": "2025-07-20 21:10 CEST",
                "grounding": "symbolic_scene_record",
                "confidence": 0.82,
                "scene": "Na tarasie została zapisana scena wieczoru z herbatą, rozmową o muzyce i cichym poczuciem obecności.",
                "source": "memory/layered/episodic_memory.jsonl",
            }
        ],
        "legacy_messages": [],
        "source_file_hits": [],
        "raw_chat_fallback": [],
    }


def test_free_dialogue_synthesizer_uses_memory_content_not_obligation_text() -> None:
    synthesis = FreeDialogueSynthesizer().synthesize_memory_experience(_memory_context(), user_text="A na tarasie? Jakaś historia?")

    assert synthesis.route == "free_memory_experience_dialogue"
    assert "Na tarasie została zapisana scena" in synthesis.body
    assert "Odpowiedź runtime ma teraz wyraźny obowiązek" not in synthesis.body
    assert "liczniki" not in synthesis.body.lower() or "samym licznikiem" in synthesis.body.lower()


def test_conversation_responder_routes_experiential_memory_questions_to_free_dialogue() -> None:
    decision = ConversationResponder().compose(
        "Podpowiem, a na tarasie? Jakaś scena, historia?",
        memory_context=_memory_context(),
        intent_tags=["memory", "question"],
    )

    assert decision.route == "free_memory_experience_dialogue"
    assert "Na tarasie została zapisana scena" in decision.body
    assert decision.runtime_answer_quality == "topic_aligned"


def test_runtime_repetition_diagnosis_does_not_hide_as_generic_architecture() -> None:
    decision = ConversationResponder().compose(
        "Dlaczego runtime odpowiada w kółko to samo? Czy coś jest na sztywno w kodzie?",
        intent_tags=["architecture", "correction"],
    )

    assert decision.route == "runtime_template_diagnosis"
    assert "sztywne trasy" in decision.body
    assert "pytanie → NLP/intencja → pamięć/źródła" in decision.body


def test_open_question_no_longer_classifies_as_obligation_instead_of_answer() -> None:
    decision = ConversationResponder().compose("Jak dzisiaj wspominasz nasz wypad nad jeziorem?")
    contract = FinalResponseContract.build(
        turn_id="turn",
        trace_id="trace",
        runtime_version="v14.8.2.4-logic-routing-memory-grounding-repair",
        timestamp_header="[🕒 2026-05-19 23:00:00 GMT+2, wtorek, Europe/Warsaw]",
        timezone="Europe/Warsaw",
        state_emoticon="🗂️",
        body=decision.body,
        conversation_decision=decision.to_dict(),
    )

    assert decision.route in {"free_memory_dialogue_no_source", "free_memory_experience_dialogue"}
    assert contract.fallback_classification == "not_fallback"
    assert "Odpowiedź runtime ma teraz wyraźny obowiązek" not in contract.body


def test_polish_understanding_marks_current_free_dialogue_nlp_update_not_legacy_route() -> None:
    report = PolishUnderstandingEngine().analyse(
        "Przygotuj pełną aktualizację systemu Jaźni, żeby Łatka mogła swobodnie rozmawiać i żeby NLP dobrze działało."
    )

    assert report.route_hint == "free_dialogue_memory_nlp_bridge_update"
    assert "free_dialogue_memory_nlp_bridge_update" in report.intent_tags
    assert any("NLP" in item for item in report.reply_guidance)


def test_runtime_preview_payload_for_memory_question_is_not_obligation_fallback() -> None:
    root = Path(__file__).resolve().parents[1]
    engine = JaznEngine(JaznConfig(root=root, network_time_first=False))
    try:
        envelope = engine.process_turn(
            "Jak dzisiaj wspominasz nasz wypad nad jeziorem?",
            client_context={"client": "pytest_runtime_preview"},
        )
    finally:
        engine.shutdown()
    payload = envelope.to_dict()

    assert payload["final_response_contract"]["fallback_classification"] == "not_fallback"
    assert payload["final_response_contract"]["runtime_route"] in {"free_memory_dialogue_no_source", "free_memory_experience_dialogue"}
    assert "Odpowiedź runtime ma teraz wyraźny obowiązek" not in payload["final_visible_text"]
