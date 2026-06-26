from __future__ import annotations

import json

from latka_jazn.core.model_context_compiler import (
    ModelContextPacket,
    build_forbidden_claims,
    compile_model_context,
    extract_allowed_memory_items,
)
from latka_jazn.core.nlg_planner import build_nlg_plan
from latka_jazn.core.operational_thought_frame import build_operational_thought_frame


def _ordinary_plan():
    return build_nlg_plan(
        user_text="Cześć, porozmawiajmy chwilę.",
        cognitive_frame={"memory_gate": "not_needed"},
        response_policy={"answer_kind": "natural_dialogue"},
        route="ordinary_dialogue",
        detected_intent="ordinary_conversation",
        model_adapter_status={"status": "not_configured"},
    )


def test_compile_model_context_for_ordinary_dialogue_has_no_memory_items():
    plan = _ordinary_plan()
    thought = build_operational_thought_frame(
        user_text="Cześć, porozmawiajmy chwilę.",
        nlg_plan=plan,
        cognitive_frame={"memory_gate": "not_needed"},
        response_policy={},
    )
    packet = compile_model_context(
        user_text="Cześć, porozmawiajmy chwilę.",
        cognitive_frame={
            "memory_gate": "not_needed",
            "memory_recall_contract": {"items": [{"id": "m1", "excerpt": "nie powinno trafić do modelu"}]},
            "voice_source_contract": {"active_source": "jazn_runtime", "biological_claims_allowed": False},
        },
        nlg_plan=plan,
        thought_frame=thought,
        response_policy={},
    )
    assert isinstance(packet, ModelContextPacket)
    assert packet.allowed_memory_items == []
    assert "Nie dodawaj timestampu; timestamp jest odpowiedzialnością runtime." in packet.output_instructions


def test_compile_model_context_for_memory_request_requires_sources():
    plan = build_nlg_plan(
        user_text="Co pamiętasz o naszym spacerze?",
        cognitive_frame={"semantic_frame": {"requires_memory": True}},
        response_policy={"source_grounding_required": True},
        route="memory_recall",
        detected_intent="memory_recall_request",
        model_adapter_status={"status": "configured"},
    )
    items = extract_allowed_memory_items(
        {
            "items": [
                {
                    "item_id": "walk-1",
                    "excerpt": "Spacer był spokojny i związany z rozmową.",
                    "source": "runtime_memory",
                    "timestamp": "2025-07-01T12:00:00+02:00",
                    "confidence": 0.87,
                    "relevance_reason": "użytkownik pyta o spacer",
                    "raw_sqlite_row": "NIE WOLNO PRZEKAZAĆ",
                }
            ]
        },
        plan,
    )
    assert items == [
        {
            "item_id": "walk-1",
            "excerpt": "Spacer był spokojny i związany z rozmową.",
            "source": "runtime_memory",
            "timestamp": "2025-07-01T12:00:00+02:00",
            "confidence": 0.87,
            "relevance_reason": "użytkownik pyta o spacer",
        }
    ]


def test_model_context_contains_forbidden_biological_claims():
    plan = _ordinary_plan()
    forbidden = build_forbidden_claims(plan, {"biological_claims_allowed": False, "background_process_claim_allowed": False})
    assert "biological_consciousness_claim" in forbidden
    assert "persistent_background_process_claim" in forbidden
    assert "model_as_identity_source" in forbidden


def test_model_context_does_not_include_raw_sqlite_or_full_archive_payloads():
    plan = build_nlg_plan(
        user_text="Przypomnij mi coś z pamięci.",
        cognitive_frame={"semantic_frame": {"requires_memory": True}},
        response_policy={"source_grounding_required": True},
        route="memory_recall",
        detected_intent="memory_recall_request",
        model_adapter_status={"status": "configured"},
    )
    thought = build_operational_thought_frame(user_text="Przypomnij mi coś z pamięci.", nlg_plan=plan, cognitive_frame={}, response_policy={})
    packet = compile_model_context(
        user_text="Przypomnij mi coś z pamięci.",
        cognitive_frame={
            "voice_source_contract": {"active_source": "jazn_runtime"},
            "memory_recall_contract": {
                "items": [
                    {
                        "id": "m2",
                        "excerpt": "Krótki, dozwolony wycinek pamięci.",
                        "source": "episodic_memories",
                        "raw_sqlite_dump": "SECRET_RAW_SQLITE",
                        "full_archive_blob": "SECRET_FULL_ARCHIVE",
                    }
                ]
            },
        },
        nlg_plan=plan,
        thought_frame=thought,
        response_policy={},
    )
    dumped = json.dumps(packet.to_dict(), ensure_ascii=False)
    assert "SECRET_RAW_SQLITE" not in dumped
    assert "SECRET_FULL_ARCHIVE" not in dumped
    assert "Krótki, dozwolony wycinek pamięci." in dumped


def test_model_guided_context_uses_model_context_packet_shape():
    from latka_jazn.core.model_guided_response_synthesizer import ModelGuidedResponseSynthesizer

    context = ModelGuidedResponseSynthesizer._build_context(
        user_text="Co o tym myślisz?",
        draft_body="Szkic runtime.",
        detected_intent="ordinary_conversation",
        route="ordinary_dialogue",
        cognitive_frame={
            "cognitive_packets": {"dominant_packet": "logic", "packets": [], "reply_guidance": []},
            "voice_source_contract": {"active_source": "jazn_runtime", "biological_claims_allowed": False},
        },
        response_policy={"answer_kind": "natural_dialogue"},
    )
    assert context["schema_version"] == "model_context_packet/v14.8.4.003"
    assert context["detected_intent"] == "ordinary_conversation"
    assert context["cognitive_packets"]["dominant_packet"] == "logic"
    assert context["allowed_memory_items"] == []
    assert "timestamp_generated_by_model" in context["forbidden_claims"]
