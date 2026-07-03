from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.runtime_response_synthesizer import RuntimeResponseSynthesizer
from latka_jazn.core.template_registry import TemplateRegistry


def test_allowed_positive_feedback_template_is_not_replaced_by_repair_template() -> None:
    body = "Też się cieszę."
    template = TemplateRegistry().classify_body(body, detected_intent="positive_feedback_current_turn")
    synthesis = RuntimeResponseSynthesizer().synthesize(
        user_text="Super",
        detected_intent="positive_feedback_current_turn",
        original_body=body,
        route="ordinary_dialogue",
        template_origin=template,
        validation={"must_regenerate": False},
    )
    assert synthesis.should_override is False
    assert synthesis.body == body


def test_process_turn_positive_feedback_is_short_relevant_and_timestamped() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False, memory_db_name="workspace_runtime/test_v14824_positive_feedback.sqlite3")
    engine = JaznEngine(cfg)
    try:
        envelope = engine.process_turn("Super", client_context={"client": "pytest", "lifecycle": "one_shot"}).to_dict()
    finally:
        engine.shutdown()

    frame = envelope["cognitive_frame"]
    final_text = envelope["final_visible_text"] or ""
    timestamp = envelope["trace"]["timestamp_header"]
    assert frame["dialogue_intent_classifier"]["primary_intent"] == "positive_feedback_current_turn"
    assert final_text.startswith(timestamp)
    assert "wymaga generacji przez host/model" in final_text
    assert "Zatrzymuję się przy tym zdaniu" not in final_text
    assert envelope["final_response_contract"]["fallback_classification"] == "cannot_answer_directly"
    assert envelope["final_response_contract"]["requires_host_model"] is True
