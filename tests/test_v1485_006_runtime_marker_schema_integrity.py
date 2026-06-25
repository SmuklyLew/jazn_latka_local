from __future__ import annotations

import json
from pathlib import Path

from latka_jazn.core.affect_mixer import SCHEMA_VERSION as AFFECT_SCHEMA_VERSION
from latka_jazn.core.final_response_contract import FinalResponseContract
from latka_jazn.core.runtime_rendering_modes import SCHEMA_VERSION as RENDERING_SCHEMA_VERSION
from latka_jazn.core.runtime_session import SCHEMA_VERSION as RUNTIME_SESSION_SCHEMA_VERSION
from latka_jazn.core.session_provenance import SCHEMA_VERSION as SESSION_PROVENANCE_SCHEMA_VERSION
from latka_jazn.core.session_provenance import validate_final_visible_integrity
from latka_jazn.core.template_registry import SCHEMA_VERSION as TEMPLATE_REGISTRY_SCHEMA_VERSION
from latka_jazn.core.turn_response_policy import SCHEMA_VERSION as TURN_POLICY_SCHEMA_VERSION
from latka_jazn.model_adapters.null_model_adapter import NullModelAdapter
from latka_jazn.tools.active_extraction_cache import build_active_runtime_status, write_active_runtime_marker
from latka_jazn.version import PACKAGE_VERSION, schema_version

EXPECTED_VERSION = "v14.8.5.006"


def _minimal_runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / "jazn_root"
    root.mkdir()
    (root / "VERSION.txt").write_text(EXPECTED_VERSION, encoding="utf-8")
    (root / "main.py").write_text("# start file\n", encoding="utf-8")
    (root / "MANIFEST_CURRENT.json").write_text(
        json.dumps({"version": EXPECTED_VERSION, "start_file": "main.py"}, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return root


def test_package_version_is_current_006() -> None:
    assert PACKAGE_VERSION == EXPECTED_VERSION


def test_marker_drift_requires_refresh_but_not_reextraction(tmp_path: Path) -> None:
    root = _minimal_runtime_root(tmp_path)
    marker = tmp_path / "JAZN_ACTIVE_RUNTIME.json"
    marker.write_text(
        json.dumps(
            {
                "active_root": str(root),
                "version": "v14.8.5.002",
                "manifest_current_sha256": "stale",
                "valid": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    status = build_active_runtime_status(root, marker_output=marker)

    assert status["version"] == EXPECTED_VERSION
    assert status["should_reuse_existing_extraction"] is True
    assert status["marker_refresh_required"] is True
    assert status["marker_differs"] is True
    assert "marker_version_differs_or_missing" in status["cache_miss_reasons"]
    assert "marker_manifest_sha256_differs_or_missing" in status["cache_miss_reasons"]


def test_written_marker_clears_marker_miss_reasons(tmp_path: Path) -> None:
    root = _minimal_runtime_root(tmp_path)
    marker = tmp_path / "JAZN_ACTIVE_RUNTIME.json"

    written = write_active_runtime_marker(root, marker_output=marker)
    status = build_active_runtime_status(root, marker_output=marker)

    assert written["should_reuse_existing_extraction"] is True
    assert status["should_reuse_existing_extraction"] is True
    assert status["marker_refresh_required"] is False
    assert status["marker_differs"] is False
    assert "marker_version_matches" in status["cache_hit_reasons"]
    assert "marker_manifest_sha256_matches" in status["cache_hit_reasons"]


def test_final_response_contract_carries_visible_integrity() -> None:
    timestamp = "[🕒 2026-06-25 00:00:00 GMT+2, czwartek, Europe/Warsaw]"
    contract = FinalResponseContract.build(
        turn_id="turn-test",
        trace_id="trace-test",
        runtime_version=EXPECTED_VERSION,
        timestamp_header=timestamp,
        timezone="Europe/Warsaw",
        state_emoticon="🌿",
        body="Jestem przy Tobie.",
        conversation_decision={"route": "ordinary_dialogue", "detected_user_intent": "ordinary_conversation"},
    )

    assert contract.schema_version == schema_version("final_response_contract")
    assert contract.final_visible_integrity is not None
    assert contract.final_visible_integrity["valid"] is True
    assert contract.final_visible_integrity["timestamp_present"] is True


def test_session_integrity_schema_is_current() -> None:
    timestamp = "[🕒 2026-06-25 00:00:00 GMT+2, czwartek, Europe/Warsaw]"
    result = {
        "trace": {"timestamp_header": timestamp},
        "final_visible_text": f"{timestamp} 🌿\nJestem przy Tobie.",
        "runtime_provenance": {"visible_answer_text": f"{timestamp} 🌿\nJestem przy Tobie."},
    }
    integrity = validate_final_visible_integrity(result)
    assert integrity["schema_version"] == schema_version("final_visible_integrity")
    assert integrity["valid"] is True


def test_active_schema_labels_are_current_for_runtime_surface() -> None:
    expected = {
        schema_version("affect_mixer"),
        schema_version("runtime_rendering_modes"),
        schema_version("runtime_session"),
        schema_version("session_provenance"),
        schema_version("template_registry"),
        schema_version("turn_response_policy"),
        schema_version("null_model_adapter"),
    }
    actual = {
        AFFECT_SCHEMA_VERSION,
        RENDERING_SCHEMA_VERSION,
        RUNTIME_SESSION_SCHEMA_VERSION,
        SESSION_PROVENANCE_SCHEMA_VERSION,
        TEMPLATE_REGISTRY_SCHEMA_VERSION,
        TURN_POLICY_SCHEMA_VERSION,
        NullModelAdapter().describe()["schema_version"],
    }
    assert actual == expected
