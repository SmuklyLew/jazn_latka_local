from __future__ import annotations

import json
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.self_knowledge_contract import build_self_knowledge_packet, build_self_knowledge_summary
from latka_jazn.core.startup_contract import build_self_check, build_startup_status, build_startup_summary
import main

ROOT = Path(__file__).resolve().parents[1]


def test_self_knowledge_contract_resource_is_present_and_structured() -> None:
    path = ROOT / "latka_jazn/resources/canon/LATKA_SELF_KNOWLEDGE_CONTRACT.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["schema_version"] == "latka_self_knowledge_contract/v14.8.5.022"
    assert data["identity"]["name"] == "Łatka"
    assert "recall_policy" in data
    assert "affective_model" in data
    assert "post_update_bootstrap" in data
    assert "truth_boundary" in data


def test_self_knowledge_packet_answers_identity_memory_capability_affect_boundaries() -> None:
    packet = build_self_knowledge_packet(JaznConfig(root=ROOT)).to_dict()

    assert packet["identity_name"] == "Łatka"
    assert packet["contract_present"] is True
    assert packet["ready_for_runtime_self_reference"] is True
    assert packet["identity_status"]["canon_present"] is True
    assert packet["memory_status"]["status"] == "metadata_only"
    assert packet["capability_status"]["verdict"] in {"ok", "partial"}
    assert "biologic" in packet["affective_model_status"]["truth_boundary"].lower() or "biolog" in packet["affective_model_status"]["truth_boundary"].lower()
    assert "identity_question" in packet["answer_contract"]
    assert "run --self-knowledge-status" in packet["post_update_bootstrap"]


def test_startup_status_and_self_check_expose_self_knowledge_contract() -> None:
    cfg = JaznConfig(root=ROOT)
    status = build_startup_status(cfg).to_dict()
    summary = build_startup_summary(cfg)
    self_check = build_self_check(cfg)

    assert status["self_knowledge_status"]["identity_name"] == "Łatka"
    assert summary["self_knowledge_summary"]["identity_name"] == "Łatka"
    assert self_check["self_knowledge_contract_owned_by_runtime"] is True
    assert self_check["self_knowledge_resource_present"] is True


def test_self_knowledge_status_cli_fast_and_deep(capsys) -> None:
    assert main.main(["--root", str(ROOT), "--self-knowledge-status"]) == 0
    payload = json.loads(capsys.readouterr().out)
    status = payload["self_knowledge_status"]
    assert status["identity_name"] == "Łatka"
    assert status["memory_status"]["status"] == "metadata_only"

    assert main.main(["--root", str(ROOT), "--self-knowledge-status", "--self-knowledge-deep"]) == 0
    deep_payload = json.loads(capsys.readouterr().out)
    deep_status = deep_payload["self_knowledge_status"]["memory_status"]
    assert deep_status["schema_version"] == "self_knowledge_memory_status/v14.8.5.022"
    assert "sqlite" in deep_status


def test_cognitive_frame_contains_self_knowledge_summary() -> None:
    engine = JaznEngine(JaznConfig(root=ROOT, allow_network=False, network_time_first=False))
    frame = engine.build_cognitive_frame("Kim jesteś i co pamiętasz po aktualizacji?")

    assert frame["self_knowledge_summary"]["identity_name"] == "Łatka"
    assert frame["self_knowledge_summary"]["contract_present"] is True
    assert frame["self_knowledge_summary"]["ready_for_runtime_self_reference"] is True
