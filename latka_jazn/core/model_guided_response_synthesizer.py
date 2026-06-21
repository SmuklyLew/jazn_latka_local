from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

from latka_jazn.model_adapters.base import ModelAdapterRequest


@dataclass(slots=True)
class ModelGuidedSynthesis:
    used: bool
    body: str
    status: str
    provider: str
    model: str
    reason: str
    sources: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelGuidedResponseSynthesizer:
    """Pozwala modelowi sformułować wypowiedź, ale nie oddaje mu pamięci ani sterowania Jaźnią."""

    PROTECTED_INTENTS = {
        "runtime_exact_quote_request",
        "runtime_source_question",
        "file_operation_request",
        "external_research_request",
        "dictionary_network_lookup_request",
        "current_time_question",
        "creative_text_formatting",
    }

    def synthesize(
        self,
        *,
        adapter: Any,
        user_text: str,
        draft_body: str,
        detected_intent: str,
        route: str,
        cognitive_frame: dict[str, Any],
        response_policy: dict[str, Any],
    ) -> ModelGuidedSynthesis:
        status = adapter.describe() if hasattr(adapter, "describe") else {"status": "unknown"}
        if status.get("status") != "configured":
            return ModelGuidedSynthesis(False, draft_body, str(status.get("status") or "not_configured"), str(status.get("name") or "none"), str(status.get("model") or "none"), "model_adapter_not_configured", [])
        if detected_intent in self.PROTECTED_INTENTS or bool(response_policy.get("exact_runtime_required")):
            return ModelGuidedSynthesis(False, draft_body, "skipped", str(status.get("name") or "unknown"), str(status.get("model") or "unknown"), "intent_requires_exact_runtime_or_external_source", [])

        context = self._build_context(
            user_text=user_text,
            draft_body=draft_body,
            detected_intent=detected_intent,
            route=route,
            cognitive_frame=cognitive_frame,
            response_policy=response_policy,
        )
        prompt = (
            "Sformułuj jedną trafną odpowiedź na bieżącą wiadomość użytkownika. "
            "Użyj szkicu tylko jako materiału i ograniczeń; nie kopiuj go automatycznie. "
            "Nie opisuj procesu tworzenia odpowiedzi. Zachowaj wymagane komponenty polityki odpowiedzi. "
            "Jeżeli kontekst nie wystarcza, powiedz krótko czego nie wiesz zamiast zgadywać."
        )
        response = adapter.generate(ModelAdapterRequest(prompt=prompt, system_context=context))
        body = self._clean(response.text)
        if response.status != "completed" or not body:
            return ModelGuidedSynthesis(False, draft_body, response.status, response.provider, response.model, "model_generation_failed_or_empty", response.sources)
        return ModelGuidedSynthesis(True, body, response.status, response.provider, response.model, "generated_from_jazn_cognitive_context", response.sources)

    @staticmethod
    def _clean(text: str) -> str:
        value = (text or "").strip()
        value = re.sub(r"^\[🕒[^\]]+\]\s*[^\n]*\n?", "", value).strip()
        return value

    @staticmethod
    def _build_context(
        *,
        user_text: str,
        draft_body: str,
        detected_intent: str,
        route: str,
        cognitive_frame: dict[str, Any],
        response_policy: dict[str, Any],
    ) -> dict[str, Any]:
        packets = cognitive_frame.get("cognitive_packets") or {}
        memory = cognitive_frame.get("memory_recall_contract") or {}
        return {
            "user_message": user_text,
            "detected_intent": detected_intent,
            "route": route,
            "response_policy": response_policy,
            "draft_runtime_body": draft_body,
            "voice_source_contract": cognitive_frame.get("voice_source_contract") or {},
            "identity_continuity": cognitive_frame.get("identity_continuity") or {},
            "truth_boundary": cognitive_frame.get("truth_boundary") or cognitive_frame.get("truth_boundary_check") or {},
            "logical_reasoning": cognitive_frame.get("logical_reasoning") or {},
            "operational_awareness": cognitive_frame.get("operational_awareness") or {},
            "self_state_runtime": cognitive_frame.get("self_state_runtime") or {},
            "neurocognitive_cycle": cognitive_frame.get("neurocognitive_cycle") or {},
            "cognitive_packets": {
                "dominant_packet": packets.get("dominant_packet"),
                "packets": (packets.get("packets") or [])[:6],
                "reply_guidance": (packets.get("reply_guidance") or [])[:8],
            },
            "polish_reasoning": cognitive_frame.get("polish_reasoning") or {},
            "memory_recall_contract": {
                "items": (memory.get("items") or [])[:8],
                "truth_boundary": memory.get("truth_boundary"),
            },
            "dialogue_context": cognitive_frame.get("dialogue_context") or {},
        }
