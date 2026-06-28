from __future__ import annotations

from pathlib import Path

from latka_jazn.core.active_runtime_access_contract import (
    build_all_runtime_access_contracts,
    build_runtime_access_contract,
)
from latka_jazn.tools.active_extraction_cache import write_active_runtime_marker
from latka_jazn.version import PACKAGE_RELEASE_NAME, PACKAGE_VERSION, RUNTIME_CONTRACT_VERSION


def test_runtime_version_is_current_route_contract_audit() -> None:
    assert PACKAGE_VERSION == "v14.8.5.016.2"
    assert RUNTIME_CONTRACT_VERSION == PACKAGE_VERSION
    assert PACKAGE_RELEASE_NAME == "route-contract-audit"


def test_active_runtime_access_contract_modes_are_explicit() -> None:
    contracts = build_all_runtime_access_contracts()

    assert set(contracts) == {
        "local_daemon",
        "chatgpt_turn_command",
        "simulated_active_marker",
    }
    assert contracts["local_daemon"]["continuous_process_confirmed"] is True
    assert contracts["chatgpt_turn_command"]["continuous_process_confirmed"] is False
    assert contracts["simulated_active_marker"]["memory_write_allowed"] is False


def test_simulated_marker_does_not_claim_live_runtime() -> None:
    contract = build_runtime_access_contract("simulated_active_marker")

    assert contract.continuous_process_confirmed is False
    assert contract.memory_write_allowed is False
    assert "does not prove" in contract.description


def test_write_active_runtime_marker_clears_post_write_marker_flags(tmp_path: Path) -> None:
    root = tmp_path / "active_root"
    root.mkdir()
    (root / "VERSION.txt").write_text("v14.8.5.015\n", encoding="utf-8")
    (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")

    marker_path = root / "workspace_runtime" / "JAZN_ACTIVE_RUNTIME.json"
    marker = write_active_runtime_marker(root, marker_output=marker_path)

    assert marker["cache_miss_reasons"] == []
    assert marker["marker_refresh_required"] is False
    assert marker["marker_differs"] is False
    assert marker_path.exists()
