from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.startup_contract import build_startup_status, build_self_check, build_truth_boundary_check, classify_fallback_text
from latka_jazn.core.memory_search_planner import MemorySearchPlanner
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.conversation import ConversationResponder

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def test_startup_status_says_chatgpt_is_minimal_loader_and_runtime_owns_logic() -> None:
    root = Path(__file__).resolve().parents[1]
    status = build_startup_status(JaznConfig(root=root, network_time_first=False)).to_dict()

    assert status["schema_version"] == "self_owned_startup_contract/v14.6.10"
    assert status["runtime_version"] == VERSION
    assert status["start_file"] == "main.py"
    assert status["cli_capabilities"]["--startup-status"] is True
    assert status["cli_capabilities"]["--memory-plan"] is True
    assert "minimal_loader" in status["minimal_chatgpt_loader"].lower() or "lekki loader" in status["minimal_chatgpt_loader"].lower()
    assert any("--memory-plan" in item for item in status["responsibility_split"]["runtime_owned_responsibilities"])
    assert "ChatGPT" in status["truth_boundary"]


def test_self_check_and_truth_boundary_are_runtime_owned() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False)
    self_check = build_self_check(cfg)
    boundary = build_truth_boundary_check(cfg)

    assert self_check["schema_version"] == "self_check/v14.6.10"
    assert self_check["startup_contract_ready"] is True
    assert self_check["chatgpt_instruction_role"] == "minimal_loader_only"
    assert boundary["schema_version"] == "truth_boundary_check/v14.6.10"
    assert any(rule["subject"] == "ChatGPT" for rule in boundary["rules"])


def test_fallback_audit_detects_debug_fallback_text() -> None:
    audit = classify_fallback_text("runtime odebrał wiadomość. Nie znalazłam osobnej trasy odpowiedzi.")
    assert audit["schema_version"] == "fallback_audit/v14.6.10"
    assert audit["classification"] == "technical_fallback"
    assert audit["requires_visible_disclosure"] is True


def test_cli_startup_status_memory_plan_and_fallback_audit_payloads() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False)
    start_payload = build_startup_status(cfg).to_dict()
    assert start_payload["schema_version"] == "self_owned_startup_contract/v14.6.10"
    assert start_payload["runtime_version"] == VERSION

    planner = MemorySearchPlanner(root)
    plan = planner.plan("Przypomnij sobie wszystko na temat naszych piosenek oraz domu")
    plan_payload = {
        "schema_version": "memory_plan_cli/v14.6.10",
        "runtime_version": cfg.version,
        "memory_search_plan": plan.to_dict(),
        "source_file_hits": [hit.to_dict() for hit in planner.search_source_files(plan, limit=5)],
    }
    assert "songs_music" in plan_payload["memory_search_plan"]["topic_keys"]
    assert "home_design" in plan_payload["memory_search_plan"]["topic_keys"]
    assert plan_payload["source_file_hits"]

    audit_payload = classify_fallback_text("runtime odebrał wiadomość")
    assert audit_payload["classification"] == "technical_fallback"


def test_runtime_preview_answers_instruction_vs_runtime_question_without_general_llm_route() -> None:
    decision = ConversationResponder().compose(
        "Czy instrukcja ChatGPT jest już tylko loaderem, a system Jaźni ma pracować sam?"
    )
    assert decision.runtime_answer_quality == "topic_aligned"
    assert decision.route == "free_dialogue_memory_nlp_bridge_question"
    assert "Instrukcja projektu ChatGPT ma być krótka" in decision.body
