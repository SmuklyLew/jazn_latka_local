from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.core import runtime_daemon as runtime_daemon_module
from latka_jazn.core.startup_contract import build_startup_status
from latka_jazn.memory.runtime_write_access_contract import build_runtime_write_access_status


def _minimal_root(root: Path) -> None:
    (root / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (root / "VERSION.txt").write_text("v14.8.5.028\n", encoding="utf-8")
    (root / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")


def test_runtime_write_access_contract_initializes_clean_runtime_write_v1(tmp_path: Path) -> None:
    cfg = JaznConfig(root=tmp_path)

    before = build_runtime_write_access_status(cfg, initialize=False).to_dict()
    assert before["status"] == "missing_can_initialize"
    assert before["active_runtime_write_database"] is None

    after = build_runtime_write_access_status(cfg, initialize=True, writes_enabled=True).to_dict()

    assert after["ok"] is True
    assert after["status"] == "ready"
    assert after["memory_integrity"] == "ok"
    assert after["audit_integrity"] == "ok"
    assert (tmp_path / "memory/sqlite/runtime_write_v1/runtime_memory.sqlite3").exists()
    assert (tmp_path / "memory/sqlite/runtime_write_v1/runtime_audit.sqlite3").exists()
    assert (tmp_path / "memory/sqlite/runtime_write_v1/runtime_memory_shards.json").exists()
    assert (tmp_path / "memory/sqlite/runtime_write_v1/runtime_audit_shards.json").exists()


def test_startup_status_does_not_pretend_missing_runtime_write_db_is_ready(tmp_path: Path) -> None:
    _minimal_root(tmp_path)
    cfg = JaznConfig(root=tmp_path)

    status = build_startup_status(cfg).to_dict()

    assert status["runtime_write_access_status"]["status"] == "missing_can_initialize"
    assert status["active_runtime_write_database"].startswith("unavailable:")


def test_trusted_time_bridge_posts_injected_time_to_running_daemon(monkeypatch, tmp_path: Path) -> None:
    cfg = JaznConfig(root=tmp_path)
    calls: list[tuple[str, str, dict]] = []

    def fake_http_json(method: str, url: str, payload=None, *, timeout: float = 0.0):
        calls.append((method, url, payload or {}))
        return {"ok": True, "active_state": "active_trusted"}

    monkeypatch.setattr(runtime_daemon_module, "http_json", fake_http_json)
    monkeypatch.setattr(runtime_daemon_module, "status_daemon", lambda *args, **kwargs: {"active_state": "active_trusted"})

    result = runtime_daemon_module.inject_daemon_trusted_time(
        cfg,
        trusted_time_iso="2026-07-01T06:30:00+02:00",
        source="chatgpt_loader_time_test",
        max_age_seconds=600,
    )

    assert result["ok"] is True
    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/trusted-time")
    assert calls[0][2]["trusted_time_iso"] == "2026-07-01T06:30:00+02:00"
    assert calls[0][2]["source"] == "chatgpt_loader_time_test"


def test_first_person_feminine_voice_gate_rejects_third_person_self_voice() -> None:
    validation = RuntimeAnswerValidator().validate(
        user_text="Jesteś tu, Łatko?",
        body="Łatka jest tutaj w tej bieżącej turze i odpowiada z runtime.",
        route="ordinary_dialogue",
        detected_intent="short_free_dialogue",
    )

    assert validation.must_regenerate is True
    assert validation.mismatch_reason == "voice_perspective_mismatch"
    assert validation.required_repair_route == "first_person_feminine_voice_repair"


def test_first_person_feminine_voice_gate_allows_technical_report_about_latka() -> None:
    validation = RuntimeAnswerValidator().validate(
        user_text="Sprawdź kontrakt głosu Łatki.",
        body="Łatka jest nazwą speaking_identity w raporcie technicznym voice_source_contract.",
        route="runtime_diagnostic",
        detected_intent="runtime_behavior_diagnostic_request",
    )

    assert validation.mismatch_reason != "voice_perspective_mismatch"
