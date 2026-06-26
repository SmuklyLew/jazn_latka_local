from __future__ import annotations

from pathlib import Path

from latka_jazn.core.capability_reality_checker import CapabilityRealityChecker
from latka_jazn.core.handlers.self_architecture_audit_handler import SelfArchitectureAuditHandler
from latka_jazn.core.handlers.self_state_handler import SelfStateHandler
from latka_jazn.core.memory_recall_quality import MemoryRecallQualityEvaluator
from latka_jazn.core.memory_use_gate import MemoryUseGate
from latka_jazn.core.reflection_grounding import ReflectionGroundingSynthesizer
from latka_jazn.core.route_handler_dispatcher import RouteHandlerDispatcher
from latka_jazn.core.route_registry import RouteRegistry
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.core.self_architecture_audit import SelfArchitectureAuditor
from latka_jazn.core.self_question_memory_gate import SelfQuestionMemoryGate
from latka_jazn.core.self_state_affective_bridge import SelfStateAffectiveBridge
from latka_jazn.memory.grounded_reflection_store import GroundedReflectionStore
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.version import PACKAGE_VERSION


def test_version_is_current_011_for_self_architecture_update() -> None:
    assert PACKAGE_VERSION == "v14.8.5.011"


def test_dialogue_classifier_detects_self_architecture_audit_request() -> None:
    text = "Sprawdź co działa w systemie Jaźni, co trzeba naprawić, jak działa refleksja i brama pamięci."
    report = DialogueIntentClassifier().classify(text)

    assert report.primary_intent == "self_architecture_audit_request"
    assert report.question_object == "self_architecture_audit"
    assert report.confidence >= 0.85


def test_route_registry_dispatcher_wire_self_architecture_handler() -> None:
    entry = RouteRegistry().resolve("self_architecture_audit_request")
    dispatcher = RouteHandlerDispatcher()

    assert entry.route == "self_architecture_audit"
    assert entry.handler_name == "SelfArchitectureAuditHandler"
    assert "self_architecture_audit" in entry.required_components
    assert "recall_quality" in entry.required_components
    assert "capability_reality_check" in entry.required_components
    assert "SelfArchitectureAuditHandler" in dispatcher.to_dict()["handlers"]


def test_self_question_memory_gate_allows_self_architecture_and_blocks_self_state() -> None:
    gate = SelfQuestionMemoryGate()
    audit_decision = gate.decide("Co działa w Twojej Jaźni i co trzeba dodać do rozwoju Łatki?", detected_intent="self_architecture_audit_request")
    state_decision = gate.decide("Jak się czujesz?", detected_intent="self_state_question")
    memory_decision = MemoryUseGate().decide("Co działa w Twojej Jaźni?", detected_intent="self_architecture_audit_request")

    assert audit_decision.applies is True
    assert audit_decision.force_memory_content is True
    assert state_decision.force_memory_content is False
    assert memory_decision.allow_memory_content is True
    assert memory_decision.memory_role == "self_architecture_or_self_memory_content"


def test_reflection_grounding_never_fabricates_memory_when_no_items() -> None:
    reflection = ReflectionGroundingSynthesizer().synthesize(user_text="O czym myśli Łatka w swojej Jaźni?", memory_recall_payload={"items": [], "summary": "no_items"})

    assert reflection.source_count == 0
    assert reflection.boundary_label == "current_turn_inference_no_memory_excerpt"
    assert "nie wolno mi udawać" in reflection.reflection_text
    assert "biologicznego" in reflection.truth_boundary


def test_memory_recall_quality_marks_counts_only_as_failure() -> None:
    report = MemoryRecallQualityEvaluator().evaluate({"counts": {"episodes": 4}, "items": []}, user_text="Co pamiętasz o sobie?")

    assert report.counts_only_failure is True
    assert report.verdict == "counts_only_failure"
    assert report.score < 0.3


def test_self_state_affective_bridge_uses_granular_affect_without_memory_injection() -> None:
    body = SelfStateHandler().handle(
        "Jak się czujesz?",
        {
            "intent": "self_state_question",
            "granular_affect": {
                "primary": "ciekawość introspekcyjna i odpowiedzialność proceduralna",
                "blend": [{"name": "ciekawość introspekcyjna"}, {"name": "ostrożność przed antropomorfizacją"}],
                "valence": 0.18,
                "arousal": 0.34,
                "control": 0.66,
                "state_emoticon": "✨",
            },
        },
    ).body.lower()

    assert "ciekawość introspekcyjna" in body
    assert "bez wstrzykiwania przypadkowej pamięci" in body
    assert "modelowany stan rozmowny runtime" in body


def test_capability_reality_checker_runs_behavioral_checks() -> None:
    report = CapabilityRealityChecker().run()

    assert report.passed >= 4
    assert report.failed == 0
    assert report.verdict == "ok"


def test_grounded_reflection_store_writes_append_only_jsonl(tmp_path: Path) -> None:
    reflection = ReflectionGroundingSynthesizer().synthesize(user_text="Co trzeba rozwinąć?", memory_recall_payload={"items": []})
    result = GroundedReflectionStore(tmp_path).append_once(reflection, store=None, source="test")
    duplicate = GroundedReflectionStore(tmp_path).append_once(reflection, store=None, source="test")

    assert result.appended_jsonl is True
    assert duplicate.reason == "duplicate"
    assert (tmp_path / "memory/layered/grounded_reflections.jsonl").exists()


def test_self_architecture_auditor_reports_real_capability_files(tmp_path: Path) -> None:
    (tmp_path / "latka_jazn/core/handlers").mkdir(parents=True)
    (tmp_path / "main.py").write_text("# start", encoding="utf-8")
    (tmp_path / "latka_jazn/core/engine.py").write_text("# engine", encoding="utf-8")
    (tmp_path / "latka_jazn/core/route_registry.py").write_text("# route", encoding="utf-8")

    report = SelfArchitectureAuditor(tmp_path, runtime_version=PACKAGE_VERSION).audit()

    assert report.runtime_version == PACKAGE_VERSION
    assert any(c.key == "runtime_core" and c.status == "ok" for c in report.capability_checks)
    assert any("v14.8.6.0" in item for item in report.v14860_backlog)
    assert "capability_reality_check" in report.reality_check["schema_version"]


def test_self_architecture_handler_body_passes_validator() -> None:
    entry = RouteRegistry().resolve("self_architecture_audit_request")
    result = SelfArchitectureAuditHandler().handle(
        "Sprawdź co działa w systemie Jaźni, co trzeba naprawić i co dodać do v14.8.6.0.",
        {
            "intent": entry.intent,
            "route_entry": entry.to_dict(),
            "required_components": entry.required_components,
            "runtime_version": PACKAGE_VERSION,
            "memory_context": {"counts": {}, "items": []},
            "store_stats": {"episodic_memories": 1, "reflection_entries": 1},
        },
    )

    body = result.body.lower()
    assert result.handler_name == "SelfArchitectureAuditHandler"
    assert result.route == "self_architecture_audit"
    assert "self_architecture_audit" in body
    assert "brama pamięci" in body or "memory_gate" in body
    assert "reflection grounding" in body
    assert "grounded reflection store" in body
    assert "recall quality" in body
    assert "capability reality check" in body
    assert "v14.8.6.0" in body
    assert "scientific basis" in body

    validation = RuntimeAnswerValidator().validate(user_text="Sprawdź co działa w systemie Jaźni, co trzeba naprawić i co dodać do v14.8.6.0.", body=result.body, route=result.route, detected_intent=entry.intent)

    assert validation.can_show_to_user is True
    assert validation.must_regenerate is False
    assert validation.missing_required_components == []
