from latka_jazn.config import JaznConfig
from latka_jazn.core.model_guided_response_synthesizer import ModelGuidedResponseSynthesizer
from latka_jazn.model_adapters.base import ModelAdapterResponse
from latka_jazn.model_adapters.factory import build_model_adapter
from latka_jazn.model_adapters.local_llm_adapter import LocalLlmAdapter


class FakeConfiguredAdapter:
    def describe(self):
        return {"status": "configured", "name": "fake", "model": "fake-model"}

    def generate(self, request):
        assert request.system_context["detected_intent"] == "ordinary_conversation"
        assert request.system_context["cognitive_packets"]["dominant_packet"] == "logic"
        return ModelAdapterResponse(
            text="Rozumiem sedno. Teraz odpowiadam z całego aktywnego kontekstu, a nie z gotowej formuły.",
            provider="fake",
            model="fake-model",
            status="completed",
        )


def test_default_model_adapter_stays_truthful_and_offline():
    adapter = build_model_adapter(JaznConfig())
    assert adapter.describe()["status"] == "available_as_truthful_fallback"


def test_local_model_adapter_is_truthful_when_model_is_not_selected():
    adapter = LocalLlmAdapter()
    assert adapter.describe()["status"] == "not_configured"
    assert adapter.generate(__import__("latka_jazn.model_adapters.base", fromlist=["ModelAdapterRequest"]).ModelAdapterRequest(prompt="test")).status == "not_configured"


def test_model_guided_synthesis_uses_cognitive_state_instead_of_template():
    result = ModelGuidedResponseSynthesizer().synthesize(
        adapter=FakeConfiguredAdapter(),
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


def test_exact_runtime_request_is_not_rewritten_by_model():
    result = ModelGuidedResponseSynthesizer().synthesize(
        adapter=FakeConfiguredAdapter(),
        user_text="Co dokładnie odpowiedział runtime?",
        draft_body="dokładny tekst",
        detected_intent="runtime_exact_quote_request",
        route="runtime_source",
        cognitive_frame={},
        response_policy={"exact_runtime_required": True},
    )
    assert result.used is False
    assert result.body == "dokładny tekst"
