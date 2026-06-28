from __future__ import annotations

from latka_jazn.core.route_contract_matrix import RouteContractMatrix
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.core.route_registry import RouteRegistry


def test_route_contract_matrix_recognizes_core_short_inputs() -> None:
    matrix = RouteContractMatrix()
    cases = {
        "Działasz?": "runtime_health_check",
        "Jesteś tam Łatko?": "presence_check",
        "Czy to nadal Ty?": "identity_continuity_check",
        "Co teraz czujesz?": "self_state_question",
        "Wiesz jaka jest pora?": "time_awareness_question",
        "Co teraz czujesz? Wiesz jaka jest pora?": "self_state_time_awareness",
    }
    for text, expected in cases.items():
        hint = matrix.classify(text)
        assert hint.primary_intent == expected, text
        assert expected in hint.matched_contracts or expected == "self_state_time_awareness"


def test_dialogue_intent_classifier_uses_route_contract_matrix_before_ordinary_fallback() -> None:
    classifier = DialogueIntentClassifier()
    cases = {
        "Działasz?": "runtime_health_check",
        "Jesteś tam Łatko?": "presence_check",
        "Czy to nadal Ty?": "identity_continuity_check",
        "Co teraz czujesz?": "self_state_question",
        "Wiesz jaka jest pora?": "time_awareness_question",
        "Co teraz czujesz? Wiesz jaka jest pora?": "self_state_time_awareness",
    }
    for text, expected in cases.items():
        report = classifier.classify(text)
        assert report.primary_intent == expected, report.to_dict()
        assert report.primary_intent != "ordinary_conversation"
        assert any("route_contract_matrix" in item for item in report.evidence)


def test_route_registry_has_contract_entries_for_new_intents() -> None:
    registry = RouteRegistry()
    expected = {
        "runtime_health_check": ("runtime_health_check", "CapabilityStatusHandler"),
        "presence_check": ("presence_status", "PresenceStatusHandler"),
        "identity_presence_check": ("identity_presence_status", "PresenceStatusHandler"),
        "identity_continuity_check": ("identity_runtime_truth_contract", "IdentityRuntimeTruthHandler"),
        "time_awareness_question": ("time_awareness", "TimeAwarenessHandler"),
        "self_state_time_awareness": ("self_state", "SelfStateHandler"),
    }
    for intent, (route, handler) in expected.items():
        entry = registry.resolve(intent)
        assert entry.route == route
        assert entry.handler_name == handler
        assert entry.required_components
