from latka_jazn.core.source_origin_ledger import SourceOriginLedger


def test_ledger_records_model_source_and_validation(tmp_path) -> None:
    entry = SourceOriginLedger(tmp_path).build_entry(
        turn_id="t1",
        user_text="Hej",
        response_text="Cześć.",
        route="ordinary_dialogue",
        detected_intent="casual_greeting",
        validator_result={"accepted": True},
        model_response={
            "adapter_id": "lmstudio_runtime_adapter",
            "provider": "lmstudio",
            "endpoint_used": "/responses",
            "candidate_kind": "model_generated",
            "generated": True,
            "source_origin": "model_adapter",
        },
    )
    assert entry.source_origin == "model_adapter"
    assert entry.model_provider == "lmstudio"
    assert entry.model_endpoint_used == "/responses"
    assert entry.model_candidate_validated is True
