from __future__ import annotations

from pathlib import Path

import pytest

from latka_jazn.core.canon import canon_source_summary
from latka_jazn.core.handlers.canon_source_handler import CanonSourceHandler
from latka_jazn.core.route_handler_dispatcher import RouteHandlerDispatcher
from latka_jazn.core.route_registry import RouteRegistry
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier


@pytest.mark.parametrize(
    "text",
    [
        "Skąd bierzesz kanon Łatki?",
        "Z czego składa się kanon Łatki?",
        "Czy kanon jest z pamięci, JSON czy Python?",
        "Jakie są źródła kanonu Łatki?",
    ],
)
def test_canon_source_question_intent_has_priority_over_runtime_source(text: str) -> None:
    report = DialogueIntentClassifier().classify(text)
    assert report.primary_intent == "canon_source_question"
    assert report.question_object == "canon_source"


@pytest.mark.parametrize(
    "text",
    [
        "Skąd ta odpowiedź?",
        "Co runtime dokładnie odpowiedział?",
        "Czy to cytat runtime?",
        "Skąd bierzesz myśli?",
    ],
)
def test_runtime_source_questions_stay_runtime_source(text: str) -> None:
    report = DialogueIntentClassifier().classify(text)
    assert report.primary_intent in {"runtime_source_question", "runtime_exact_quote_request"}


def test_canon_source_route_registry_entry() -> None:
    entry = RouteRegistry().resolve("canon_source_question")
    assert entry.route == "canon_source"
    assert entry.handler_name == "CanonSourceHandler"
    assert "python_canon_modules" in entry.required_components
    assert "local_private_extension_boundary" in entry.required_components


def test_canon_source_summary_does_not_execute_local_private_extension(tmp_path: Path) -> None:
    canon_dir = tmp_path / "latka_jazn" / "core" / "canon"
    canon_dir.mkdir(parents=True)
    side_effect = tmp_path / "SIDE_EFFECT.txt"
    extension = canon_dir / "local_private_canon_extension.py"
    extension.write_text(
        "from pathlib import Path\n"
        f"Path({str(side_effect)!r}).write_text('executed', encoding='utf-8')\n"
        "LATKA_LOCAL_PRIVATE_CANON_EXTENSION = {'schema_version': 'test'}\n",
        encoding="utf-8",
    )

    summary = canon_source_summary(root=tmp_path)

    assert summary["local_private_extension_exists"] is True
    assert summary["local_private_extension_path"].endswith("local_private_canon_extension.py")
    assert not side_effect.exists()


def test_canon_source_handler_answers_with_canon_boundaries(tmp_path: Path) -> None:
    handler = CanonSourceHandler()
    result = handler.handle(
        "Skąd bierzesz kanon Łatki?",
        {"root": str(tmp_path), "intent": "canon_source_question"},
    )

    body = result.body
    assert result.handler_name == "CanonSourceHandler"
    assert result.route == "canon_source"
    assert "latka_jazn/core/canon" in body
    assert "source_controlled_python_canon_first" in body
    assert "resources/canon" in body
    assert "memory/raw" in body
    assert "reports/canon_extraction" in body
    assert "local_private_canon_extension.py" in body
    assert "nie stają" in body or "nie staja" in body or "recenz" in body.lower()


def test_dispatcher_uses_canon_source_handler() -> None:
    entry = RouteRegistry().resolve("canon_source_question")
    result = RouteHandlerDispatcher().dispatch(
        entry,
        "Skąd bierzesz kanon Łatki?",
        {"intent": "canon_source_question", "required_components": entry.required_components},
    )
    assert result.handler_name == "CanonSourceHandler"
    assert result.route == "canon_source"
    assert "latka_jazn/core/canon" in result.body


def test_runtime_answer_validator_accepts_canon_source_handler_body(tmp_path: Path) -> None:
    handler = CanonSourceHandler()
    result = handler.handle(
        "Skąd bierzesz kanon Łatki?",
        {"root": str(tmp_path), "intent": "canon_source_question"},
    )

    validation = RuntimeAnswerValidator().validate(
        user_text="Skąd bierzesz kanon Łatki?",
        body=result.body,
        route=result.route,
        detected_intent="canon_source_question",
    )

    assert validation.is_topic_aligned is True
    assert validation.must_regenerate is False
    assert validation.mismatch_reason is None


def test_canon_source_route_is_not_runtime_source() -> None:
    report = DialogueIntentClassifier().classify("Skąd bierzesz kanon Łatki?")
    entry = RouteRegistry().resolve(report.primary_intent, confidence=report.confidence)
    assert entry.route != "runtime_source"
    assert entry.handler_name != "RuntimeSourceHandler"
    assert entry.route == "canon_source"
    assert entry.handler_name == "CanonSourceHandler"
