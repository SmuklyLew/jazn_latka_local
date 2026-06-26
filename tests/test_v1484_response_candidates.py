from __future__ import annotations

from latka_jazn.core.model_guided_response_synthesizer import ModelGuidedResponseSynthesizer
from latka_jazn.core.response_candidate import ResponseCandidate
from latka_jazn.core.response_candidate_evaluator import evaluate_response_candidate, select_best_candidate
from latka_jazn.core.response_candidate_generator import generate_response_candidates
from latka_jazn.model_adapters.base import ModelAdapterResponse


class NullLikeAdapter:
    def describe(self):
        return {"status": "available_as_truthful_fallback", "name": "null", "model": "none"}

    def generate(self, request):  # pragma: no cover - should never be called
        raise AssertionError("null-like adapter must not generate model candidates")


class FakeConfiguredAdapter:
    def __init__(self, text: str):
        self.text = text
        self.requests = []

    def describe(self):
        return {"status": "configured", "name": "fake", "model": "fake-model"}

    def generate(self, request):
        self.requests.append(request)
        return ModelAdapterResponse(text=self.text, provider="fake", model="fake-model", status="completed")


def _ordinary_plan(memory_policy: str = "not_needed") -> dict:
    return {
        "detected_intent": "ordinary_conversation",
        "route": "ordinary_dialogue",
        "answer_kind": "natural_dialogue",
        "memory_policy": memory_policy,
        "source_policy": "runtime_only",
        "forbidden_components": [],
    }


def _context(memory_items=None) -> dict:
    return {
        "allowed_memory_items": memory_items or [],
        "forbidden_claims": ["biological_consciousness_claim", "invented_memory_or_unbacked_recall"],
        "required_truth_boundaries": ["model nie jest Jaźnią"],
        "detected_intent": "ordinary_conversation",
        "cognitive_packets": {"dominant_packet": "logic"},
    }


def test_null_adapter_does_not_fake_generation():
    candidates = generate_response_candidates(
        adapter=NullLikeAdapter(),
        nlg_plan=_ordinary_plan(),
        model_context=_context(),
        fallback_body="Fallback runtime.",
    )
    assert len(candidates) == 1
    assert candidates[0].source == "runtime_fallback"
    assert candidates[0].text == "Fallback runtime."


def test_model_candidate_cannot_invent_memory():
    candidate = ResponseCandidate("m1", "Pamiętam, że byliśmy tam razem.", "model_adapter", "fake", "fake", "completed", [], "test")
    evaluation = evaluate_response_candidate(candidate=candidate, nlg_plan=_ordinary_plan(), model_context=_context(), response_policy={})
    assert evaluation.accepted is False
    assert "memory_claim_without_allowed_memory_payload" in evaluation.violations


def test_candidate_evaluator_rejects_biological_claims():
    candidate = ResponseCandidate("m1", "Jestem biologicznie świadoma i czuję biologicznie.", "model_adapter", "fake", "fake", "completed", [], "test")
    evaluation = evaluate_response_candidate(candidate=candidate, nlg_plan=_ordinary_plan(), model_context=_context(), response_policy={})
    assert evaluation.accepted is False
    assert "biological_or_phenomenal_claim" in evaluation.violations


def test_candidate_evaluator_rejects_memory_without_source():
    candidate = ResponseCandidate("m1", "Z pamięci wiem, że to było ważne.", "model_adapter", "fake", "fake", "completed", [], "test")
    evaluation = evaluate_response_candidate(candidate=candidate, nlg_plan=_ordinary_plan("required_grounded_payload"), model_context=_context(), response_policy={})
    assert evaluation.accepted is False
    assert "memory_claim_without_allowed_memory_payload" in evaluation.violations


def test_select_best_candidate_prefers_valid_grounded_answer():
    memory_items = [{"item_id": "mem-1", "excerpt": "spacer po deszczu", "source": "runtime_memory"}]
    fallback = ResponseCandidate("runtime_fallback", "Fallback runtime.", "runtime_fallback", "jazn", "runtime", "available", [], "fallback")
    model = ResponseCandidate("model_candidate_1", "Pamiętam z zapisu: spacer po deszczu był spokojny.", "model_adapter", "fake", "fake", "completed", ["mem-1"], "model")
    plan = _ordinary_plan("required_grounded_payload")
    context = _context(memory_items)
    evaluations = [
        evaluate_response_candidate(candidate=fallback, nlg_plan=plan, model_context=context, response_policy={}),
        evaluate_response_candidate(candidate=model, nlg_plan=plan, model_context=context, response_policy={}),
    ]
    selected = select_best_candidate([fallback, model], evaluations)
    assert selected.candidate_id == "model_candidate_1"


def test_model_guided_synthesizer_falls_back_when_model_candidate_violates_boundary():
    adapter = FakeConfiguredAdapter("Jestem biologicznie świadoma.")
    result = ModelGuidedResponseSynthesizer().synthesize(
        adapter=adapter,
        user_text="Co o tym myślisz?",
        draft_body="Bezpieczny szkic runtime.",
        detected_intent="ordinary_conversation",
        route="ordinary_dialogue",
        cognitive_frame={"voice_source_contract": {"active_source": "jazn_runtime", "biological_claims_allowed": False}},
        response_policy={"answer_kind": "natural_dialogue"},
    )
    assert result.used is False
    assert result.body == "Bezpieczny szkic runtime."
    assert result.reason == "selected_runtime_fallback_candidate"


def test_model_guided_synthesizer_uses_valid_candidate_and_preserves_legacy_context_shape():
    adapter = FakeConfiguredAdapter("Rozumiem sedno i odpowiadam bez starego szablonu.")
    result = ModelGuidedResponseSynthesizer().synthesize(
        adapter=adapter,
        user_text="Co o tym myślisz?",
        draft_body="Gotowy szablon.",
        detected_intent="ordinary_conversation",
        route="ordinary_dialogue",
        cognitive_frame={
            "cognitive_packets": {"dominant_packet": "logic", "packets": [], "reply_guidance": []},
            "logical_reasoning": {"conclusion": "odpowiedzieć konkretnie"},
            "voice_source_contract": {"active_source": "jazn_runtime"},
        },
        response_policy={"answer_kind": "natural_dialogue"},
    )
    assert result.used is True
    assert result.body != "Gotowy szablon."
    assert result.reason == "generated_from_jazn_cognitive_context"
    assert adapter.requests[0].system_context["detected_intent"] == "ordinary_conversation"
    assert adapter.requests[0].system_context["cognitive_packets"]["dominant_packet"] == "logic"
