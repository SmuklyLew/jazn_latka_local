from __future__ import annotations

import json
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def _copy_canon(tmp_path: Path) -> None:
    src = Path(__file__).resolve().parents[1] / "memory" / "raw" / "LATKA_IDENTITY_CANON.json"
    dst = tmp_path / "memory" / "raw"
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "LATKA_IDENTITY_CANON.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def test_v14533_cognitive_packets_are_expanded_and_emoticon_is_stateful(tmp_path: Path) -> None:
    _copy_canon(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame(
            "Ale to nadal Ty? Jak się teraz czujesz i jaki emotikon wybierasz?",
            client_context={"client": "unit_test"},
        )
    finally:
        engine.shutdown()

    assert packet["runtime_version"] == VERSION
    cognitive = packet["cognitive_packets"]
    assert cognitive["schema_version"] == "cognitive_packets/v6_nlp_adapter_zip_profiles"
    assert cognitive["dominant_packet"] in {"continuity", "identity"}
    assert "continuity" in cognitive["packet_keys"]
    assert cognitive["state_emoticon"]["marker"] in {"🐾🫷", "🐾"}
    first = cognitive["packets"][0]
    assert first["dimensions"]
    assert first["response_steps"]
    assert first["grounding_policy"]
