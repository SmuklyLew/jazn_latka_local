from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any, Literal, TextIO

from latka_jazn.config import JaznConfig
from latka_jazn.core.runtime_session import JaznRuntimeSession
from latka_jazn.core.turn_timeout import RuntimeSessionWorker, RuntimeTurnTimeoutError, runtime_turn_timeout_seconds
from latka_jazn.version import schema_version

ACCEPTED_CHATGPT_INPUT_FIELDS = ("message", "text", "user_text", "content", "prompt")
CHATGPT_BRIDGE_PROTOCOL = schema_version("chatgpt_bridge_jsonl")
CHAT_OPENAI_PROTOCOL = schema_version("chat_open_ai_jsonl")
CHAT_LMSTUDIO_PROTOCOL = schema_version("chat_lm_studio_jsonl")
CHAT_BRIDGE_OUTPUT_MODES = ("jsonl", "final_visible_text")
BridgeOutputMode = Literal["jsonl", "final_visible_text"]


@dataclass(slots=True)
class ChatCommandContract:
    command: str
    mode: str
    requires_api_key: bool
    uses_openai_api: bool
    keeps_process_alive: bool
    engine_reused_between_turns: bool
    accepted_input_fields: tuple[str, ...] = ACCEPTED_CHATGPT_INPUT_FIELDS
    accepted_input_shapes: tuple[str, ...] = (
        "plain_text_line",
        "json_object.message",
        "json_object.text",
        "json_object.user_text",
        "json_object.content",
        "json_object.prompt",
        "json_object.messages[].content",
    )
    output_modes: tuple[str, ...] = CHAT_BRIDGE_OUTPUT_MODES
    truth_boundary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def chat_gpt_contract() -> ChatCommandContract:
    return ChatCommandContract(
        command="--chat-gpt",
        mode="chatgpt_bridge_without_api_key",
        requires_api_key=False,
        uses_openai_api=False,
        keeps_process_alive=True,
        engine_reused_between_turns=True,
        truth_boundary=(
            "--chat-gpt jest jedyną kanoniczną flagą mostu dla aplikacji ChatGPT/copy-paste/JSONL. "
            "Nie wymaga OPENAI_API_KEY i nie wykonuje żądań do OpenAI API. "
            "Użycie z wiadomością po `--` wypisuje final_visible_text dla człowieka; stdin JSONL zachowuje pełny pakiet dla narzędzi. "
            "Legacy aliasy `--chat-gpt-final-only` i `--chat-gpt --final-only` są tylko zgodnością wsteczną i nie zmieniają routingu."
        ),
    )


def chat_open_ai_contract() -> ChatCommandContract:
    return ChatCommandContract(
        command="--chat-open-ai",
        mode="openai_api_model_adapter_bridge",
        requires_api_key=True,
        uses_openai_api=True,
        keeps_process_alive=True,
        engine_reused_between_turns=True,
        truth_boundary=(
            "--chat-open-ai uruchamia ten sam runtime Jaźni, ale językową warstwę model_adapter kieruje przez OpenAI Responses API. "
            "OPENAI_API_KEY jest wymagany. Model jest kanałem języka, nie źródłem tożsamości ani pamięci Jaźni."
        ),
    )


def chat_lm_studio_contract() -> ChatCommandContract:
    return ChatCommandContract(
        command="--chat-lm-studio",
        mode="lmstudio_openai_compatible_local_backend_contract",
        requires_api_key=False,
        uses_openai_api=False,
        keeps_process_alive=True,
        engine_reused_between_turns=True,
        truth_boundary=(
            "LM Studio jest lokalnym backendem językowym przez OpenAI-compatible API. "
            "Nie wymaga OPENAI_API_KEY i nie jest źródłem tożsamości, pamięci, stanu ani prawdy runtime Jaźni. "
            "Widoczna odpowiedź przechodzi przez istniejący runtime, walidację i truthful fallback."
        ),
    )


def command_contract(command: str) -> dict[str, Any]:
    if command == "--chat-open-ai":
        return chat_open_ai_contract().to_dict()
    if command == "--chat-lm-studio":
        return chat_lm_studio_contract().to_dict()
    if command == "--chat-gpt":
        return chat_gpt_contract().to_dict()
    raise ValueError(f"unknown chat command contract: {command}")


def extract_user_text_from_payload(payload: dict[str, Any]) -> tuple[str, str, str]:
    for candidate in ACCEPTED_CHATGPT_INPUT_FIELDS:
        value = payload.get(candidate)
        if value is not None and str(value).strip():
            return str(value).strip(), "json", candidate

    messages = payload.get("messages")
    if isinstance(messages, list):
        fallback_content = ""
        fallback_field = "messages[].content"
        for item in messages:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if content is None:
                continue
            if isinstance(content, list):
                parts: list[str] = []
                for part in content:
                    if isinstance(part, dict):
                        text_part = part.get("text")
                        if text_part is not None:
                            parts.append(str(text_part))
                    elif part is not None:
                        parts.append(str(part))
                content_text = "".join(parts).strip()
            else:
                content_text = str(content).strip()
            if not content_text:
                continue
            fallback_content = content_text
            if str(item.get("role") or "").lower() == "user":
                return content_text, "json_chat_messages", "messages[user].content"
        if fallback_content:
            return fallback_content, "json_chat_messages", fallback_field

    return "", "json", "<missing>"



def apply_chatgpt_cli_settings(config: JaznConfig) -> JaznConfig:
    """Select the truthful ChatGPT host adapter for the --chat-gpt bridge."""
    config.model_adapter = "chatgpt_runtime_adapter"
    if not os.environ.get("JAZN_MODEL_NAME"):
        config.model_name = os.environ.get("JAZN_CHATGPT_MODEL_NAME", "chatgpt_host_model").strip() or "chatgpt_host_model"
    return config


def apply_chat_cli_settings(config: JaznConfig) -> JaznConfig:
    """Select the truthful local terminal adapter for the --chat loop."""
    config.model_adapter = "terminal_runtime_adapter"
    if not os.environ.get("JAZN_TERMINAL_MODEL_NAME"):
        config.terminal_model_name = "terminal_visible_layer"
    return config


def apply_openai_cli_settings(
    config: JaznConfig,
    *,
    model: str | None = None,
    api_base: str | None = None,
    timeout_seconds: float | None = None,
    max_output_tokens: int | None = None,
) -> JaznConfig:
    config.model_adapter = "openai_responses_adapter"
    if model:
        config.model_name = model
    if api_base:
        config.model_api_base = api_base.rstrip("/")
    if timeout_seconds is not None:
        config.model_timeout_seconds = float(timeout_seconds)
    if max_output_tokens is not None:
        config.model_max_output_tokens = int(max_output_tokens)
    return config


def apply_lm_studio_cli_settings(
    config: JaznConfig,
    *,
    model: str | None = None,
    api_base: str | None = None,
    timeout_seconds: float | None = None,
    max_output_tokens: int | None = None,
) -> JaznConfig:
    config.model_adapter = "lmstudio_runtime_adapter"
    if model:
        config.lm_studio_model_name = model
    if api_base:
        config.lm_studio_api_base = api_base.rstrip("/")
    if timeout_seconds is not None:
        config.lm_studio_timeout_seconds = float(timeout_seconds)
    if max_output_tokens is not None:
        config.lm_studio_max_output_tokens = int(max_output_tokens)
    return config


def extract_final_visible_text_from_result(payload: dict[str, Any]) -> str:
    """Return the visible Łatka reply from a chat bridge payload.

    The JSONL protocol remains the default source of truth. This helper is only
    for the human-readable --chat-gpt rendering mode.
    """
    final: Any = payload.get("final_visible_text")
    final_contract = payload.get("final_response_contract")
    if final is None and isinstance(final_contract, dict):
        final = final_contract.get("final_visible_text")
    provenance = payload.get("runtime_provenance")
    if final is None and isinstance(provenance, dict):
        final = provenance.get("visible_answer_text")
    if final is None:
        final = payload.get("exact_runtime_text")
    if final is None and payload.get("error"):
        error_code = str(payload.get("error_code") or "chat_bridge_error")
        final = f"[{error_code}] {payload.get('error')}"
    return str(final or "").strip()


def write_chat_bridge_payload(stdout: TextIO, payload: dict[str, Any], *, output_mode: BridgeOutputMode = "jsonl") -> None:
    if output_mode == "final_visible_text":
        stdout.write(extract_final_visible_text_from_result(payload) + "\n")
    else:
        stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    stdout.flush()


def run_jsonl_chat_bridge(
    *,
    config: JaznConfig,
    session_id: str | None,
    no_carryover: bool,
    command: str,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    require_openai_api_key: bool = False,
    output_mode: BridgeOutputMode = "jsonl",
) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    if output_mode not in CHAT_BRIDGE_OUTPUT_MODES:
        raise ValueError(f"unsupported chat bridge output_mode: {output_mode}")
    if command == "--chat-gpt":
        apply_chatgpt_cli_settings(config)
    contract = command_contract(command)
    protocol_version = CHATGPT_BRIDGE_PROTOCOL
    default_client = "chatgpt_bridge"
    default_lifecycle = "chatgpt_bridge_jsonl"
    if command == "--chat-open-ai":
        protocol_version = CHAT_OPENAI_PROTOCOL
        default_client = "openai_api_bridge"
        default_lifecycle = "openai_api_jsonl"
    elif command == "--chat-lm-studio":
        protocol_version = CHAT_LMSTUDIO_PROTOCOL
        default_client = "lmstudio_local_bridge"
        default_lifecycle = "lmstudio_jsonl_contract"

    if require_openai_api_key and not os.environ.get("OPENAI_API_KEY"):
        payload = {
            "schema_version": schema_version("chat_command_startup_error"),
            "ok": False,
            "error_code": "missing_openai_api_key",
            "error": "--chat-open-ai wymaga zmiennej środowiskowej OPENAI_API_KEY. Nie uruchamiam modelu i nie udaję połączenia z OpenAI API.",
            "chat_command_contract": contract,
        }
        stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        stdout.flush()
        return 3

    sessions: dict[str, RuntimeSessionWorker] = {}
    generated_session: RuntimeSessionWorker | None = None

    def bridge_meta(
        *,
        client: str = default_client,
        input_kind: str | None = None,
        input_field: str | None = None,
        line_index: int | None = None,
    ) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "protocol_version": protocol_version,
            "accepted_input_fields": list(ACCEPTED_CHATGPT_INPUT_FIELDS),
            "accepted_input_shapes": list(contract["accepted_input_shapes"]),
            "preferred_input_field": "message",
            "client": client,
            "lifecycle": default_lifecycle,
            "mode": contract["mode"],
            "command": command,
            "requires_api_key": contract["requires_api_key"],
            "uses_openai_api": contract["uses_openai_api"],
            "canonical_command": "--chat-gpt" if command == "--chat-gpt" else command,
            "legacy_aliases": ["--chat-gpt-final-only", "--chat-gpt --final-only"] if command == "--chat-gpt" else [],
            "canonicalization_policy": (
                "Use --chat-gpt as the single public ChatGPT bridge; aliases are backwards-compatible only."
                if command == "--chat-gpt" else "canonical command"
            ),
            "deprecated_flag_removed": "--chat-jsonl",
        }
        if input_kind is not None:
            meta["input_kind"] = input_kind
        if input_field is not None:
            meta["input_field"] = input_field
        if line_index is not None:
            meta["line_index"] = line_index
        return meta

    def error_payload(
        *,
        error_code: str,
        error: str,
        client: str = default_client,
        input_kind: str | None = None,
        input_field: str | None = None,
        line_index: int | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": schema_version("chat_bridge_error"),
            "chat_bridge": bridge_meta(client=client, input_kind=input_kind, input_field=input_field, line_index=line_index),
            "chat_command_contract": contract,
            "ok": False,
            "error_code": error_code,
            "error": error,
        }

    def get_session(payload_session_id: str | None, *, client: str) -> tuple[RuntimeSessionWorker, str]:
        nonlocal generated_session
        if payload_session_id:
            if payload_session_id not in sessions:
                sessions[payload_session_id] = RuntimeSessionWorker(session_factory=JaznRuntimeSession, config=config, session_id=payload_session_id, no_carryover=no_carryover, source_client=client, command=command, timeout_seconds=runtime_turn_timeout_seconds(config))
            return sessions[payload_session_id], "payload"
        if session_id:
            if session_id not in sessions:
                sessions[session_id] = RuntimeSessionWorker(session_factory=JaznRuntimeSession, config=config, session_id=session_id, no_carryover=no_carryover, source_client=client, command=command, timeout_seconds=runtime_turn_timeout_seconds(config))
            return sessions[session_id], "cli_arg"
        if generated_session is None:
            generated_session = RuntimeSessionWorker(session_factory=JaznRuntimeSession, config=config, session_id=None, no_carryover=no_carryover, source_client=client, command=command, timeout_seconds=runtime_turn_timeout_seconds(config))
            sessions[generated_session.state.session_id] = generated_session
        return generated_session, "generated"

    try:
        for line_index, line in enumerate(stdin, 1):
            line = line.strip()
            if not line:
                continue
            if line in {"/exit", "exit"}:
                break

            input_kind = "plain_text"
            input_field = "plain_text"
            payload_session_id = None
            client = default_client

            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                if line[:1] in {"{", "["}:
                    write_chat_bridge_payload(stdout, error_payload(
                        error_code="malformed_json",
                        error=f"Niepoprawna linia JSONL: {exc.msg}",
                        input_kind="malformed_json",
                        input_field="<parse_error>",
                        line_index=line_index,
                    ), output_mode=output_mode)
                    continue
                user_text = line
            else:
                input_kind = "json"
                if not isinstance(payload, dict):
                    write_chat_bridge_payload(stdout, error_payload(
                        error_code="invalid_jsonl_payload",
                        error="Każda linia mostu chat musi być obiektem JSON albo zwykłym tekstem.",
                        input_kind="json_non_object",
                        input_field="<non_object>",
                        line_index=line_index,
                    ), output_mode=output_mode)
                    continue
                client = str(payload.get("client") or default_client)
                payload_session_id = str(payload.get("session_id") or "").strip() or None
                user_text, input_kind, input_field = extract_user_text_from_payload(payload)

            if not user_text.strip():
                write_chat_bridge_payload(stdout, error_payload(
                    error_code="empty_message",
                    error="Pusta wiadomość nie została przekazana do runtime Jaźni.",
                    client=client,
                    input_kind=input_kind,
                    input_field=input_field,
                    line_index=line_index,
                ), output_mode=output_mode)
                continue

            try:
                session, session_id_source = get_session(payload_session_id, client=client)
                result = session.process_user_text(
                    user_text,
                    client=client,
                    lifecycle=default_lifecycle,
                    session_id_source=session_id_source,
                    process_reused=True,
                )
            except RuntimeTurnTimeoutError as exc:
                write_chat_bridge_payload(stdout, error_payload(
                    error_code="runtime_turn_timeout",
                    error=(
                        f"Runtime Jaźni nie zakończył etapu {getattr(exc, 'phase', 'runtime_turn')} w limicie {exc.timeout_seconds:.3g}s. "
                        "Zwracam kontrolowany błąd zamiast wiszącego mostu; sprawdź start sesji, timestamp/memory/engine.process_turn."
                    ),
                    client=client,
                    input_kind=input_kind,
                    input_field=input_field,
                    line_index=line_index,
                ), output_mode=output_mode)
                continue
            except Exception as exc:
                write_chat_bridge_payload(stdout, error_payload(
                    error_code="runtime_turn_failed",
                    error=f"Runtime Jaźni przerwał turę: {type(exc).__name__}: {exc}",
                    client=client,
                    input_kind=input_kind,
                    input_field=input_field,
                    line_index=line_index,
                ), output_mode=output_mode)
                continue
            result["chat_bridge"] = bridge_meta(client=client, input_kind=input_kind, input_field=input_field, line_index=line_index)
            # Zachowujemy stary klucz dla zgodności z narzędziami, które już czytają --chat-gpt.
            if command == "--chat-gpt":
                result["chatgpt_bridge"] = result["chat_bridge"]
            result["chat_command_contract"] = contract
            # v14.8.5.014: most nie może nadpisać blokady runtime truth gate przez ok=True.
            result["ok"] = bool(result.get("ok", True))
            write_chat_bridge_payload(stdout, result, output_mode=output_mode)
    finally:
        for session in sessions.values():
            session.close()
    return 0
