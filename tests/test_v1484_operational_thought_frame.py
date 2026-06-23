from latka_jazn.core.nlg_planner import build_nlg_plan
from latka_jazn.core.operational_thought_frame import (
    SCHEMA_VERSION,
    OperationalThoughtFrame,
    OperationalThoughtSignal,
    build_operational_thought_frame,
    summarize_current_user_message,
)


def _ordinary_plan():
    return build_nlg_plan(
        user_text="Cześć, Łatko. Chcę zwyczajnie porozmawiać.",
        cognitive_frame={"memory_gate": "not_needed"},
        response_policy={},
        route="ordinary_dialogue",
        detected_intent="ordinary_conversation",
    )


def test_summarize_current_user_message_trims_without_memory_lookup():
    long = "  To jest   bardzo długie zdanie " * 20
    summary = summarize_current_user_message(long, max_chars=80)
    assert len(summary) <= 80
    assert "  " not in summary
    assert summary.endswith("…")


def test_operational_thought_frame_for_ordinary_dialogue():
    frame = build_operational_thought_frame(
        user_text="Cześć, Łatko. Chcę zwyczajnie porozmawiać.",
        nlg_plan=_ordinary_plan(),
        cognitive_frame={"memory_gate": "not_needed"},
        response_policy={},
    )
    assert isinstance(frame, OperationalThoughtFrame)
    assert frame.schema_version == SCHEMA_VERSION
    assert frame.memory_decision == "not_needed"
    assert frame.source_decision == "runtime_only"
    assert frame.model_decision in {"allowed_if_configured", "disabled_null_adapter", "allowed"}
    assert "random_memory_injection" in frame.rejected_paths
    assert "naturalnie" in frame.selected_goal
    assert "present" in frame.selected_tone
    assert any(signal.name == "memory_gate" for signal in frame.observed_signals)


def test_operational_thought_frame_for_memory_request_requires_grounding():
    plan = build_nlg_plan(
        user_text="Co pamiętasz?",
        cognitive_frame={"polish_reasoning": {"semantic_frame": {"requires_memory": True}}},
        response_policy={"source_grounding_required": True},
        route="self_memory_recall",
        detected_intent="memory_recall_request",
    )
    frame = build_operational_thought_frame(
        user_text="Co pamiętasz?",
        nlg_plan=plan,
        cognitive_frame={},
        response_policy={"source_grounding_required": True},
    )
    assert frame.memory_decision == "required_grounded_payload"
    assert frame.source_decision == "runtime_plus_memory"
    assert frame.refusal_or_boundary is not None
    assert any(signal.name == "memory_grounding_required" for signal in frame.observed_signals)
    assert "claiming_memory_without_payload" not in frame.rejected_paths


def test_operational_thought_frame_for_exact_runtime_quote_forbids_model():
    plan = build_nlg_plan(
        user_text="Pokaż dokładny tekst runtime.",
        cognitive_frame={},
        response_policy={"exact_runtime_required": True},
        route="runtime_source",
        detected_intent="runtime_exact_quote_request",
        model_adapter_status={"status": "configured", "name": "fake"},
    )
    frame = build_operational_thought_frame(
        user_text="Pokaż dokładny tekst runtime.",
        nlg_plan=plan,
        cognitive_frame={},
        response_policy={"exact_runtime_required": True},
    )
    assert frame.model_decision == "forbidden_exact_runtime_required"
    assert frame.source_decision == "exact_runtime_only"
    assert "model_paraphrase_of_exact_runtime_text" in frame.rejected_paths
    assert any(signal.name == "exact_runtime_required" for signal in frame.observed_signals)


def test_operational_thought_frame_for_external_source_rejects_fake_lookup():
    plan = build_nlg_plan(
        user_text="Sprawdź aktualne informacje w sieci.",
        cognitive_frame={},
        response_policy={"allow_online_lookup": True},
        route="external_research",
        detected_intent="external_research_request",
    )
    frame = build_operational_thought_frame(
        user_text="Sprawdź aktualne informacje w sieci.",
        nlg_plan=plan,
        cognitive_frame={},
        response_policy={"allow_online_lookup": True},
    )
    assert frame.source_decision == "requires_external_web"
    assert "local_runtime_fake_web_lookup" in frame.rejected_paths
    assert frame.refusal_or_boundary is not None


def test_signal_and_frame_to_dict_are_plain_dicts():
    signal = OperationalThoughtSignal(name=" answer kind ", value=" natural_dialogue ", confidence=2.5, source=" nlg_plan ")
    assert signal.confidence == 1.0
    frame = OperationalThoughtFrame(
        schema_version="",
        user_message_summary=" test ",
        observed_signals=[signal.to_dict()],
        selected_goal=" answer ",
        selected_tone=["calm", "calm"],
        memory_decision="not_needed",
        source_decision="runtime_only",
        model_decision="allowed_if_configured",
        refusal_or_boundary="",
        rejected_paths=["old_topic_stale_route", "old_topic_stale_route"],
        truth_boundary="",
    )
    data = frame.to_dict()
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["observed_signals"][0]["name"] == "answer_kind"
    assert data["selected_tone"] == ["calm"]
    assert data["refusal_or_boundary"] is None
