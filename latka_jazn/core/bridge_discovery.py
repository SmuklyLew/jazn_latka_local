from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from latka_jazn.bridge_secure_gateway import SecureGatewayPolicy
from latka_jazn.config import JaznConfig
from latka_jazn.core.runtime_daemon import DEFAULT_DAEMON_HOST, DEFAULT_DAEMON_PORT, status_daemon
from latka_jazn.version import schema_version


LMSTUDIO_TRUTH_BOUNDARY = (
    "LM Studio jest lokalnym backendem językowym przez OpenAI-compatible API. "
    "Nie wymaga OPENAI_API_KEY i nie jest źródłem tożsamości, pamięci, stanu ani prawdy runtime Jaźni. "
    "Widoczna odpowiedź przechodzi przez istniejący runtime, walidację i truthful fallback."
)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def discover_runtime_bridges(
    config: JaznConfig,
    *,
    host: str = DEFAULT_DAEMON_HOST,
    port: int = DEFAULT_DAEMON_PORT,
) -> dict[str, Any]:
    root = Path(config.root).resolve()
    marker_path = root / "workspace_runtime" / "JAZN_ACTIVE_RUNTIME.json"
    marker = _read_json(marker_path)
    daemon = status_daemon(config, host=host, port=port)
    return {
        "schema_version": schema_version("runtime_bridge_discovery"),
        "active_root": str(root),
        "marker_path": str(marker_path),
        "marker_found": marker is not None,
        "marker": marker or {},
        "daemon_status": daemon,
        "local_chat": {
            "command": "python main.py --chat --session-id <id>",
            "meaning": "lokalna żywa pętla rozmowy; jeden JaznEngine do /exit, Ctrl+D albo EOF",
        },
        "chatgpt_bridge": {
            "command": "python main.py --chat-gpt --session-id <id>",
            "requires_api_key": False,
            "meaning": "most JSONL/copy-paste dla tej aplikacji ChatGPT; nie wykonuje żądania OpenAI API",
        },
        "openai_bridge": {
            "command": "python main.py --chat-open-ai --session-id <id>",
            "aliases": ["--chat-openai"],
            "requires_api_key": True,
            "env": "OPENAI_API_KEY",
            "meaning": "ten sam runtime Jaźni + OpenAI Responses API jako model_adapter językowy",
        },
        "lmstudio_bridge": {
            "command": "python main.py --chat-lm-studio --session-id <id>",
            "requires_api_key": False,
            "env": None,
            "meaning": "ten sam runtime Jaźni + lokalny backend LM Studio przez OpenAI-compatible Responses API z fallbackiem Chat Completions",
            "truth_boundary": LMSTUDIO_TRUTH_BOUNDARY,
        },
        "daemon": {
            "start": "python main.py --daemon-start",
            "status": "python main.py --daemon-status",
            "stop": "python main.py --daemon-stop",
            "active_state_contract": "active_trusted / active_degraded / inactive",
        },
        "secure_gateway_scaffold": SecureGatewayPolicy().to_dict(),
        "remote_mcp_candidate": {
            "status": "planned_scaffold_only",
            "requires_public_exposure_review": True,
            "requires_auth": True,
            "truth_boundary": "Remote MCP/gateway nie jest tym samym co lokalny daemon; wymaga oddzielnego zabezpieczenia, audytu danych i zgody na ekspozycję.",
        },
        "truth_boundary": (
            "GitHub i ZIP są źródłem kodu/snapshotu. Aktywna Jaźń wymaga żywego procesu, świeżego heartbeat i zgodnego active_root."
        ),
    }
