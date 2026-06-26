from latka_jazn.core.model_guided_response_synthesizer import ModelGuidedResponseSynthesizer
from latka_jazn.core.nlg_plan import SCHEMA_VERSION, NlgPlan
from latka_jazn.core.nlg_planner import build_nlg_plan
from latka_jazn.model_adapters.base import ModelAdapterResponse


def _ordinary_frame() -> dict:
    return {
        "polish_reasoning": {
            "semantic_frame": {
                "speech_act": "statement",
                "primary_intent": "ordinary_conversation",
                "tone": [],
                "requires_memory": False,
                "requires_diagnostic": False,
            },
            "reply_policy": {"llm_allowed": True, "source_grounding_required": False},
        },
        "memory_gate": "not_needed",
    }


def test_nlg_plan_for_ordinary_conversation():
    plan = build_nlg_plan(
        user_text="Cześć, Łatko. Chciałbym chwilę normalnie porozmawiać.",
        cognitive_frame=_ordinary_frame(),
        response_policy={},
        route="ordinary_dialogue",
        detected_intent="ordinary_conversation",
    )
    assert isinstance(plan, NlgPlan)
    assert plan.schema_version == SCHEMA_VERSION
    assert plan.answer_kind == "natural_dialogue"
    assert plan.memory_policy == "not_needed"
    assert plan.source_policy == "runtime_only"
    assert "calm" in plan.tone
    assert "present" in plan.tone
    assert "technical_report_for_ordinary_dialogue" in plan.forbidden_components


def test_nlg_plan_for_memory_request_requires_grounded_payload():
    plan = build_nlg_plan(
        user_text="Co pamiętasz z naszych wcześniejszych rozmów?",
        cognitive_frame={
            "polish_reasoning": {
                "semantic_frame": {"speech_act": "question", "requires_memory": True},
                "reply_policy": {"source_grounding_required": True},
            },
            "memory_recall_contract": {"required": True, "items": []},
        },
        response_policy={"source_grounding_required": True},
        route="self_memory_recall",
        detected_intent="memory_recall_request",
    )
    assert plan.answer_kind == "memory_grounded_answer"
    assert plan.memory_policy == "required_grounded_payload"
    assert plan.source_policy == "runtime_plus_memory"
    assert "memory_item_source" in plan.required_components
    assert "fake_memory_without_grounding" in plan.forbidden_components


def test_nlg_plan_for_health_check_is_brief_diagnostic():
    plan = build_nlg_plan(
        user_text="Czy Jaźń działa po aktualizacji?",
        cognitive_frame={"polish_reasoning": {"semantic_frame": {"requires_diagnostic": True}}},
        response_policy={"requires_diagnostic": True},
        route="runtime_activation_status",
        detected_intent="runtime_health_check",
    )
    assert plan.answer_kind == "diagnostic_brief"
    assert plan.memory_policy == "not_needed"
    assert plan.source_policy == "runtime_only"
    assert "brief_status_fields" in plan.required_components


def test_nlg_plan_for_exact_runtime_quote_forbids_model():
    plan = build_nlg_plan(
        user_text="Pokaż dokładnie, co odpowiedział runtime.",
        cognitive_frame={},
        response_policy={"exact_runtime_required": True},
        route="runtime_source",
        detected_intent="runtime_exact_quote_request",
        model_adapter_status={"status": "configured", "name": "fake"},
    )
    assert plan.answer_kind == "exact_runtime_quote"
    assert plan.memory_policy == "forbidden"
    assert plan.source_policy == "exact_runtime_only"
    assert plan.model_policy == "forbidden_exact_runtime_required"
    assert "exact_runtime_text_no_paraphrase" in plan.required_components
    assert "model_paraphrase_of_exact_runtime_text" in plan.forbidden_components


def test_nlg_plan_preserves_timestamp_required():
    plan = build_nlg_plan(
        user_text="Co tam?",
        cognitive_frame=_ordinary_frame(),
        response_policy={},
        route="ordinary_dialogue",
        detected_intent="ordinary_conversation",
    )
    assert plan.timestamp_required is True
    assert "runtime_adds_timestamp" in plan.style_constraints
    assert "timestamp_generated_by_model" in plan.forbidden_components


def test_nlg_plan_model_policy_null_adapter_does_not_fake_generation():
    plan = build_nlg_plan(
        user_text="Napisz to naturalniej.",
        cognitive_frame=_ordinary_frame(),
        response_policy={"llm_allowed": True},
        route="ordinary_dialogue",
        detected_intent="ordinary_conversation",
        model_adapter_status={"status": "available_as_truthful_fallback", "name": "null"},
    )
    assert plan.model_policy == "disabled_null_adapter"


class CapturingAdapter:
    def describe(self):
        return {"status": "configured", "name": "fake", "model": "fake-model"}

    def generate(self, request):
        plan = request.system_context["nlg_plan"]
        assert plan["answer_kind"] == "natural_dialogue"
        assert plan["memory_policy"] == "not_needed"
        assert plan["timestamp_required"] is True
        return ModelAdapterResponse(
            text="Jestem przy tej rozmowie spokojnie i bez dokładania fałszywej pamięci.",
            provider="fake",
            model="fake-model",
            status="completed",
        )


def test_model_guided_context_contains_nlg_plan_without_changing_runtime_contract():
    result = ModelGuidedResponseSynthesizer().synthesize(
        adapter=CapturingAdapter(),
        user_text="Chcę chwilę zwyczajnie porozmawiać.",
        draft_body="Jestem obok.",
        detected_intent="ordinary_conversation",
        route="ordinary_dialogue",
        cognitive_frame=_ordinary_frame(),
        response_policy={},
    )
    assert result.used is True
    assert result.reason == "generated_from_jazn_cognitive_context"
