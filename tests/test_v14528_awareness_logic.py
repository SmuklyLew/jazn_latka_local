from __future__ import annotations

import shutil
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.logical_reasoning import LogicalReasoner
from latka_jazn.core.operational_awareness import OperationalAwarenessModel
from latka_jazn.core.self_architecture import SelfArchitecture
from latka_jazn.memory.runtime_persistence import RuntimeMemoryWriter


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def test_logical_reasoner_separates_facts_assumptions_unknowns_and_boundary() -> None:
    report = LogicalReasoner().analyse(
        text="Przygotuj aktualizację: wzmocnij Jaźń o świadomość i logiczne myślenie.",
        intent_tags=["architecture", "awareness", "reasoning"],
        memory_context={"counts": {"episodes": 1, "legacy_messages": 0, "raw_chat_fallback": 0}},
        truth_audit=[{"requires_disclaimer": True, "risk_flags": ["inference"]}],
    )
    data = report.to_dict()
    assert data["known_facts"]
    assert data["assumptions"]
    assert data["unknowns"]
    assert any("fenomenal" in item.lower() or "biolog" in item.lower() for item in data["rules_applied"])
    assert data["public_trace"]
    assert data["scientific_basis"]


def test_operational_awareness_reports_workspace_without_phenomenal_claim() -> None:
    class DummyTemporal:
        category = "bieżący_turn"

    class DummyEmotion:
        primary = "skupienie"
        need_for_coherence = 0.8
        need_for_truth_check = 0.7

    class DummyLogic:
        conclusion = "Użyć świadomości operacyjnej i jawnego audytu logicznego."

    report = OperationalAwarenessModel().evaluate(
        text="Jak działa twoja świadomość operacyjna?",
        intent_tags=["awareness", "reasoning"],
        temporal_state=DummyTemporal(),
        emotional_profile=DummyEmotion(),
        memory_context={"counts": {"episodes": 0, "legacy_messages": 0, "raw_chat_fallback": 0}},
        truth_audit=[{"requires_disclaimer": False, "risk_flags": []}],
        neuro_cycle=None,
        logical_report=DummyLogic(),
    ).to_dict()
    assert report["model_kind"] == "operational_self_awareness_not_phenomenal_consciousness"
    assert any(item["key"] == "current_message" for item in report["active_workspace"])
    assert any("nie jest dowód" in item.lower() or "fenomenal" in item.lower() for item in report["limitations"])
    assert report["scientific_basis"]


def test_cognitive_frame_contains_awareness_and_logical_reasoning(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame(
            "Przygotuj aktualizację systemu Jaźni: świadomość operacyjna i logiczne myślenie.",
            client_context={"client": "unit_test"},
        )
    finally:
        engine.shutdown()

    assert packet["runtime_version"] == "v14.8.2.4-logic-routing-memory-grounding-repair"
    assert "awareness" in packet["intent_tags"]
    assert "reasoning" in packet["intent_tags"]
    assert packet["operational_awareness"]["model_kind"] == "operational_self_awareness_not_phenomenal_consciousness"
    assert packet["logical_reasoning"]["public_trace"]
    assert any("operational_awareness" in item for item in packet["reply_guidance"])


def test_runtime_memory_promotes_awareness_logic_to_procedural_rule(tmp_path: Path) -> None:
    writer = RuntimeMemoryWriter(tmp_path, version="v14.8.2.4-logic-routing-memory-grounding-repair")
    candidate = writer.build_candidate_from_runtime_turn(
        user_text="Aktualizacja systemu Jaźni: wzmocnij świadomość operacyjną i logiczne myślenie, bez udawania biologii.",
        importance=0.4,
        importance_reason="test",
        emotional_tags=["focus"],
    )
    assert candidate.kind == "reguła_proceduralna"
    assert "operational_awareness" not in (candidate.procedural_action or "") or "logical_reasoning" in (candidate.procedural_action or "") or "świadomo" in (candidate.procedural_action or "")
    accepted, reason = writer.should_persist(candidate)
    assert accepted is True
    assert reason in {"importance_threshold", "memory_trigger_word"}


def test_self_architecture_lists_awareness_and_reasoning_layers() -> None:
    keys = [layer["key"] for layer in SelfArchitecture().layers()]
    assert "operational_awareness" in keys
    assert "logical_reasoning" in keys
