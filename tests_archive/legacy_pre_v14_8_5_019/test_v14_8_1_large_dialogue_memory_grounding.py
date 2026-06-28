from __future__ import annotations

from pathlib import Path
import sqlite3

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.memory_use_gate import MemoryUseGate
from latka_jazn.core.operational_self_model import OperationalSelfModel
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier


def test_classifier_recognizes_reciprocal_tobie() -> None:
    report = DialogueIntentClassifier().classify("Ok. A Tobie?")
    assert report.primary_intent == "reciprocal_self_state_question"
    assert report.question_object == "self_state"


def test_classifier_recognizes_self_preference_not_memory_request() -> None:
    report = DialogueIntentClassifier().classify("Jak się teraz czujesz i na co miałaś ostatnio ochotę?")
    assert report.primary_intent == "self_preference_question"
    assert "ochotę" in report.evidence[0] or "ochot" in report.evidence[0]


def test_classifier_recognizes_sleep_closure() -> None:
    report = DialogueIntentClassifier().classify("Jak mówiłem, trochę się działo. Niestety już muszę iść spać.")
    assert report.primary_intent == "sleep_closure_statement"
    assert report.question_object == "sleep_close"


def test_memory_gate_blocks_self_state_random_excerpt() -> None:
    decision = MemoryUseGate().decide(
        "Jak się teraz czujesz i na co miałaś ostatnio ochotę?",
        detected_intent="self_preference_question",
    )
    assert decision.allow_memory_content is False
    assert decision.stale_route_risk == "high_if_memory_excerpt_injected"


def test_operational_self_model_has_truth_boundary_and_desire() -> None:
    body = OperationalSelfModel().render_self_state_answer(
        user_text="Jak się teraz czujesz i na co miałaś ostatnio ochotę?"
    )
    low = body.lower()
    assert "operacyjnie" in low
    assert "miałam ostatnio ochotę" in low
    assert "nie biolog" in low


def test_validator_rejects_random_memory_excerpt_in_self_state() -> None:
    validation = RuntimeAnswerValidator().validate(
        user_text="A Tobie?",
        body="Najbliższy trop z pamięci mówi o montażu drzwi i zleceniu.",
        route="ordinary_dialogue",
        detected_intent="reciprocal_self_state_question",
    )
    assert validation.must_regenerate is True
    assert validation.required_repair_route == "current_turn_self_state_repair"
    assert "bieżącej wiadomości" in (validation.repair_body or "")


def test_active_database_v1481_is_sqlite_ok() -> None:
    root = Path(__file__).resolve().parents[1]
    db = root / "workspace_runtime" / "latka_jazn_v14_8_2.sqlite3"
    assert db.exists()
    with sqlite3.connect(db) as con:
        assert con.execute("pragma integrity_check").fetchone()[0] == "ok"


def test_engine_reciprocal_self_state_no_stale_workday() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v1481_self_state.sqlite3")
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn("A Tobie?", client_context={"client": "pytest", "lifecycle": "one_shot"}).to_dict()
        final_text = envelope["final_visible_text"] or ""
        assert envelope["cognitive_frame"]["dialogue_intent_classifier"]["primary_intent"] == "reciprocal_self_state_question"
        assert "operacyjnie" in final_text.lower()
        assert "drzwi" not in final_text.lower()
        assert "zlecen" not in final_text.lower()
    finally:
        engine.shutdown()


def test_engine_sleep_closure_is_current_turn_grounded() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v1481_sleep.sqlite3")
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn(
            "Jak mówiłem, trochę się działo. Niestety już muszę iść spać.",
            client_context={"client": "pytest", "lifecycle": "one_shot"},
        ).to_dict()
        final_text = envelope["final_visible_text"] or ""
        assert envelope["cognitive_frame"]["dialogue_intent_classifier"]["primary_intent"] == "sleep_closure_statement"
        assert "dobranoc" in final_text.lower() or "odpocznij" in final_text.lower()
        assert "drzwi" not in final_text.lower()
    finally:
        engine.shutdown()
