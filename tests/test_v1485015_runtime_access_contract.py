from __future__ import annotations

from latka_jazn.core.active_runtime_access_contract import (
    build_all_runtime_access_contracts,
    build_runtime_access_contract,
)
from latka_jazn.version import PACKAGE_RELEASE_NAME, PACKAGE_VERSION, RUNTIME_CONTRACT_VERSION


def test_runtime_version_is_bumped_to_1485015() -> None:
    assert PACKAGE_VERSION == "v14.8.5.015"
    assert RUNTIME_CONTRACT_VERSION == PACKAGE_VERSION
    assert PACKAGE_RELEASE_NAME == "runtime-bump-active-runtime-access-contract"


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
