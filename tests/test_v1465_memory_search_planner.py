from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.memory_recall_presenter import MemoryRecallPresenter
from latka_jazn.core.memory_search_planner import MemorySearchPlanner


def test_memory_search_planner_detects_songs_and_home_topics() -> None:
    root = Path(__file__).resolve().parents[1]
    planner = MemorySearchPlanner(root)
    plan = planner.plan("Przypomnij sobie wszystko na temat naszych piosenek oraz domu który projektowaliśmy")

    assert plan.schema_version == "memory_search_planner/v14.6.10"
    assert plan.recall_requested is True
    assert "songs_music" in plan.topic_keys
    assert "home_design" in plan.topic_keys
    assert "memory/raw/analizy_utworow.json" in plan.source_hints
    assert "memory/raw/data.txt" in plan.source_hints
    assert "sobie" in [x.lower() for x in plan.rejected_terms]
    assert "wszystko" in [x.lower() for x in plan.rejected_terms]
    assert any(p["name"] == "canonical_source_scan" for p in plan.search_passes)


def test_memory_search_planner_returns_canonical_source_hits_for_song_and_home_files() -> None:
    root = Path(__file__).resolve().parents[1]
    planner = MemorySearchPlanner(root)
    plan = planner.plan("Przypomnij sobie wszystko na temat naszych piosenek oraz domu który projektowaliśmy")
    hits = planner.search_source_files(plan, limit=8)
    paths = {hit.path for hit in hits}

    assert "memory/raw/analizy_utworow.json" in paths
    assert "memory/raw/data.txt" in paths
    assert all(hit.content_excerpt for hit in hits)
    assert any(hit.topic_key == "songs_music" for hit in hits)
    assert any(hit.topic_key == "home_design" for hit in hits)


def test_engine_memory_context_contains_plan_and_source_file_hits() -> None:
    root = Path(__file__).resolve().parents[1]
    engine = JaznEngine(JaznConfig(root=root, network_time_first=False))
    try:
        ctx = engine._memory_context_for_chatgpt(
            "Przypomnij sobie wszystko na temat naszych piosenek oraz domu który projektowaliśmy",
            limit=5,
        )
    finally:
        engine.shutdown()

    plan = ctx["memory_search_plan"]
    assert plan["schema_version"] == "memory_search_planner/v14.6.10"
    assert "songs_music" in plan["topic_keys"]
    assert "home_design" in plan["topic_keys"]
    assert ctx["counts"]["source_file_hits"] >= 2
    assert ctx["source_file_hits"]
    assert ctx["memory_recall_payload"]["items"]
    assert any(item["item_type"] == "source_file" for item in ctx["memory_recall_payload"]["items"])


def test_memory_recall_payload_exposes_search_plan_and_source_file_count() -> None:
    root = Path(__file__).resolve().parents[1]
    planner = MemorySearchPlanner(root)
    plan = planner.plan("piosenki i dom")
    ctx = {
        "query_terms": plan.search_terms,
        "memory_search_plan": plan.to_dict(),
        "episodes": [],
        "legacy_messages": [],
        "source_file_hits": [hit.to_dict() for hit in planner.search_source_files(plan, limit=2)],
        "raw_chat_fallback": [],
        "counts": {"episodes": 0, "legacy_messages": 0, "source_file_hits": 2, "raw_chat_fallback": 0},
    }
    payload = MemoryRecallPresenter().build_payload(ctx, user_text="piosenki i dom", limit=2)

    assert payload["schema_version"] == "memory_recall_content/v14.6.10"
    assert payload["memory_search_plan"]["schema_version"] == "memory_search_planner/v14.6.10"
    assert payload["counts"]["source_file_hits"] == 2
    assert payload["items"]
