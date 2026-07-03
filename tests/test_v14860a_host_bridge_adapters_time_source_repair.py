from __future__ import annotations

from datetime import datetime, timezone
import io
import json
from types import SimpleNamespace

import pytest

import main
import latka_jazn.core.chat_command_contract as chat_command_module
import latka_jazn.core.clock as clock_module
from latka_jazn.config import JaznConfig
from latka_jazn.core.chat_command_contract import run_jsonl_chat_bridge
from latka_jazn.core.clock import TimeSample, TimeSourceResolver
from latka_jazn.core.engine import JaznEngine, _handler_body_can_cross_chatgpt_host_bridge
from latka_jazn.core.model_guided_response_synthesizer import ModelGuidedResponseSynthesizer
from latka_jazn.model_adapters.chatgpt_runtime_adapter import ChatgptRuntimeAdapter
from latka_jazn.model_adapters.null_model_adapter import NullModelAdapter


def _runtime_result(*, intent: str = "standalone_greeting", requires_host: bool = True) -> dict:
    fallback = "cannot_answer_directly" if requires_host else "not_fallback"
    return {
        "ok": True,
        "final_visible_text": "RuntimeTurnTruthGate fallback",
        "trace": {"turn_id": "turn-1", "trace_id": "trace-1", "timestamp_header": "[test-time]"},
        "conversation_decision": {
            "detected_user_intent": intent,
            "route": "ordinary_dialogue",
            "handler_name": "RuntimeTurnTruthGate",
            "requires_host_model": requires_host,
        },
        "runtime_turn_contract": {
            "requires_host_model": requires_host,
            "fallback_classification": fallback,
            "can_generate_model_guided_speech": False,
        },
        "final_response_contract": {
            "requires_host_model": requires_host,
            "fallback_classification": fallback,
        },
    }


class _FakeRuntimeSession:
    def __init__(self, *args, session_id=None, **kwargs) -> None:
        self.state = type("State", (), {"session_id": session_id or "test-session"})()

    def process_user_text(self, user_text: str, **kwargs) -> dict:
        return _runtime_result()

    def close(self) -> None:
        pass


@pytest.mark.parametrize("intent", ["standalone_greeting", "casual_greeting", "ordinary_conversation"])
def test_chatgpt_jsonl_turn_requests_host_generation_for_dialogue(monkeypatch, intent: str) -> None:
    class IntentRuntimeSession(_FakeRuntimeSession):
        def process_user_text(self, user_text: str, **kwargs) -> dict:
            return _runtime_result(intent=intent)

    monkeypatch.setattr(chat_command_module, "JaznRuntimeSession", IntentRuntimeSession)
    stdout = io.StringIO()

    assert run_jsonl_chat_bridge(
        config=JaznConfig(),
        session_id="host-phase",
        no_carryover=True,
        command="--chat-gpt",
        stdin=io.StringIO("Hej\n"),
        stdout=stdout,
        output_mode="jsonl",
    ) == 0

    payload = json.loads(stdout.getvalue())
    assert payload["conversation_decision"]["detected_user_intent"] == intent
    assert payload["chatgpt_host_bridge"]["phase"] == "host_visible_generation_requested"
    assert payload["chatgpt_host_bridge"]["host_must_generate_visible_reply"] is True


def test_final_only_promotes_required_host_phase_to_jsonl_envelope(monkeypatch) -> None:
    monkeypatch.setattr(chat_command_module, "JaznRuntimeSession", _FakeRuntimeSession)
    stdout = io.StringIO()

    run_jsonl_chat_bridge(
        config=JaznConfig(),
        session_id="final-only-host-phase",
        no_carryover=True,
        command="--chat-gpt",
        stdin=io.StringIO("Hej\n"),
        stdout=stdout,
        output_mode="final_visible_text",
    )

    payload = json.loads(stdout.getvalue())
    assert payload["chatgpt_host_bridge"]["phase"] == "host_visible_generation_requested"
    assert payload["chat_bridge_output"]["effective_mode"] == "jsonl_host_bridge_envelope"
    assert stdout.getvalue().strip() != "RuntimeTurnTruthGate fallback"


def test_real_chatgpt_one_shot_cli_does_not_hide_required_host_phase(monkeypatch, tmp_path, capsys) -> None:
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text("test\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("JAZN_CHATGPT_PREFER_DAEMON", "0")

    assert main.main(["--root", str(tmp_path), "--chat-gpt", "--", "Hej"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["chatgpt_host_bridge"]["phase"] == "host_visible_generation_requested"
    assert payload["chat_bridge_output"]["effective_mode"] == "jsonl_host_bridge_envelope"
    assert payload["chatgpt_host_bridge"]["host_must_generate_visible_reply"] is True


def test_daemon_fast_path_attaches_same_host_contract(monkeypatch, tmp_path, capsys) -> None:
    cfg = JaznConfig(root=tmp_path)
    marker = tmp_path / "workspace_runtime" / "JAZN_ACTIVE_RUNTIME.json"
    marker.parent.mkdir(parents=True)
    marker.write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("JAZN_CHATGPT_PREFER_DAEMON", "1")
    monkeypatch.setattr(main, "status_daemon", lambda *args, **kwargs: {"active_state": "active_trusted", "endpoint_reachable": True})
    monkeypatch.setattr(main, "chat_daemon", lambda *args, **kwargs: _runtime_result())

    result = main._try_chat_gpt_one_shot_via_daemon(
        cfg=cfg,
        text="Hej",
        session_id="daemon-session",
        no_carryover=True,
        host="127.0.0.1",
        port=8765,
        timeout=1.0,
        output_mode="final_visible_text",
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["chat_bridge"]["daemon_fast_path"] is True
    assert payload["chatgpt_bridge"] == payload["chat_bridge"]
    assert payload["chatgpt_host_bridge"]["phase"] == "host_visible_generation_requested"
    assert payload["chatgpt_host_bridge"]["host_must_generate_visible_reply"] is True


def _synthesis(adapter) -> dict:
    return ModelGuidedResponseSynthesizer().synthesize(
        adapter=adapter,
        user_text="Hej",
        draft_body="draft",
        detected_intent="standalone_greeting",
        route="ordinary_dialogue",
        cognitive_frame={},
        response_policy={},
    ).to_dict()


def test_adapter_diagnostics_distinguish_chatgpt_host_from_null_model() -> None:
    host_status = ChatgptRuntimeAdapter().describe()
    host = _synthesis(ChatgptRuntimeAdapter())
    null = _synthesis(NullModelAdapter())

    assert host_status["can_generate_model_guided_speech"] is False
    assert host_status["can_attempt_model_guided_speech"] is False
    assert host_status["host_bridge_phase"] == "host_visible_generation_requested"
    assert host["status"] == "host_visible_generation_requested"
    assert host["reason"] == "host_chatgpt_bridge_requires_external_visible_reply"
    assert host["reason"] != "model_adapter_not_configured"
    assert null["reason"] == "null_model_adapter_has_no_generation_capability"


def test_real_engine_chatgpt_greeting_requires_host_without_relaxing_template_gate(tmp_path) -> None:
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text("test\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")
    engine = JaznEngine(
        JaznConfig(
            root=tmp_path,
            model_adapter="chatgpt_runtime_adapter",
            model_name="chatgpt_host_model",
            network_time_first=False,
            memory_db_name="runtime-test.sqlite3",
        )
    )
    try:
        payload = engine.process_turn(
            "Hej.",
            client_context={"client": "pytest", "lifecycle": "chatgpt_bridge_jsonl", "no_carryover": True},
        ).to_dict()
    finally:
        engine.shutdown()

    decision = payload["conversation_decision"]
    assert decision["requires_host_model"] is True
    assert decision["fallback_classification"] == "cannot_answer_directly"
    assert decision["handler_name"] == "RuntimeTurnTruthGate"
    assert decision["model_guided_synthesis"]["reason"] == "host_chatgpt_bridge_requires_external_visible_reply"
    assert payload["runtime_turn_contract"]["requires_host_model"] is True


def test_null_adapter_keeps_truthful_final_fallback(tmp_path) -> None:
    (tmp_path / "main.py").write_text("print('stub')\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text("test\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")
    engine = JaznEngine(
        JaznConfig(root=tmp_path, model_adapter="null", network_time_first=False, memory_db_name="runtime-null.sqlite3")
    )
    try:
        payload = engine.process_turn(
            "Hej.",
            client_context={"client": "pytest", "lifecycle": "one_shot", "no_carryover": True},
        ).to_dict()
    finally:
        engine.shutdown()

    assert payload["conversation_decision"]["handler_name"] == "RuntimeTurnTruthGate"
    assert payload["final_response_contract"]["fallback_classification"] == "cannot_answer_directly"
    assert "wymaga generacji przez host/model" in payload["final_visible_text"]


def test_only_validated_non_template_handler_can_cross_chatgpt_visible_bridge() -> None:
    status = ChatgptRuntimeAdapter().describe()
    handler = SimpleNamespace(body="Konkretna odpowiedź handlera.")
    validation = SimpleNamespace(accepted=True)
    common = {
        "adapter_status": status,
        "handler_result": handler,
        "handler_missing": [],
        "handler_required": ["answer"],
        "handler_satisfied": {"answer"},
        "validation": validation,
    }

    assert _handler_body_can_cross_chatgpt_host_bridge(template_origin={}, **common) is True
    assert _handler_body_can_cross_chatgpt_host_bridge(
        template_origin={"template_id": "tpl_forbidden_dynamic_speech"}, **common
    ) is False


@pytest.mark.parametrize(
    ("env", "expected_shell"),
    [
        ({"PSModulePath": "x", "WT_SESSION": "1"}, "powershell"),
        ({"ComSpec": r"C:\\Windows\\System32\\cmd.exe"}, "cmd"),
        ({"SHELL": "/bin/bash", "TERM": "xterm"}, "bash"),
        ({}, "unknown"),
    ],
)
def test_time_resolver_detects_shell_without_crashing(env: dict[str, str], expected_shell: str) -> None:
    resolver = TimeSourceResolver(env=env)
    result = resolver.resolve(TimeSample(datetime.now(timezone.utc), "local_fallback", False)).to_dict()

    assert result["shell"] == expected_shell
    assert result["timestamp_source"] == "system_local"
    assert result["timestamp_trusted"] is False


def test_time_resolver_reports_aware_cross_platform_contract(monkeypatch) -> None:
    monkeypatch.setattr(clock_module.platform, "system", lambda: "Linux")
    result = TimeSourceResolver(env={"SHELL": "/bin/bash"}).resolve(
        TimeSample(datetime.now(timezone.utc), "test_network_time", True)
    ).to_dict()

    assert result["platform_system"] == "Linux"
    assert result["timezone_key"] == "Europe/Warsaw"
    assert result["timestamp_source"] == "network"
    assert result["timestamp_trusted"] is True
    assert result["timestamp_freshness_ok"] is True
    assert datetime.fromisoformat(result["utc_iso"]).tzinfo is not None
    assert datetime.fromisoformat(result["local_iso"]).tzinfo is not None
    assert result["human_time_header"].startswith("[🕒 ")


def test_missing_iana_database_is_controlled_degraded_status(monkeypatch) -> None:
    def missing_zoneinfo(key: str):
        raise clock_module.ZoneInfoNotFoundError(key)

    monkeypatch.setattr(clock_module, "ZoneInfo", missing_zoneinfo)
    resolver = TimeSourceResolver(env={"ComSpec": r"C:\\Windows\\System32\\cmd.exe"})
    result = resolver.resolve(TimeSample(datetime.now(timezone.utc), "local_fallback", False)).to_dict()

    assert result["status"] == "active_degraded"
    assert result["timezone_status"] == "degraded_fixed_offset"
    assert result["degradation_reason"]
    assert result["timestamp_source"] != "network"
