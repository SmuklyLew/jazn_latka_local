from __future__ import annotations

from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler
from latka_jazn.core.route_registry import RouteRegistry
from latka_jazn.version import PACKAGE_VERSION, generation_mode, schema_version


def test_version_is_current_009_for_sleep_closure_validator_contract() -> None:
    assert PACKAGE_VERSION == "v14.8.5.009"


def test_sleep_closure_handler_satisfies_route_registry_required_components() -> None:
    entry = RouteRegistry().resolve("sleep_closure_statement")
    result = OrdinaryDialogueHandler().handle(
        "Dobranoc",
        {
            "intent": entry.intent,
            "route_entry": entry.to_dict(),
            "required_components": entry.required_components,
        },
    )

    assert result.route == "sleep_closure"
    assert result.intent == "sleep_closure_statement"
    assert result.generation_mode == generation_mode("ordinary_dialogue")
    assert result.source_origin_detail == schema_version("ordinary_dialogue_handler")
    assert set(entry.required_components).issubset(set(result.satisfied_components))
    assert "Dobranoc, Krzysztofie" in result.body
    assert "Odpowiedź nie zawiera wymaganych składników" not in result.body
    assert "Runtime musi ponowić trasę" not in result.body


def test_non_sleep_ordinary_dialogue_does_not_claim_sleep_components() -> None:
    result = OrdinaryDialogueHandler().handle("Co tam słychać?", {"intent": "ordinary_conversation"})

    assert "current_turn_closure" not in result.satisfied_components
    assert "warmth" not in result.satisfied_components
    assert result.generation_mode == generation_mode("ordinary_dialogue")
