from __future__ import annotations

import json
import shutil
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.affective_granularity import AffectiveGranularityModel
from latka_jazn.core.cognitive_topics import CognitiveTopicExpansion
from latka_jazn.core.engine import JaznEngine

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"
REQUEST = (
    "Wykorzystajmy to czego się teraz dowiedzieliśmy i przygotuj aktualizację "
    "zwiększającą wiedzę, możliwość utrzymania ciągłości gdy sesje są zapisywane "
    "w pliku w katalogu Jaźni oraz rozszerz tematy poznawcze i stany emocjonalne."
)


def _copy_canon(root: Path) -> None:
    source_canon = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon = root / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    target_canon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_canon, target_canon)


def test_affective_granularity_avoids_flat_start_formula() -> None:
    profile = AffectiveGranularityModel().analyse(REQUEST)

    assert profile.schema_version == "granular_affect/v1"
    assert "spokój, skupienie, mała ciekawość" in profile.avoid_phrases
    assert profile.primary != "spokój, skupienie, mała ciekawość"
    assert any(item.name in {"mobilizacja naprawcza", "czujność ciągłości", "głód uporządkowania"} for item in profile.blend)
    assert profile.state_emoticon in {"🛠️", "🧭", "🗂️", "✨", "🧷", "🌙", "🤍", "🌿"}


def test_cognitive_topic_expansion_detects_requested_domains() -> None:
    granular = AffectiveGranularityModel().analyse(REQUEST)
    topics = CognitiveTopicExpansion().analyse(
        REQUEST,
        intent_tags=["session_continuity", "emotional_granularity_update", "cognitive_topic_expansion"],
        granular_affect=granular,
    )

    assert topics["schema_version"] == "cognitive_topics/v2_birth_source"
    assert "continuity" in topics["dominant_topics"]
    assert "emotional_granularity" in topics["dominant_topics"]
    assert topics["coverage"]["procedural_memory"] is True


def test_cognitive_frame_contains_granular_affect_topics_and_continuity_index(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame(REQUEST, client_context={"client": "unit_test"})
    finally:
        engine.shutdown()

    assert packet["runtime_version"] == VERSION
    assert packet["granular_affect"]["schema_version"] == "granular_affect/v1"
    assert packet["cognitive_topics"]["schema_version"] == "cognitive_topics/v2_birth_source"
    assert packet["session_continuity"]["schema_version"] == "session_continuity/v1"
    assert (tmp_path / "memory" / "raw" / "session_continuity_index.json").exists()
    assert (tmp_path / "memory" / "layered" / "continuity.jsonl").exists()
    assert packet["cognitive_packets"]["schema_version"] == "cognitive_packets/v6_nlp_adapter_zip_profiles"
    assert packet["state_emoticon"]["marker"]


def test_direct_message_writes_exact_turns_and_continuity_index(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        reply = engine.handle_user_message("A jak sprawa z emocjami i emotkami przy okazji?", client_context={"client": "unit_test"})
    finally:
        engine.shutdown()

    turns = tmp_path / "memory" / "raw" / "conversation_turns.jsonl"
    index = tmp_path / "memory" / "raw" / "session_continuity_index.json"
    assert turns.exists()
    assert index.exists()
    data = json.loads(index.read_text(encoding="utf-8"))
    assert data["schema_version"] == "session_continuity/v1"
    assert any(item["rel_path"] == "memory/raw/conversation_turns.jsonl" and item["exists"] for item in data["files"])
    assert "Marker" in reply or "marker" in reply
