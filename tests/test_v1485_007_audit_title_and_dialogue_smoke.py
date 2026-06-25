from __future__ import annotations

from pathlib import Path

from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler
from latka_jazn.core.handlers.self_state_handler import SelfStateHandler
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.version import PACKAGE_VERSION, generation_mode, schema_version
from tools.audit_legacy_literals_v1485 import render_markdown

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_audit_markdown_heading_uses_current_target_version() -> None:
    report = {
        "schema_version": schema_version("legacy_literal_audit"),
        "target_version": PACKAGE_VERSION,
        "root": str(ROOT),
        "finding_count": 0,
        "blocker_count": 0,
        "findings": [],
        "blockers": [],
        "truth_boundary": "test truth boundary",
    }

    markdown = render_markdown(report)

    assert markdown.splitlines()[0] == f"# Legacy literal audit {PACKAGE_VERSION}"
    assert "v14.8.5.000" not in markdown.splitlines()[0]


def test_self_state_phrases_are_not_routed_as_generic_ordinary_conversation() -> None:
    classifier = DialogueIntentClassifier()

    for message in ("Jak się masz?", "Jak się miewasz?"):
        report = classifier.classify(message)
        assert report.primary_intent == "self_state_question"
        assert report.question_object == "self_state"
        assert report.schema_version == schema_version("dialogue_intent_classifier")


def test_ordinary_dialogue_handler_keeps_casual_turns_non_technical() -> None:
    handler = OrdinaryDialogueHandler()

    for message, intent in (
        ("Dzień dobry.", "standalone_greeting"),
        ("Co tam słychać?", "ordinary_conversation"),
    ):
        result = handler.handle(message, {"intent": intent})
        body = result.body

        assert result.generation_mode == generation_mode("ordinary_dialogue")
        assert result.source_origin_detail == schema_version("ordinary_dialogue_handler")
        assert body.strip()
        assert "cache_contract_version" not in body
        assert "MANIFEST_CURRENT" not in body
        assert "marker_refresh_required" not in body
        assert "Nie znalazłam osobnej trasy" not in body
        assert "runtime odebrał wiadomość" not in body


def test_self_state_handler_answers_jak_sie_miewasz_as_state_not_debug_report() -> None:
    classifier = DialogueIntentClassifier()
    report = classifier.classify("Jak się miewasz?")
    handler = SelfStateHandler()

    result = handler.handle("Jak się miewasz?", {"intent": report.primary_intent})
    body = result.body.lower()

    assert result.route == "self_state"
    assert result.intent == "self_state_question"
    assert result.generation_mode == generation_mode("self_state")
    assert result.source_origin_detail == schema_version("self_state_handler")
    assert "modelowany stan" in body
    assert "prawda:" in body
    assert "cache_contract_version" not in body
    assert "manifest_current" not in body
    assert "marker_refresh_required" not in body
