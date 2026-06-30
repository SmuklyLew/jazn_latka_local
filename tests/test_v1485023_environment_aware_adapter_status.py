from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import main
import pytest
from latka_jazn.config import JaznConfig
from latka_jazn.core.runtime_environment import detect_runtime_environment
from latka_jazn.model_adapters.factory import build_model_adapter_status

LMSTUDIO_TRUTH_BOUNDARY = (
    "LM Studio jest lokalnym backendem językowym przez OpenAI-compatible API. "
    "Nie wymaga OPENAI_API_KEY i nie jest źródłem tożsamości, pamięci, stanu ani prawdy runtime Jaźni. "
    "Widoczna odpowiedź przechodzi przez istniejący runtime, walidację i truthful fallback."
)


def _clear_host_env(monkeypatch) -> None:
    for key in list(__import__("os").environ):
        if key.startswith("CUA_DD_"):
            monkeypatch.delenv(key, raising=False)
    for key in [
        "JUPYTER_SERVER_OAI_PATH",
        "JAZN_ASSUME_CHATGPT_HOST",
        "JAZN_HOST_RUNTIME",
        "JAZN_VISIBLE_CHANNEL",
        "JAZN_MODEL_ADAPTER",
        "JAZN_LM_STUDIO_API_BASE",
        "JAZN_LM_STUDIO_MODEL",
        "OPENAI_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_environment_status_keeps_backend_and_effective_channel_separate(monkeypatch) -> None:
    _clear_host_env(monkeypatch)
    status = build_model_adapter_status(JaznConfig(), command="--chat-gpt-final-only")

    assert status["adapter_id"] == "chatgpt_runtime_adapter"
    assert status["selected_backend_adapter"] == "null_model_adapter"
    assert status["visible_channel_adapter"] == "chatgpt_runtime_adapter"
    assert status["effective_runtime_adapter"] == "chatgpt_runtime_adapter"
    assert status["base_backend_adapter_status"]["adapter_id"] == "null_model_adapter"
    assert status["runtime_environment"]["explicit_command"] == "--chat-gpt"
    assert status["runtime_environment"]["is_chatgpt_host_bridge"] is True
    assert status["requires_api_key"] is False


def test_environment_status_uses_terminal_adapter_for_chat_command(monkeypatch) -> None:
    _clear_host_env(monkeypatch)
    status = build_model_adapter_status(JaznConfig(), command="--chat")

    assert status["adapter_id"] == "terminal_runtime_adapter"
    assert status["selected_backend_adapter"] == "null_model_adapter"
    assert status["visible_channel_adapter"] == "terminal_runtime_adapter"
    assert status["runtime_environment"]["is_terminal_chat_loop"] is True


def test_model_adapter_status_detects_chatgpt_tool_container(monkeypatch, capsys) -> None:
    _clear_host_env(monkeypatch)
    monkeypatch.setenv("CUA_DD_PYTHON_TOOL", "true")

    assert main.main(["--model-adapter-status"]) == 0
    payload = json.loads(capsys.readouterr().out)
    status = payload["model_adapter_status"]

    assert status["adapter_id"] == "chatgpt_runtime_adapter"
    assert status["selected_backend_adapter"] == "null_model_adapter"
    assert status["effective_runtime_adapter"] == "chatgpt_runtime_adapter"
    assert status["runtime_environment"]["environment_host"] == "openai_chatgpt_tool_container"
    assert "detected_openai_chatgpt_tool_container" in status["runtime_environment"]["detection_basis"]


def test_default_builder_without_host_inference_stays_null(monkeypatch) -> None:
    _clear_host_env(monkeypatch)
    monkeypatch.setenv("CUA_DD_PYTHON_TOOL", "true")

    status = build_model_adapter_status(JaznConfig())

    assert status["adapter_id"] == "null_model_adapter"
    assert status["effective_runtime_adapter"] == "null_model_adapter"


def test_runtime_environment_env_marker_can_select_chatgpt(monkeypatch) -> None:
    _clear_host_env(monkeypatch)
    monkeypatch.setenv("JAZN_VISIBLE_CHANNEL", "chatgpt")

    env = detect_runtime_environment(JaznConfig())

    assert env.selected_backend_adapter == "null_model_adapter"
    assert env.visible_channel_adapter == "chatgpt_runtime_adapter"
    assert env.effective_runtime_adapter == "chatgpt_runtime_adapter"
    assert env.environment_host == "chatgpt_env_marker"


def test_startup_status_exposes_runtime_environment(monkeypatch, capsys) -> None:
    _clear_host_env(monkeypatch)
    monkeypatch.setenv("JAZN_HOST_RUNTIME", "chatgpt")

    assert main.main(["--startup-status-fast"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["runtime_environment"]["effective_runtime_adapter"] == "chatgpt_runtime_adapter"
    assert payload["model_adapter_status"]["selected_backend_adapter"] == "null_model_adapter"
    assert payload["model_adapter_status"]["adapter_id"] == "chatgpt_runtime_adapter"


@pytest.mark.parametrize(
    ("args", "expected_command", "expected_adapter"),
    [
        (["--chat-gpt", "--startup-status-fast"], "--chat-gpt", "chatgpt_runtime_adapter"),
        (["--chat-gpt-final-only", "--startup-status-fast"], "--chat-gpt", "chatgpt_runtime_adapter"),
        (["--chat", "--startup-status-fast"], "--chat", "terminal_runtime_adapter"),
    ],
)
def test_startup_status_combined_cli_mode_reports_effective_adapter(
    monkeypatch,
    capsys,
    args: list[str],
    expected_command: str,
    expected_adapter: str,
) -> None:
    _clear_host_env(monkeypatch)

    assert main.main(args) == 0
    payload = json.loads(capsys.readouterr().out)
    runtime_environment = payload["runtime_environment"]
    model_adapter_status = payload["model_adapter_status"]

    assert runtime_environment["explicit_command"] == expected_command
    assert runtime_environment["effective_runtime_adapter"] == expected_adapter
    assert runtime_environment["visible_channel_adapter"] == expected_adapter
    assert model_adapter_status["selected_backend_adapter"] == "null_model_adapter"
    assert model_adapter_status["effective_runtime_adapter"] == expected_adapter


def test_chat_openai_alias_reports_same_effective_adapter_as_chat_open_ai(monkeypatch, capsys) -> None:
    _clear_host_env(monkeypatch)

    assert main.main(["--chat-openai", "--model-adapter-status"]) == 0
    alias_payload = json.loads(capsys.readouterr().out)

    assert main.main(["--chat-open-ai", "--model-adapter-status"]) == 0
    canonical_payload = json.loads(capsys.readouterr().out)

    alias_status = alias_payload["model_adapter_status"]
    canonical_status = canonical_payload["model_adapter_status"]
    assert alias_status["effective_runtime_adapter"] == canonical_status["effective_runtime_adapter"] == "openai_responses_adapter"
    assert alias_status["runtime_environment"]["explicit_command"] == canonical_status["runtime_environment"]["explicit_command"] == "--chat-open-ai"


def test_chat_lm_studio_model_adapter_status_is_truthful_local_backend(monkeypatch, capsys) -> None:
    _clear_host_env(monkeypatch)

    assert main.main(["--chat-lm-studio", "--model-adapter-status"]) == 0
    payload = json.loads(capsys.readouterr().out)
    status = payload["model_adapter_status"]

    assert status["adapter_id"] == "lmstudio_runtime_adapter"
    assert status["provider"] == "lmstudio"
    assert status["effective_runtime_adapter"] == "lmstudio_runtime_adapter"
    assert status["runtime_environment"]["uses_openai_api"] is False
    assert status["runtime_environment"]["requires_openai_api_key"] is False
    assert status["status"] == "not_configured"
    assert status["failure_reason"] == "lmstudio_model_name_missing"
    assert status["truth_boundary"] == LMSTUDIO_TRUTH_BOUNDARY


def test_chat_lm_studio_startup_status_reports_explicit_command(monkeypatch, capsys) -> None:
    _clear_host_env(monkeypatch)

    assert main.main(["--chat-lm-studio", "--startup-status-fast"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["runtime_environment"]["explicit_command"] == "--chat-lm-studio"
    assert payload["runtime_environment"]["environment_host"] == "lmstudio_explicit_command"
    assert payload["runtime_environment"]["detection_basis"] == ["explicit_command:--chat-lm-studio"]
    assert payload["cli_capabilities"]["--chat-open-ai"] is True
    assert payload["cli_capabilities"]["--chat-openai"] is True
    assert payload["cli_capabilities"]["--chat-lm-studio"] is True


def _protected_fingerprint(root: Path) -> dict[str, tuple[int, int, str]]:
    result: dict[str, tuple[int, int, str]] = {}
    for name in ("memory", "workspace_runtime", "exports", "reports", "patchs"):
        base = root / name
        if not base.exists():
            continue
        for path in sorted(item for item in base.rglob("*") if item.is_file()):
            raw = path.read_bytes()
            result[path.relative_to(root).as_posix()] = (
                len(raw),
                path.stat().st_mtime_ns,
                hashlib.sha256(raw).hexdigest(),
            )
    return result


def test_lmstudio_and_adapter_status_paths_do_not_write_protected_directories(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _clear_host_env(monkeypatch)
    (tmp_path / "main.py").write_text("# status fixture\n", encoding="utf-8")
    (tmp_path / "VERSION.txt").write_text("v14.8.5.026b\n", encoding="utf-8")
    (tmp_path / "MANIFEST_CURRENT.json").write_text("{}\n", encoding="utf-8")

    runtime_dir = tmp_path / "memory" / "sqlite" / "runtime_write_v1"
    runtime_dir.mkdir(parents=True)
    memory_db = runtime_dir / "runtime_memory.sqlite3"
    audit_db = runtime_dir / "runtime_audit.sqlite3"
    for path in (memory_db, audit_db):
        with sqlite3.connect(path) as con:
            con.execute("CREATE TABLE marker(value TEXT)")
            con.execute("INSERT INTO marker(value) VALUES('unchanged')")
            con.commit()

    (runtime_dir / "runtime_memory_shards.json").write_text(
        json.dumps(
            {
                "active_write_shard": "0001",
                "shards": [
                    {
                        "shard_id": "0001",
                        "path": "memory/sqlite/runtime_write_v1/runtime_memory.sqlite3",
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (runtime_dir / "runtime_audit_shards.json").write_text(
        json.dumps(
            {
                "active_write_shard": "0001",
                "shards": [
                    {
                        "shard_id": "0001",
                        "path": "memory/sqlite/runtime_write_v1/runtime_audit.sqlite3",
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    before = _protected_fingerprint(tmp_path)

    commands = [
        ["--root", str(tmp_path), "--model-adapter-status"],
        ["--root", str(tmp_path), "--chat-lm-studio", "--model-adapter-status"],
        ["--root", str(tmp_path), "--chat-lm-studio", "--startup-status-fast"],
    ]
    for args in commands:
        assert main.main(args) == 0
        json.loads(capsys.readouterr().out)
        assert _protected_fingerprint(tmp_path) == before

    assert not (tmp_path / "workspace_runtime" / "project_startup_index_v14_6_10.json").exists()
    assert not list(runtime_dir.glob("*.sqlite3-shm"))
    assert not list(runtime_dir.glob("*.sqlite3-wal"))
