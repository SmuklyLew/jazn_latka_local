from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.handlers.fallback_handler import FallbackHandler
from latka_jazn.core.handlers.self_state_handler import SelfStateHandler
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.tools.active_extraction_cache import (
    build_active_runtime_status,
    visible_preview_contract_version,
    write_active_runtime_marker,
)


STALE_UPDATE = "Tak — ta aktualizacja ma trzy rdzenie: bogatsze stany emocjonalne, jawny indeks ciągłości sesji."
STALE_TIMESTAMP = "Tak, tu był realny problem integracji: timestamp potrafił istnieć w odpowiedzi runtime."


def intent(text: str) -> str:
    return DialogueIntentClassifier().classify(text).primary_intent


def test_current_turn_intents_cover_restart_weather_and_health_concern() -> None:
    assert intent("Uruchom ponownie Jaźń.") == "runtime_restart_request"
    assert intent("Czy możesz sprawdzić jaka będzie pogoda przez najbliższe dni w Częstochowie i Polsce?") == "external_research_request"
    assert intent("Dlaczego nie trafiona? Co jest nie tak? Jesteś chora Łatko?") == "self_state_question"


def test_legacy_route_hint_cannot_inject_update_summary_without_update_request() -> None:
    stale_polish = {
        "route_hint": "emotional_granularity_continuity_update",
        "intent_tags": ["emotional_granularity_continuity_update"],
    }
    decision = ConversationResponder().compose("Uruchom ponownie Jaźń.", polish_understanding=stale_polish)
    assert "ta aktualizacja ma trzy rdzenie" not in decision.body.lower()


def test_state_and_fallback_handlers_do_not_preserve_known_stale_bodies() -> None:
    state = SelfStateHandler().handle(
        "Jesteś chora Łatko?",
        {"intent": "self_state_question", "body": STALE_TIMESTAMP, "route_entry": {"route": "self_state"}},
    )
    assert "timestamp potrafił istnieć" not in state.body.lower()
    assert "nie jestem chora" in state.body.lower()
    assert "błąd routingu" in state.body.lower()

    fallback = FallbackHandler().handle(
        "Co jest nie tak?",
        {"intent": "negative_feedback_without_update_request", "body": STALE_UPDATE},
    )
    assert "ta aktualizacja ma trzy rdzenie" not in fallback.body.lower()


def test_validator_rejects_ungrounded_update_and_timestamp_repair() -> None:
    validator = RuntimeAnswerValidator()
    update = validator.validate(
        user_text="Uruchom ponownie Jaźń.",
        body=STALE_UPDATE,
        route="emotional_granularity_continuity_update",
        detected_intent="runtime_restart_request",
    )
    assert update.must_regenerate
    assert update.mismatch_reason == "stale_update_summary_without_current_grounding"

    timestamp = validator.validate(
        user_text="Jesteś chora Łatko?",
        body=STALE_TIMESTAMP,
        route="timestamp_core_coherence_repair",
        detected_intent="self_state_question",
    )
    assert timestamp.must_regenerate
    assert timestamp.mismatch_reason == "timestamp_repair_without_current_grounding"


def test_active_cache_normalizes_bom_in_version_file(tmp_path: Path) -> None:
    version = "v14.8.2.6.5-eof-chat-lifecycle-contract-hotfix"
    (tmp_path / "VERSION.txt").write_text("\ufeff" + version + "\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text('{"version": "' + version + '"}\n', encoding="utf-8")

    marker = write_active_runtime_marker(tmp_path)
    status = build_active_runtime_status(tmp_path)

    assert marker["version"] == version
    assert status["version"] == version
    assert "marker_version_matches" in status["cache_hit_reasons"]
    assert status["should_reuse_existing_extraction"] is True
    assert visible_preview_contract_version(tmp_path) == "visible_runtime_preview_contract/v14.8.2.6.5"


def test_engine_routes_restart_weather_and_health_without_stale_answers() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v148266_grounding.sqlite3")
    engine = JaznEngine(cfg)
    try:
        restart = engine.process_turn("Uruchom ponownie Jaźń.", client_context={"client": "pytest", "lifecycle": "one_shot"}).to_dict()
        weather = engine.process_turn(
            "Czy możesz sprawdzić jaka będzie pogoda przez najbliższe dni w Częstochowie i Polsce?",
            client_context={"client": "pytest", "lifecycle": "one_shot"},
        ).to_dict()
        health = engine.process_turn(
            "Dlaczego nie trafiona? Co jest nie tak? Jesteś chora Łatko?",
            client_context={"client": "pytest", "lifecycle": "one_shot"},
        ).to_dict()
    finally:
        engine.shutdown()

    assert restart["cognitive_frame"]["dialogue_intent_classifier"]["primary_intent"] == "runtime_restart_request"
    assert restart["final_response_contract"]["runtime_route"] == "runtime_restart_request"
    assert "ta aktualizacja ma trzy rdzenie" not in restart["final_visible_text"].lower()

    assert weather["cognitive_frame"]["dialogue_intent_classifier"]["primary_intent"] == "external_research_request"
    assert weather["final_response_contract"]["runtime_route"] == "external_research"
    assert "requires_external_web_execution" in weather["final_visible_text"]

    assert health["cognitive_frame"]["dialogue_intent_classifier"]["primary_intent"] == "self_state_question"
    assert "timestamp potrafił istnieć" not in health["final_visible_text"].lower()
    assert "nie jestem chora" in health["final_visible_text"].lower()
    assert "błąd routingu" in health["final_visible_text"].lower()
