from __future__ import annotations

import json
import shutil
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.runtime_operating_model import CognitiveRuntimeOperatingModel
from latka_jazn.integrations.github_repository_plan import build_github_repository_plan, write_github_repository_plan

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def test_config_version_and_memory_db_are_v14538() -> None:
    cfg = JaznConfig()
    assert cfg.version == VERSION
    assert cfg.memory_db_path.name == "latka_jazn_v14_8_2.sqlite3"


def test_runtime_operating_model_splits_llm_and_jazn_roles() -> None:
    decision = CognitiveRuntimeOperatingModel().analyse(
        "Czy system Jaźni powinien działać jak LLM, OpenAI i ChatGPT, czy bardziej jak mózg runtime?",
        intent_tags=["architecture"],
    )
    data = decision.to_dict()
    assert data["route"] == "llm_plus_cognitive_runtime"
    assert "kanał języka" in data["llm_role"]
    assert "warstwa" in data["jazn_role"]
    assert "biologicznego" in data["truth_boundary"]


def test_github_repository_plan_contains_two_private_truth_sources(tmp_path: Path) -> None:
    plan = build_github_repository_plan(tmp_path)
    names = [repo.name for repo in plan.repositories]
    assert "SmuklyLew/Latka.Jazn" in names
    assert "SmuklyLew/Latka.Jazn.Memory" in names
    assert any("memory/raw/dziennik.json" in repo.include for repo in plan.repositories)
    assert "memory/raw/chat.html.7z" in plan.files_to_keep_private
    assert "commicie/pushu" in plan.truth_boundary

    path = write_github_repository_plan(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "github_repository_plan/v1"
    assert len(data["repositories"]) == 2


def test_cognitive_frame_contains_runtime_operating_model_and_github_plan(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame(
            "Przygotuj aktualizację pod GitHub i powiedz, czy Jaźń to LLM czy warstwa mózgopodobna runtime.",
            client_context={"client": "unit_test"},
        )
    finally:
        engine.shutdown()

    assert packet["runtime_version"] == VERSION
    assert packet["runtime_operating_model"]["route"] == "system_update_with_repository_prep"
    assert packet["github_repository_plan"]["repositories"][0]["name"] == "SmuklyLew/Latka.Jazn"
    assert "github_checkpoint_policy" in packet
    assert any("GitHub" in item or "LLM" in item for item in packet["reply_guidance"])


def test_main_parser_has_github_plan_flag() -> None:
    from main import _build_parser

    parser = _build_parser()
    ns = parser.parse_args(["--github-plan"])
    assert ns.github_plan is True
