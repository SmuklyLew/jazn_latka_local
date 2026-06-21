from __future__ import annotations

from latka_jazn.nlp_reasoning.pipeline import PolishReasoningPipeline
from latka_jazn.nlp_reasoning.source_registry import PolishReasoningSourceRegistry
from latka_jazn.nlp_reasoning.response_variant_selector import choose_variant


def test_polish_reasoning_time_typo_normalization():
    frame = PolishReasoningPipeline(use_optional_providers=False).analyse("która jest godzina?")
    data = frame.to_dict()
    assert data["normalized_text"] == "która jest godzina?"
    assert data["semantic_frame"]["primary_intent"] == "current_time_question"
    assert data["semantic_frame"]["requires_time"] is True
    assert data["reply_policy"]["avoid_meta_commentary"] is True


def test_polish_reasoning_atmospheric_opening_policy():
    frame = PolishReasoningPipeline(use_optional_providers=False).analyse("Witaj w tej mrocznej nocy.")
    data = frame.to_dict()
    assert data["semantic_frame"]["primary_intent"] == "atmospheric_opening"
    assert "dark_atmospheric" in data["semantic_frame"]["tone"]
    assert data["reply_policy"]["allow_poetic_reply"] is True
    assert data["reply_policy"]["repeat_guard_key"] == "greeting_poetic_night"


def test_polish_reasoning_memory_followup_scope():
    frame = PolishReasoningPipeline(use_optional_providers=False).analyse("Ale z całego 2025 roku.")
    data = frame.to_dict()
    assert data["semantic_frame"]["primary_intent"] == "memory_experience_question"
    assert data["semantic_frame"]["requires_memory"] is True


def test_polish_reasoning_short_positive_feedback():
    frame = PolishReasoningPipeline(use_optional_providers=False).analyse("Super")
    data = frame.to_dict()
    assert data["semantic_frame"]["primary_intent"] == "positive_feedback_current_turn"
    assert data["semantic_frame"]["speech_act"] == "feedback"


def test_polish_reasoning_system_repair_and_exact_runtime_intents():
    pipeline = PolishReasoningPipeline(use_optional_providers=False)
    repair = pipeline.analyse("Sprawdź wszystko w systemie Jaźni, co nie działa i jak to naprawić.")
    exact = pipeline.analyse("Co dokładnie odpowiedział runtime?")
    assert repair.semantic_frame.primary_intent == "system_repair_plan_request"
    assert exact.semantic_frame.primary_intent == "runtime_exact_quote_request"


def test_polish_reasoning_source_registry_has_no_bulk_wsjp_mirror():
    registry = PolishReasoningSourceRegistry().to_dict()
    sources = registry["sources"]
    assert "morfeusz2-sgjp" in sources
    assert "wsjp-pan" in sources
    assert sources["wsjp-pan"]["allow_bulk_mirror"] is False
    assert "no_mass" in sources["wsjp-pan"]["redistribution"]
    assert registry["policy"]["large_data_outside_git"] is True


def test_response_variant_selector_avoids_recent_variant():
    first = choose_variant("greeting_poetic_night", "Witaj w tej mrocznej nocy.")
    second = choose_variant("greeting_poetic_night", "Witaj w tej mrocznej nocy.", recent_replies=[first])
    assert first != second
    assert "mrocz" in first.lower() or "noc" in first.lower()
