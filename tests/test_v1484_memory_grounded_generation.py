from __future__ import annotations

from latka_jazn.core.memory_grounded_generation_bridge import (
    build_grounded_memory_items,
    enforce_memory_grounding,
    memory_allowed_for_generation,
)
from latka_jazn.core.model_context_compiler import extract_allowed_memory_items
from latka_jazn.core.nlg_plan import NlgPlan
from latka_jazn.core.response_candidate import ResponseCandidate


def _memory_plan() -> NlgPlan:
    return NlgPlan(
        schema_version="nlg_plan/v14.8.4.001",
        user_text="Co pamiętasz o spacerze?",
        detected_intent="self_memory_recall_request",
        route="memory_recall",
        speech_act="question",
        answer_kind="memory_grounded_answer",
        tone=["spokojny"],
        style_constraints=["bez zmyślania"],
        required_components=["grounded_memory_payload"],
        forbidden_components=["invented_memory"],
        memory_policy="required_grounded_payload",
        source_policy="runtime_plus_memory",
        model_policy="allowed_if_configured",
        truth_boundary="pamięć tylko z payloadu runtime",
        timestamp_required=True,
        max_length_hint="medium",
    )


def _ordinary_plan() -> NlgPlan:
    plan = _memory_plan()
    plan.memory_policy = "not_needed"
    plan.answer_kind = "natural_dialogue"
    return plan


def test_memory_allowed_for_generation_requires_grounded_policy() -> None:
    assert memory_allowed_for_generation(_memory_plan(), {"allow_memory_content": True}) is True
    assert memory_allowed_for_generation(_ordinary_plan(), {"allow_memory_content": True}) is False
    assert memory_allowed_for_generation(_memory_plan(), {"allow_memory_content": False}) is False


def test_build_grounded_memory_items_keeps_minimal_source_time_confidence() -> None:
    items = build_grounded_memory_items(
        {
            "items": [
                {
                    "item_id": "walk-1",
                    "content": "Spacer do Olsztyna i spokojna rozmowa o drodze.",
                    "source": "conversation_archive_v1",
                    "timestamp": "2025-07-01T12:00:00+02:00",
                    "confidence": 0.73,
                    "relevance_reason": "pasuje do pytania o spacer",
                }
            ]
        }
    )
    assert len(items) == 1
    assert items[0].item_id == "walk-1"
    assert items[0].source == "conversation_archive_v1"
    assert items[0].timestamp == "2025-07-01T12:00:00+02:00"
    assert items[0].confidence == 0.73
    assert "spacer" in items[0].excerpt.lower()


def test_model_context_extracts_memory_only_when_required() -> None:
    contract = {"items": [{"item_id": "m1", "content": "Konkretne wspomnienie.", "source": "runtime_memory"}]}
    assert extract_allowed_memory_items(contract, _ordinary_plan()) == []
    allowed = extract_allowed_memory_items(contract, _memory_plan())
    assert allowed == [
        {
            "item_id": "m1",
            "excerpt": "Konkretne wspomnienie.",
            "source": "runtime_memory",
            "timestamp": None,
            "confidence": 0.5,
            "relevance_reason": "grounded_memory_payload",
        }
    ]


def test_candidate_with_memory_claim_without_items_is_rejected() -> None:
    candidate = ResponseCandidate(
        "c1",
        "Pamiętam tamten spacer i mogę o nim opowiedzieć.",
        "model_adapter",
        "test",
        "test-model",
        "ok",
        [],
        "unit-test",
    )
    evaluation = enforce_memory_grounding(candidate, [])
    assert evaluation.accepted is False
    assert "memory_claim_without_grounded_items" in evaluation.violations


def test_candidate_declared_memory_id_must_match_payload() -> None:
    grounded = build_grounded_memory_items({"items": [{"item_id": "m1", "content": "Wspomnienie z payloadu.", "source": "runtime_memory"}]})
    good = ResponseCandidate("c2", "Mogę odnieść się do przekazanego wspomnienia.", "model_adapter", "test", "test-model", "ok", ["m1"], "unit-test")
    bad = ResponseCandidate("c3", "Mogę odnieść się do przekazanego wspomnienia.", "model_adapter", "test", "test-model", "ok", ["missing"], "unit-test")
    assert enforce_memory_grounding(good, grounded).accepted is True
    rejected = enforce_memory_grounding(bad, grounded)
    assert rejected.accepted is False
    assert "used_memory_id_not_in_grounded_payload" in rejected.violations


def test_candidate_memory_claim_with_payload_must_declare_used_ids() -> None:
    grounded = build_grounded_memory_items({"items": [{"item_id": "m1", "content": "Wspomnienie z payloadu.", "source": "runtime_memory"}]})
    candidate = ResponseCandidate("c4", "Pamiętam ten fragment z przekazanego payloadu.", "model_adapter", "test", "test-model", "ok", [], "unit-test")
    evaluation = enforce_memory_grounding(candidate, grounded)
    assert evaluation.accepted is False
    assert "model_memory_claim_without_declared_used_memory_ids" in evaluation.violations
