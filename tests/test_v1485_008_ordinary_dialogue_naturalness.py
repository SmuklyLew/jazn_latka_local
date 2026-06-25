from __future__ import annotations

from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler
from latka_jazn.core.handlers.self_state_handler import SelfStateHandler
from latka_jazn.core.operational_self_model import OperationalSelfModel
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.version import PACKAGE_VERSION, generation_mode, schema_version

FORBIDDEN_NATURAL_TURN_MARKERS = (
    "cache_contract_version",
    "manifest_current",
    "marker_refresh_required",
    "nie znalazłam osobnej trasy",
    "runtime odebrał wiadomość",
    "techniczny fallback",
    "debugowy fallback",
    "raport diagnostyczny",
    "stale-route",
)


def _assert_natural(body: str) -> None:
    lowered = body.lower()
    assert body.strip()
    for marker in FORBIDDEN_NATURAL_TURN_MARKERS:
        assert marker not in lowered


def test_version_is_current_008_for_ordinary_dialogue_naturalness() -> None:
    assert PACKAGE_VERSION == "v14.8.5.008"


def test_co_tam_ok_and_dobranoc_are_warm_not_meta_reports() -> None:
    handler = OrdinaryDialogueHandler()

    samples = (
        ("Co tam słychać?", "ordinary_conversation"),
        ("ok", "ordinary_conversation"),
        ("Dobranoc", "sleep_closure_statement"),
    )
    for text, intent in samples:
        result = handler.handle(text, {"intent": intent})
        assert result.generation_mode == generation_mode("ordinary_dialogue")
        assert result.source_origin_detail == schema_version("ordinary_dialogue_handler")
        _assert_natural(result.body)

    assert "A u Ciebie jak leci?" in handler.handle("Co tam słychać?", {"intent": "ordinary_conversation"}).body
    assert "idziemy dalej spokojnie" in handler.handle("ok", {"intent": "ordinary_conversation"}).body
    assert "Dobranoc, Krzysztofie" in handler.handle("Dobranoc", {"intent": "sleep_closure_statement"}).body


def test_a_ty_and_jak_sie_miewasz_route_to_self_state_with_truth_boundary() -> None:
    classifier = DialogueIntentClassifier()
    handler = SelfStateHandler()

    for text, expected_intent in (
        ("A Ty?", "reciprocal_self_state_question"),
        ("Jak się miewasz?", "self_state_question"),
    ):
        report = classifier.classify(text)
        assert report.primary_intent == expected_intent
        result = handler.handle(text, {"intent": report.primary_intent})
        body = result.body.lower()

        assert result.generation_mode == generation_mode("self_state")
        assert result.source_origin_detail == schema_version("self_state_handler")
        assert "prawda:" in body
        assert "modelowany stan rozmowny runtime" in body
        _assert_natural(result.body)


def test_operational_self_model_schema_tracks_active_package_version() -> None:
    state = OperationalSelfModel().current_state(user_text="Jak się miewasz?").to_dict()

    assert state["schema_version"] == schema_version("operational_self_model")
    assert state["primary"]
    assert "biologiczne" in state["truth_boundary"]
