from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core import runtime_daemon as runtime_daemon_module
from latka_jazn.core.clock import WarsawClock
from latka_jazn.core.runtime_daemon import (
    DEFAULT_DAEMON_HOST,
    JaznDaemonHandler,
    JaznDaemonServer,
    daemon_default_marker_path,
)
from latka_jazn.core.runtime_truth_gate import daemon_active_state, time_trust_state
from latka_jazn.tools.active_extraction_cache import write_active_runtime_marker
from latka_jazn.version import PACKAGE_VERSION


def _minimal_runtime_root(tmp_path: Path) -> JaznConfig:
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text(f"{PACKAGE_VERSION}\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")
    return JaznConfig(root=tmp_path)


def test_liveness_no_longer_depends_on_trusted_network_time() -> None:
    assert daemon_active_state(
        marker_found=True,
        pid_alive=True,
        ping_ok=True,
        timestamp_trusted=False,
    ) == "active_trusted"
    assert time_trust_state(
        timestamp_trusted=False,
        timestamp_source="local_fallback",
    ) == "local_machine_unverified"


def test_daemon_marker_local_time_is_active_with_separate_time_state(monkeypatch, tmp_path: Path) -> None:
    cfg = _minimal_runtime_root(tmp_path)
    marker_path = daemon_default_marker_path(tmp_path)
    write_active_runtime_marker(tmp_path, marker_output=marker_path)

    def fake_contract(config, *, network_first=None, timeout_seconds=None, reason="direct"):
        return {
            "trusted": False,
            "source": "local_fallback",
            "error": "network_time_unavailable",
            "timestamp_header": "[test-local-time]",
            "daemon_status_time_mode": "local_machine_unverified_nonblocking",
            "daemon_status_refresh_reason": reason,
            "does_not_block_startup": True,
        }

    monkeypatch.setattr(runtime_daemon_module, "daemon_timestamp_contract", fake_contract)
    server = JaznDaemonServer((DEFAULT_DAEMON_HOST, 0), JaznDaemonHandler, config=cfg, marker_path=marker_path)
    try:
        payload = server.write_marker()
        lite = server.lite_status_payload(endpoint="/ready", latency_ms=1)
    finally:
        server.server_close()

    assert payload["active_state"] == "active_trusted"
    assert payload["runtime_active_state"] == "active_trusted"
    assert payload["time_trust_state"] == "network_time_unavailable_local_machine_unverified"
    assert payload["timestamp_trusted"] is False
    assert payload["timestamp_does_not_block_startup"] is True
    assert lite["ok"] is True
    assert lite["active_state"] == "active_trusted"
    assert lite["time_trust_state"] == "network_time_unavailable_local_machine_unverified"


def test_network_time_check_failure_reports_local_fallback_without_startup_block(monkeypatch) -> None:
    clock = WarsawClock("Europe/Warsaw")
    monkeypatch.setattr(clock, "_network_time", lambda *args, **kwargs: None)
    result = clock.network_time_check(timeout_seconds=0.01)

    assert result["status"] == "unavailable"
    assert result["does_not_block_startup"] is True
    assert result["time_trust_state"] == "network_time_unavailable_local_machine_unverified"
    assert result["fallback_sample"]["source"] == "local_fallback"
    assert result["fallback_sample"]["trusted"] is False
