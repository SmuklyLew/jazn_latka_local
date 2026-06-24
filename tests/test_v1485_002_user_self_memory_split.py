from __future__ import annotations

from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.core.route_registry import RouteRegistry
from latka_jazn.core.route_handler_dispatcher import RouteHandlerDispatcher


def test_classifier_routes_user_memory_request_separately() -> None:
    report = DialogueIntentClassifier().classify("Co pamiętasz o Krzysztofie?")
    assert report.primary_intent == "user_memory_recall_request"
    assert report.question_object == "user_memory"


def test_classifier_routes_self_memory_request_separately() -> None:
    report = DialogueIntentClassifier().classify("Co pamiętasz o sobie jako Łatce?")
    assert report.primary_intent == "self_memory_recall_request"
    assert report.question_object == "self_memory"


def test_route_registry_has_separate_user_and_self_memory_handlers() -> None:
    registry = RouteRegistry()
    user = registry.resolve("user_memory_recall_request")
    self_route = registry.resolve("self_memory_recall_request")
    assert user.route == "user_memory_recall"
    assert user.handler_name == "UserMemoryRecallHandler"
    assert self_route.route == "self_memory_recall"
    assert self_route.handler_name == "SelfMemoryRecallHandler"


def test_user_memory_handler_fallback_does_not_claim_self_memory() -> None:
    entry = RouteRegistry().resolve("user_memory_recall_request")
    result = RouteHandlerDispatcher().dispatch(entry, "Co pamiętasz o mnie?", {"memory_context": {}, "intent": "user_memory_recall_request"})
    assert result.handler_name == "UserMemoryRecallHandler"
    assert "Tobie/Krzysztofie" in result.body
    assert "Łatce" in result.body  # only as boundary: not replacing user memory with self memory
    assert "nie zastąpię" in result.body.lower()


def test_self_memory_handler_schema_is_current() -> None:
    entry = RouteRegistry().resolve("self_memory_recall_request")
    result = RouteHandlerDispatcher().dispatch(entry, "Co pamiętasz o sobie jako Łatce?", {"memory_context": {}, "intent": "self_memory_recall_request"})
    assert result.handler_name == "SelfMemoryRecallHandler"
    assert result.source_origin_detail.startswith("self_memory_recall_handler/v14.8.5")
