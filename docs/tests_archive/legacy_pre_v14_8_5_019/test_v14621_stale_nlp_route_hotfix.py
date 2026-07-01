from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.final_response_contract import FinalResponseContract
from latka_jazn.core.engine import JaznEngine
from latka_jazn.config import JaznConfig

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def test_version_and_active_sqlite_name_are_hotfix() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False)
    assert cfg.version == VERSION
    assert cfg.memory_db_path.name == "latka_jazn_v14_8_2.sqlite3"


def test_current_problem_does_not_route_to_legacy_nlp_update() -> None:
    decision = ConversationResponder().compose(
        '"Jedna ważna rzecz uczciwie: zwykłe wywołanie rozmowne nadal raz odpowiedziało zbyt ogólnym tropem o NLP/v14.6.1", więc co trzeba teraz zrobić?'
    )
    assert decision.route == "v14_6_2_1_stale_nlp_route_hotfix"
    assert decision.runtime_answer_quality == "topic_aligned"
    assert "v14.6.2.1" in decision.body
    assert "v14.6.1" in decision.body
    assert "stable" not in decision.body.lower()


def test_nlp_scope_question_routes_to_hotfix_scope_not_legacy_update() -> None:
    decision = ConversationResponder().compose(
        "A do aktualizacji NLP, co jest potrzebne? Może warto to rozbudować w hotfix, który zaraz będziesz robić?"
    )
    assert decision.route == "v14_6_2_1_nlp_safety_scope"
    assert decision.direct_answer_required is True
    assert "pełny ciężki model" in decision.body or "ciężki model" in decision.body
    assert "v14_6_1_nlp_adapter_update" not in decision.body


def test_explicit_legacy_nlp_request_can_still_use_legacy_route() -> None:
    decision = ConversationResponder().compose(
        "Przygotuj aktualizację v14.6.1 NLP, lematyzację i profile ZIP krok po kroku."
    )
    assert decision.route == "v14_6_1_nlp_adapter_update"
    assert decision.detected_user_intent == "explicit_legacy_nlp_update"


def test_final_contract_detects_stale_route_mismatch() -> None:
    contract = FinalResponseContract.build(
        turn_id="turn-test",
        trace_id="trace-test",
        runtime_version=VERSION,
        timestamp_header="[🕒 2026-05-17 23:30:00 GMT+0200, niedziela, Europe/Warsaw]",
        timezone="Europe/Warsaw",
        state_emoticon="🛠️",
        body="Tak — to jest właściwy bezpieczny krok dla v14.6.1. Utrzymać v14.6.1 jako stabilny fundament.",
        conversation_decision={"route": "v14_6_1_nlp_adapter_update"},
    )
    assert contract.fallback_classification == "stale_route_mismatch"
    assert contract.runtime_answer_quality == "stale_route_mismatch"
    assert contract.preservation_contract["must_report_fallback_classification"] is True


def test_runtime_preview_reports_hotfix_route_for_current_problem() -> None:
    root = Path(__file__).resolve().parents[1]
    engine = JaznEngine(JaznConfig(root=root, network_time_first=False))
    try:
        envelope = engine.process_turn(
            'Co trzeba teraz zrobić po zbyt ogólnym tropie o NLP/v14.6.1 w obecnej v14.6.2?',
            client_context={"client": "pytest_runtime_preview"},
        )
    finally:
        engine.shutdown()
    payload = envelope.to_dict()
    assert payload["runtime_version"] == VERSION
    contract = payload["final_response_contract"]
    assert contract["runtime_route"] == "v14_6_2_1_stale_nlp_route_hotfix"
    assert contract["runtime_answer_quality"] == "topic_aligned"
    assert contract["fallback_classification"] == "not_fallback"
