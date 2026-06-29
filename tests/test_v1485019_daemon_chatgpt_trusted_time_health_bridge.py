from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core import runtime_daemon as runtime_daemon_module
from latka_jazn.core.runtime_daemon import (
    DEFAULT_DAEMON_HOST,
    JaznDaemonHandler,
    JaznDaemonServer,
    apply_daemon_trusted_time_env,
    chat_daemon,
    daemon_default_marker_path,
)
from latka_jazn.version import PACKAGE_VERSION


def _minimal_runtime_root(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text(f"{PACKAGE_VERSION}\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")


def test_apply_daemon_trusted_time_env_sets_only_explicit_values(monkeypatch) -> None:
    monkeypatch.delenv("JAZN_TRUSTED_TIME_ISO", raising=False)
    monkeypatch.delenv("JAZN_TRUSTED_TIME_SOURCE", raising=False)
    monkeypatch.delenv("JAZN_TRUSTED_TIME_MAX_AGE_SECONDS", raising=False)

    result = apply_daemon_trusted_time_env(
        trusted_time_iso="2026-06-28T22:50:00+00:00",
        source="chatgpt_loader_test",
        max_age_seconds=600,
    )

    assert result["trusted_time_env_present"] is True
    assert result["trusted_time_source"] == "chatgpt_loader_test"
    assert result["trusted_time_max_age_seconds"] == 600
    assert "JAZN_TRUSTED_TIME_ISO" in result["changed_env"]


def test_lite_status_payload_is_fast_and_does_not_require_marker_rewrite(monkeypatch, tmp_path: Path) -> None:
    _minimal_runtime_root(tmp_path)
    marker_path = daemon_default_marker_path(tmp_path)
    cfg = JaznConfig(root=tmp_path)

    calls = []

    def fake_contract(config, *, network_first=None, timeout_seconds=None, reason="direct"):
        calls.append((network_first, timeout_seconds, reason))
        return {
            "trusted": False,
            "source": "local_fallback",
            "timestamp_header": "[test]",
            "daemon_status_time_mode": "degraded_local_fallback",
            "daemon_status_refresh_reason": reason,
        }

    monkeypatch.setattr(runtime_daemon_module, "daemon_timestamp_contract", fake_contract)
    server = JaznDaemonServer((DEFAULT_DAEMON_HOST, 0), JaznDaemonHandler, config=cfg, marker_path=marker_path)
    try:
        payload = server.lite_status_payload(endpoint="/ready", latency_ms=1)
    finally:
        server.server_close()

    assert payload["endpoint"] == "/ready"
    assert payload["active_state"] == "inactive"
    assert payload["timestamp_contract"]["daemon_status_fast_path"] is True
    assert marker_path.exists() is False
    assert calls
    assert all(call[0] is False for call in calls)


def test_status_daemon_recommends_trusted_time_when_alive_but_degraded(monkeypatch, tmp_path: Path) -> None:
    _minimal_runtime_root(tmp_path)
    marker_path = daemon_default_marker_path(tmp_path)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(
        '{"daemon_pid": 4321, "runtime_daemon": {"pid": 4321}, "runtime_process_active": true, "last_heartbeat_at_utc": "'
        + runtime_daemon_module.utc_now_iso()
        + '", "heartbeat_interval_seconds": 30.0}',
        encoding="utf-8",
    )
    cfg = JaznConfig(root=tmp_path)

    def fake_probe(host: str, port: int, *, timeout: float = 0.75):
        return {
            "active_state": "active_degraded",
            "daemon_pid": 4321,
            "runtime_daemon": {"pid": 4321},
            "runtime_process_active": True,
            "timestamp_trusted": False,
        }, None, "/ready"

    monkeypatch.setattr(runtime_daemon_module, "pid_is_alive", lambda pid: True)
    monkeypatch.setattr(runtime_daemon_module, "_probe_daemon_status", fake_probe)

    status = runtime_daemon_module.status_daemon(cfg)

    assert status["active_state"] == "active_degraded"
    assert status["ping_endpoint"] == "/ready"
    assert status["recommended_repair"]["kind"] == "trusted_time_missing"


def test_chat_daemon_returns_structured_error_on_empty_message(tmp_path: Path) -> None:
    _minimal_runtime_root(tmp_path)
    cfg = JaznConfig(root=tmp_path)

    result = chat_daemon(cfg, "   ")

    assert result["ok"] is False
    assert result["error_code"] == "empty_message"
