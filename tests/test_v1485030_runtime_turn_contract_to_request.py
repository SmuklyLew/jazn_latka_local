from latka_jazn.core.runtime_turn_contract import RuntimeTurnContract


def test_runtime_turn_contract_builds_candidate_only_request() -> None:
    turn = RuntimeTurnContract.for_model_request(
        user_text="Cześć",
        detected_intent="casual_greeting",
        route="ordinary_dialogue",
        runtime_exact_text="runtime draft",
        system_context={"trace_id": "trace-1"},
    )
    request = turn.to_model_adapter_request(user_text="Cześć")
    assert request.prompt == "Cześć"
    assert request.system_context["runtime_exact_text"] == "runtime draft"
    assert request.metadata["candidate_requires_runtime_validation"] is True
    assert "Nie jesteś Jaźnią" in request.instructions
