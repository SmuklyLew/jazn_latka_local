from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

from latka_jazn.config import JaznConfig
from latka_jazn.core.clock import WarsawClock
from latka_jazn.core.runtime_session import JaznRuntimeSession
from latka_jazn.core.runtime_truth_gate import daemon_active_state
from latka_jazn.tools.active_extraction_cache import (
    build_active_runtime_status,
    write_active_runtime_marker,
)
from latka_jazn.version import PACKAGE_VERSION, PACKAGE_VERSION_FULL, schema_version

DEFAULT_DAEMON_HOST = "127.0.0.1"
DEFAULT_DAEMON_PORT = 8787
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 30.0
DEFAULT_START_TIMEOUT_SECONDS = 12.0
DEFAULT_STOP_TIMEOUT_SECONDS = 5.0
DEFAULT_HTTP_TIMEOUT_SECONDS = 2.0
DEFAULT_STATUS_HTTP_TIMEOUT_SECONDS = 3.0
DEFAULT_LITE_STATUS_HTTP_TIMEOUT_SECONDS = 0.75
DEFAULT_DAEMON_CHAT_TIMEOUT_SECONDS = 180.0
DEFAULT_HEARTBEAT_FRESH_MULTIPLIER = 3.0
DEFAULT_TIMESTAMP_BACKGROUND_REFRESH_MIN_SECONDS = 20.0
DEFAULT_TIMESTAMP_BACKGROUND_REFRESH_TIMEOUT_SECONDS = 0.35
DAEMON_MAX_BODY_BYTES = 1_000_000
DAEMON_SCHEMA_VERSION = schema_version("persistent_daemon_runtime", version=PACKAGE_VERSION_FULL)
DAEMON_MARKER_STATUS_ACTIVE = "active_daemon_runtime"
DAEMON_MARKER_STATUS_STOPPED = "stopped_daemon_runtime"
LOOPBACK_CLIENTS = {"127.0.0.1", "::1", "localhost"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def daemon_default_marker_path(root: Path) -> Path:
    return Path(root).resolve() / "workspace_runtime" / "JAZN_ACTIVE_RUNTIME.json"


def daemon_pid_path(root: Path) -> Path:
    return Path(root).resolve() / "workspace_runtime" / "jazn_daemon.pid"


def daemon_log_dir(root: Path) -> Path:
    return Path(root).resolve() / "workspace_runtime" / "daemon"


def daemon_url(host: str = DEFAULT_DAEMON_HOST, port: int = DEFAULT_DAEMON_PORT, path: str = "/status") -> str:
    return f"http://{host}:{int(port)}{path}"


def read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _env_bool_value(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "tak", "on"}


def _env_float_value(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _env_int_value(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def apply_daemon_trusted_time_env(
    *,
    trusted_time_iso: str | None = None,
    source: str | None = None,
    max_age_seconds: int | None = None,
) -> dict[str, Any]:
    """Inject a host-provided trusted timestamp for this process and daemon children.

    ChatGPT-hosted runs cannot rely on Python network access from the sandbox.
    The loader can pass its trusted current timestamp into the runtime with
    --trusted-time-iso or the JAZN_TRUSTED_TIME_ISO environment variable.
    This helper only records explicitly supplied data; it never invents a
    trusted clock from the local system clock.
    """
    changed: list[str] = []
    if trusted_time_iso and str(trusted_time_iso).strip():
        os.environ["JAZN_TRUSTED_TIME_ISO"] = str(trusted_time_iso).strip()
        changed.append("JAZN_TRUSTED_TIME_ISO")
    if source and str(source).strip():
        os.environ["JAZN_TRUSTED_TIME_SOURCE"] = str(source).strip()
        changed.append("JAZN_TRUSTED_TIME_SOURCE")
    if max_age_seconds is not None and int(max_age_seconds) > 0:
        os.environ["JAZN_TRUSTED_TIME_MAX_AGE_SECONDS"] = str(int(max_age_seconds))
        changed.append("JAZN_TRUSTED_TIME_MAX_AGE_SECONDS")
    return {
        "trusted_time_env_present": bool(os.environ.get("JAZN_TRUSTED_TIME_ISO", "").strip()),
        "trusted_time_source": os.environ.get("JAZN_TRUSTED_TIME_SOURCE", "chatgpt_loader_time"),
        "trusted_time_max_age_seconds": _env_int_value("JAZN_TRUSTED_TIME_MAX_AGE_SECONDS", 120),
        "changed_env": changed,
        "truth_boundary": "Trusted time is accepted only when explicitly injected by the host/loader or supplied through the environment; the daemon must not silently promote local fallback time to trusted.",
    }


def daemon_timestamp_contract(
    config: JaznConfig,
    *,
    network_first: bool | None = None,
    timeout_seconds: float | None = None,
    reason: str = "direct",
) -> dict[str, Any]:
    # /status nadal musi być szybki, ale nie może z definicji fałszować stanu
    # czasu. Jeśli daemon może pobrać zaufany czas sieciowy albo dostał świeży
    # czas wstrzyknięty przez loader, marker ma prawo przejść w active_trusted.
    # Gdy sieć zawiedzie, wracamy do jawnego active_degraded.
    clock = WarsawClock(config.timezone)
    network_allowed = bool(getattr(config, "allow_network", True)) and _env_bool_value("JAZN_DAEMON_STATUS_NETWORK_TIME", True)
    if network_first is None:
        network_first = network_allowed and bool(getattr(config, "network_time_first", True))
    else:
        network_first = bool(network_first) and network_allowed
    if timeout_seconds is None:
        timeout_seconds = _env_float_value("JAZN_DAEMON_STATUS_NETWORK_TIME_TIMEOUT", 0.8)
    sample = clock.now(
        network_first=network_first,
        allow_fallback=True,
        timeout_seconds=float(timeout_seconds),
    )
    contract = clock.sample_contract(sample)
    contract["daemon_status_network_time_checked"] = bool(network_first)
    contract["daemon_status_network_time_allowed"] = network_allowed
    contract["daemon_status_network_time_timeout_seconds"] = float(timeout_seconds)
    contract["daemon_status_refresh_reason"] = reason
    if contract.get("trusted") is True:
        contract["daemon_status_time_mode"] = "trusted_time_confirmed"
        contract["error"] = None
    else:
        contract["daemon_status_time_mode"] = "degraded_local_fallback"
        contract["error"] = "daemon status could not confirm trusted network or injected time; active_state remains active_degraded"
    return contract


def pid_is_alive(pid: int | None) -> bool:
    if not pid or int(pid) <= 0:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def extract_daemon_user_text(payload: dict[str, Any] | str) -> tuple[str, str]:
    if isinstance(payload, str):
        return payload.strip(), "plain_text"
    if not isinstance(payload, dict):
        return "", "invalid_payload"
    for field_name in ("message", "text", "user_text", "content", "prompt"):
        value = payload.get(field_name)
        if value is not None and str(value).strip():
            return str(value).strip(), f"json.{field_name}"
    messages = payload.get("messages")
    if isinstance(messages, list):
        fallback = ""
        for item in messages:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                parts: list[str] = []
                for part in content:
                    if isinstance(part, dict) and part.get("text") is not None:
                        parts.append(str(part.get("text")))
                    elif part is not None:
                        parts.append(str(part))
                text = "".join(parts).strip()
            else:
                text = str(content or "").strip()
            if not text:
                continue
            fallback = text
            if str(item.get("role") or "").lower() == "user":
                return text, "json.messages[user].content"
        if fallback:
            return fallback, "json.messages[].content"
    return "", "missing_message"


def _parse_iso_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _age_seconds(value: str | None, *, now: datetime | None = None) -> float | None:
    parsed = _parse_iso_utc(value)
    if parsed is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - parsed).total_seconds())


def _heartbeat_fresh(marker: dict[str, Any] | None) -> tuple[bool, float | None, float]:
    if not isinstance(marker, dict):
        return False, None, DEFAULT_HEARTBEAT_INTERVAL_SECONDS * DEFAULT_HEARTBEAT_FRESH_MULTIPLIER
    interval = marker.get("heartbeat_interval_seconds") or (marker.get("runtime_daemon") or {}).get("heartbeat_interval_seconds") or DEFAULT_HEARTBEAT_INTERVAL_SECONDS
    try:
        interval_f = max(1.0, float(interval))
    except (TypeError, ValueError):
        interval_f = DEFAULT_HEARTBEAT_INTERVAL_SECONDS
    threshold = max(interval_f * DEFAULT_HEARTBEAT_FRESH_MULTIPLIER, interval_f + 10.0)
    age = _age_seconds(marker.get("last_heartbeat_at_utc") or (marker.get("runtime_daemon") or {}).get("last_heartbeat_at_utc"))
    return bool(age is not None and age <= threshold), age, threshold


@dataclass(slots=True)
class DaemonRuntimeState:
    root: str
    host: str = DEFAULT_DAEMON_HOST
    port: int = DEFAULT_DAEMON_PORT
    pid: int = field(default_factory=os.getpid)
    started_at_utc: str = field(default_factory=utc_now_iso)
    last_heartbeat_at_utc: str = field(default_factory=utc_now_iso)
    request_count: int = 0
    turn_count: int = 0
    sessions: int = 0
    status: str = DAEMON_MARKER_STATUS_ACTIVE
    last_request_at_utc: str | None = None
    last_status_latency_ms: int | None = None
    response_write_error_count: int = 0
    last_response_write_error: str | None = None
    timestamp_refresh_count: int = 0
    timestamp_refresh_in_progress: bool = False
    last_timestamp_refresh_at_utc: str | None = None

    def touch(self) -> None:
        self.last_heartbeat_at_utc = utc_now_iso()

    def note_request(self, *, latency_ms: int | None = None) -> None:
        self.request_count += 1
        self.last_request_at_utc = utc_now_iso()
        if latency_ms is not None:
            self.last_status_latency_ms = int(latency_ms)

    def uptime_seconds(self) -> float | None:
        started = _parse_iso_utc(self.started_at_utc)
        if started is None:
            return None
        return max(0.0, (datetime.now(timezone.utc) - started).total_seconds())

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["uptime_seconds"] = self.uptime_seconds()
        return payload


class JaznDaemonServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    block_on_close = False

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler],
        *,
        config: JaznConfig,
        marker_path: Path,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.config = config
        self.marker_path = Path(marker_path)
        self.heartbeat_interval = float(heartbeat_interval)
        self.sessions: dict[str, JaznRuntimeSession] = {}
        self.state = DaemonRuntimeState(root=str(config.root), host=server_address[0], port=int(server_address[1]))
        self.shutdown_requested = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None
        self._timestamp_lock = threading.Lock()
        self._timestamp_contract: dict[str, Any] | None = None
        self._timestamp_contract_updated_at_utc: str | None = None
        self._timestamp_refresh_thread: threading.Thread | None = None
        self._last_timestamp_refresh_started_monotonic = 0.0

    def get_session(self, session_id: str | None, *, no_carryover: bool = False, client: str = "daemon_http") -> tuple[JaznRuntimeSession, str]:
        if session_id:
            if session_id not in self.sessions:
                self.sessions[session_id] = JaznRuntimeSession(self.config, session_id=session_id, no_carryover=no_carryover, source_client=client)
            return self.sessions[session_id], "payload"
        generated = f"daemon-{uuid.uuid4()}"
        self.sessions[generated] = JaznRuntimeSession(self.config, session_id=generated, no_carryover=no_carryover, source_client=client)
        return self.sessions[generated], "generated"

    def _local_timestamp_contract(self, *, reason: str) -> dict[str, Any]:
        return daemon_timestamp_contract(
            self.config,
            network_first=False,
            timeout_seconds=0.0,
            reason=reason,
        )

    def cached_timestamp_contract(self) -> dict[str, Any]:
        with self._timestamp_lock:
            if self._timestamp_contract is not None:
                contract = dict(self._timestamp_contract)
                updated_at = self._timestamp_contract_updated_at_utc
            else:
                contract = self._local_timestamp_contract(reason="status_fast_local_bootstrap")
                updated_at = utc_now_iso()
                self._timestamp_contract = dict(contract)
                self._timestamp_contract_updated_at_utc = updated_at
        contract["daemon_status_fast_path"] = True
        contract["daemon_status_cached_at_utc"] = updated_at
        contract["daemon_status_cache_age_seconds"] = _age_seconds(updated_at)
        contract["daemon_status_refresh_in_progress"] = self.state.timestamp_refresh_in_progress
        return contract

    def refresh_timestamp_contract(self, *, reason: str, background: bool = True, force: bool = False) -> None:
        min_interval = _env_float_value("JAZN_DAEMON_TIMESTAMP_REFRESH_MIN_SECONDS", DEFAULT_TIMESTAMP_BACKGROUND_REFRESH_MIN_SECONDS)
        timeout_seconds = _env_float_value("JAZN_DAEMON_TIMESTAMP_REFRESH_TIMEOUT", DEFAULT_TIMESTAMP_BACKGROUND_REFRESH_TIMEOUT_SECONDS)
        now_monotonic = time.monotonic()
        if not force and now_monotonic - self._last_timestamp_refresh_started_monotonic < min_interval:
            return
        if self.state.timestamp_refresh_in_progress:
            return

        def worker() -> None:
            self.state.timestamp_refresh_in_progress = True
            self._last_timestamp_refresh_started_monotonic = time.monotonic()
            try:
                contract = daemon_timestamp_contract(
                    self.config,
                    network_first=True,
                    timeout_seconds=timeout_seconds,
                    reason=reason,
                )
                with self._timestamp_lock:
                    self._timestamp_contract = dict(contract)
                    self._timestamp_contract_updated_at_utc = utc_now_iso()
                self.state.timestamp_refresh_count += 1
                self.state.last_timestamp_refresh_at_utc = self._timestamp_contract_updated_at_utc
            except Exception as exc:
                fallback = self._local_timestamp_contract(reason=f"{reason}_refresh_failed")
                fallback["daemon_status_refresh_error"] = f"{type(exc).__name__}: {exc}"
                with self._timestamp_lock:
                    self._timestamp_contract = dict(fallback)
                    self._timestamp_contract_updated_at_utc = utc_now_iso()
            finally:
                self.state.timestamp_refresh_in_progress = False

        if background:
            self._timestamp_refresh_thread = threading.Thread(target=worker, name="jazn-daemon-time-refresh", daemon=True)
            self._timestamp_refresh_thread.start()
        else:
            worker()

    def marker_payload(self, *, status: str | None = None, timestamp_contract: dict[str, Any] | None = None) -> dict[str, Any]:
        self.state.sessions = len(self.sessions)
        self.state.status = status or self.state.status
        active = build_active_runtime_status(self.config.root, marker_output=self.marker_path)
        timestamp_contract = timestamp_contract or self.cached_timestamp_contract()
        runtime_version = str(active.get("version") or PACKAGE_VERSION)
        active_state = "active_trusted" if timestamp_contract.get("trusted") is True else "active_degraded"
        payload = {
            **active,
            "schema_version": DAEMON_SCHEMA_VERSION,
            "runtime_daemon": self.state.to_dict(),
            "active_state": active_state,
            "timestamp_contract": timestamp_contract,
            "timestamp_trusted": bool(timestamp_contract.get("trusted")),
            "daemon_pid": self.state.pid,
            "daemon_host": self.state.host,
            "daemon_port": self.state.port,
            "daemon_url": daemon_url(self.state.host, self.state.port),
            "daemon_status": self.state.status,
            "daemon_started_at_utc": self.state.started_at_utc,
            "last_heartbeat_at_utc": self.state.last_heartbeat_at_utc,
            "heartbeat_interval_seconds": self.heartbeat_interval,
            "runtime_process_active": True,
            "runtime_version": runtime_version,
            "runtime_version_full": PACKAGE_VERSION_FULL,
            "start_file": "main.py",
            "version": runtime_version,
            "truth_boundary": "Ten marker oznacza działający lokalny proces daemonu tylko wtedy, gdy PID żyje, heartbeat jest świeży, /status odpowiada z localhost i active_state nie ukrywa trybu degraded. /status musi być szybkie i używa cache czasu; sieć odświeża osobny wątek.",
        }
        fresh, age, threshold = _heartbeat_fresh(payload)
        payload["heartbeat_fresh"] = fresh
        payload["heartbeat_age_seconds"] = age
        payload["heartbeat_fresh_threshold_seconds"] = threshold
        return payload

    def lite_status_payload(self, *, endpoint: str = "/ready", latency_ms: int | None = None) -> dict[str, Any]:
        timestamp_contract = self.cached_timestamp_contract()
        heartbeat_marker = {
            "last_heartbeat_at_utc": self.state.last_heartbeat_at_utc,
            "heartbeat_interval_seconds": self.heartbeat_interval,
        }
        heartbeat_fresh, heartbeat_age, heartbeat_threshold = _heartbeat_fresh(heartbeat_marker)
        active_state = "active_trusted" if timestamp_contract.get("trusted") is True else "active_degraded"
        liveness_ok = bool(heartbeat_fresh and self.state.status != DAEMON_MARKER_STATUS_STOPPED)
        readiness_ok = bool(liveness_ok and self.marker_path.exists())
        return {
            "schema_version": DAEMON_SCHEMA_VERSION,
            "ok": active_state == "active_trusted",
            "liveness_ok": liveness_ok,
            "readiness_ok": readiness_ok,
            "active_state": active_state if readiness_ok else "inactive",
            "daemon_pid": self.state.pid,
            "daemon_host": self.state.host,
            "daemon_port": self.state.port,
            "runtime_process_active": True,
            "runtime_version": PACKAGE_VERSION_FULL,
            "active_root": str(self.config.root),
            "marker_path": str(self.marker_path),
            "marker_found": self.marker_path.exists(),
            "endpoint_ok": True,
            "endpoint": endpoint,
            "status_latency_ms": int(latency_ms or 0),
            "timestamp_trusted": bool(timestamp_contract.get("trusted")),
            "timestamp_contract": timestamp_contract,
            "heartbeat_fresh": heartbeat_fresh,
            "heartbeat_age_seconds": heartbeat_age,
            "heartbeat_fresh_threshold_seconds": heartbeat_threshold,
            "last_heartbeat_at_utc": self.state.last_heartbeat_at_utc,
            "heartbeat_interval_seconds": self.heartbeat_interval,
            "request_count": self.state.request_count,
            "turn_count": self.state.turn_count,
            "sessions": len(self.sessions),
            "uptime_seconds": self.state.uptime_seconds(),
            "truth_boundary": "Fast status endpoints avoid network and heavy cache work. active_trusted still requires an injected or network-confirmed trusted timestamp; active_degraded is alive but not fully trusted.",
        }

    def write_marker(self, *, status: str | None = None, timestamp_contract: dict[str, Any] | None = None) -> dict[str, Any]:
        self.state.touch()
        payload = self.marker_payload(status=status, timestamp_contract=timestamp_contract)
        write_json_atomic(self.marker_path, payload)
        daemon_pid_path(self.config.root).parent.mkdir(parents=True, exist_ok=True)
        daemon_pid_path(self.config.root).write_text(str(self.state.pid), encoding="utf-8")
        return payload

    def start_heartbeat(self) -> None:
        def loop() -> None:
            while not self.shutdown_requested.is_set():
                try:
                    self.refresh_timestamp_contract(reason="heartbeat_background", background=True)
                    self.write_marker()
                except Exception:
                    pass
                self.shutdown_requested.wait(self.heartbeat_interval)
        self._heartbeat_thread = threading.Thread(target=loop, name="jazn-daemon-heartbeat", daemon=True)
        self._heartbeat_thread.start()

    def close_sessions(self) -> None:
        for session in list(self.sessions.values()):
            try:
                session.close()
            except Exception:
                pass
        self.sessions.clear()


class JaznDaemonHandler(BaseHTTPRequestHandler):
    server: JaznDaemonServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return

    def _loopback_only(self) -> bool:
        host = str(self.client_address[0])
        if host in LOOPBACK_CLIENTS or host.startswith("127."):
            return True
        self._json_response({"ok": False, "error": "daemon accepts loopback clients only", "client": host}, status=403)
        return False

    def _read_json_or_text(self) -> Any:
        length = int(self.headers.get("Content-Length") or 0)
        max_body = _env_int_value("JAZN_DAEMON_MAX_BODY_BYTES", DAEMON_MAX_BODY_BYTES)
        if length > max_body:
            return {"__daemon_error__": "body_too_large", "max_body_bytes": max_body, "received_bytes": length}
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        text = raw.decode("utf-8", errors="replace")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def _json_response(self, payload: dict[str, Any], *, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
            self.close_connection = True
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as exc:
            self.server.state.response_write_error_count += 1
            self.server.state.last_response_write_error = f"{type(exc).__name__}: client disconnected before daemon response was written"
            self.close_connection = True

    def do_GET(self) -> None:
        if not self._loopback_only():
            return
        started = time.perf_counter()
        path = self.path.split("?", 1)[0]
        if path in {"/live", "/liveness"}:
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.server.state.note_request(latency_ms=latency_ms)
            payload = self.server.lite_status_payload(endpoint=path, latency_ms=latency_ms)
            payload["ok"] = bool(payload.get("liveness_ok"))
            self._json_response(payload)
            return
        if path in {"/ready", "/status-lite", "/readiness"}:
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.server.state.note_request(latency_ms=latency_ms)
            payload = self.server.lite_status_payload(endpoint=path, latency_ms=latency_ms)
            self._json_response(payload)
            return
        if path in {"/", "/status", "/health"}:
            payload = self.server.write_marker()
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.server.state.note_request(latency_ms=latency_ms)
            payload["endpoint_ok"] = True
            payload["ok"] = payload.get("active_state") == "active_trusted"
            payload["endpoint"] = path
            payload["status_latency_ms"] = latency_ms
            self._json_response(payload)
            return
        if path == "/refresh-time":
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.server.state.note_request(latency_ms=latency_ms)
            self.server.refresh_timestamp_contract(reason="manual_http_refresh", background=True, force=True)
            payload = self.server.lite_status_payload(endpoint=path, latency_ms=latency_ms)
            payload.update({
                "ok": True,
                "refresh_started": True,
                "timestamp_refresh_in_progress": self.server.state.timestamp_refresh_in_progress,
            })
            self._json_response(payload)
            return
        self._json_response({"ok": False, "error": "not_found", "path": path}, status=404)

    def do_POST(self) -> None:
        if not self._loopback_only():
            return
        path = self.path.split("?", 1)[0]
        self.server.state.note_request()
        if path in {"/chat", "/message"}:
            payload = self._read_json_or_text()
            if isinstance(payload, dict) and payload.get("__daemon_error__") == "body_too_large":
                self._json_response({"ok": False, "error_code": "body_too_large", **payload}, status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return
            user_text, input_field = extract_daemon_user_text(payload)
            if not user_text:
                self._json_response({"ok": False, "error_code": "empty_message", "input_field": input_field}, status=400)
                return
            session_id = payload.get("session_id") if isinstance(payload, dict) else None
            no_carryover = bool(payload.get("no_carryover")) if isinstance(payload, dict) else False
            client = str(payload.get("client") or "daemon_http") if isinstance(payload, dict) else "daemon_http"
            try:
                session, session_id_source = self.server.get_session(str(session_id).strip() if session_id else None, no_carryover=no_carryover, client=client)
                result = session.process_user_text(user_text, client=client, lifecycle="persistent_daemon_http", session_id_source=session_id_source, process_reused=True)
                self.server.state.turn_count += 1
                marker = self.server.write_marker()
                result["ok"] = bool(result.get("ok", True))
                result["daemon"] = {
                    "schema_version": DAEMON_SCHEMA_VERSION,
                    "pid": self.server.state.pid,
                    "host": self.server.state.host,
                    "port": self.server.state.port,
                    "status": self.server.state.status,
                    "last_heartbeat_at_utc": self.server.state.last_heartbeat_at_utc,
                    "marker_path": str(self.server.marker_path),
                    "marker_sha_source": marker.get("manifest_current_sha256"),
                }
                self._json_response(result)
            except Exception as exc:
                self._json_response({"ok": False, "error_code": "runtime_turn_failed", "error": f"{type(exc).__name__}: {exc}"}, status=500)
            return
        if path == "/shutdown":
            payload = self.server.write_marker(status="shutdown_requested")
            payload["ok"] = True
            self._json_response(payload)
            def stop_later() -> None:
                time.sleep(0.15)
                self.server.shutdown_requested.set()
                self.server.shutdown()
            threading.Thread(target=stop_later, name="jazn-daemon-shutdown", daemon=True).start()
            return
        self._json_response({"ok": False, "error": "not_found", "path": path}, status=404)


def http_json(method: str, url: str, payload: dict[str, Any] | None = None, *, timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def run_daemon(
    config: JaznConfig,
    *,
    host: str = DEFAULT_DAEMON_HOST,
    port: int = DEFAULT_DAEMON_PORT,
    marker_output: Path | None = None,
    heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
) -> int:
    marker_path = Path(marker_output) if marker_output else daemon_default_marker_path(config.root)
    # Write the normal active-runtime marker first; then the daemon marker extends it.
    write_active_runtime_marker(config.root, marker_output=marker_path, action="daemon_run_start")
    server = JaznDaemonServer((host, int(port)), JaznDaemonHandler, config=config, marker_path=marker_path, heartbeat_interval=heartbeat_interval)
    server.refresh_timestamp_contract(reason="startup_background", background=True, force=True)
    server.write_marker()
    server.start_heartbeat()
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.shutdown_requested.set()
        try:
            server.close_sessions()
        finally:
            payload = server.marker_payload(status=DAEMON_MARKER_STATUS_STOPPED)
            payload["runtime_process_active"] = False
            payload["stopped_at_utc"] = utc_now_iso()
            write_json_atomic(marker_path, payload)
            server.server_close()
    return 0


def build_daemon_start_command(
    root: Path,
    *,
    host: str = DEFAULT_DAEMON_HOST,
    port: int = DEFAULT_DAEMON_PORT,
    marker_output: Path | None = None,
    heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
) -> list[str]:
    root = Path(root).resolve()
    cmd = [sys.executable, str(root / "main.py"), "--root", str(root), "--daemon-run", "--daemon-host", host, "--daemon-port", str(int(port)), "--daemon-heartbeat-interval", str(float(heartbeat_interval))]
    if marker_output:
        cmd.extend(["--daemon-marker-output", str(Path(marker_output))])
    return cmd


def _daemon_pid_from_status(status: dict[str, Any]) -> int | None:
    value = status.get("daemon_pid") or (status.get("runtime_daemon") or {}).get("pid")
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def _endpoint_confirms_pid(pid: int | None, ping: dict[str, Any] | None) -> bool:
    if not pid or not isinstance(ping, dict):
        return False
    ping_pid = _daemon_pid_from_status(ping)
    return bool(ping_pid and int(ping_pid) == int(pid) and ping.get("runtime_process_active") is True)


def _probe_daemon_status(host: str, port: int, *, timeout: float = DEFAULT_LITE_STATUS_HTTP_TIMEOUT_SECONDS) -> tuple[dict[str, Any] | None, str | None, str | None]:
    errors: list[str] = []
    for endpoint in ("/ready", "/status-lite", "/status"):
        try:
            payload = http_json("GET", daemon_url(host, int(port), endpoint), timeout=timeout if endpoint != "/status" else DEFAULT_STATUS_HTTP_TIMEOUT_SECONDS)
            payload.setdefault("endpoint", endpoint)
            return payload, None, endpoint
        except Exception as exc:
            errors.append(f"{endpoint}: {type(exc).__name__}: {exc}")
    return None, "; ".join(errors) if errors else "daemon endpoint unavailable", None


def _daemon_degraded_recommendation(*, endpoint_reachable: bool, timestamp_trusted: bool | None, heartbeat_fresh: bool) -> dict[str, Any] | None:
    if endpoint_reachable and timestamp_trusted is not True:
        return {
            "kind": "trusted_time_missing",
            "summary": "Daemon żyje, ale nie ma potwierdzonego czasu. W środowisku ChatGPT wstrzyknij zaufany timestamp z loadera albo pozwól na network-time.",
            "example": "python -X utf8 main.py --trusted-time-iso <ISO_FROM_CHATGPT_LOADER> --trusted-time-source chatgpt_loader --daemon-start",
        }
    if heartbeat_fresh and not endpoint_reachable:
        return {
            "kind": "endpoint_unreachable",
            "summary": "PID i heartbeat wyglądają świeżo, ale HTTP endpoint nie odpowiada. Sprawdź port, logi workspace_runtime/daemon oraz wykonaj --daemon-stop/--daemon-start.",
        }
    return None


def start_daemon(
    config: JaznConfig,
    *,
    host: str = DEFAULT_DAEMON_HOST,
    port: int = DEFAULT_DAEMON_PORT,
    marker_output: Path | None = None,
    heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    startup_timeout: float = DEFAULT_START_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    marker_path = Path(marker_output) if marker_output else daemon_default_marker_path(config.root)
    try:
        existing, _existing_error, _existing_endpoint = _probe_daemon_status(host, int(port))
        if isinstance(existing, dict) and existing.get("active_state") in {"active_trusted", "active_degraded"}:
            return {
                "ok": bool(existing.get("ok")),
                "already_running": True,
                "started": False,
                "degraded": existing.get("active_state") == "active_degraded",
                "pid": _daemon_pid_from_status(existing),
                "status": existing,
                "marker_path": str(marker_path),
            }
    except Exception:
        pass
    log_dir = daemon_log_dir(config.root)
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / "stdout.log"
    stderr_path = log_dir / "stderr.log"
    cmd = build_daemon_start_command(config.root, host=host, port=port, marker_output=marker_path, heartbeat_interval=heartbeat_interval)
    creationflags = 0
    popen_kwargs: dict[str, Any] = {}
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    else:
        popen_kwargs["start_new_session"] = True
    with stdout_path.open("ab") as out, stderr_path.open("ab") as err:
        proc = subprocess.Popen(cmd, cwd=str(config.root), stdout=out, stderr=err, stdin=subprocess.DEVNULL, creationflags=creationflags, **popen_kwargs)
    deadline = time.time() + float(startup_timeout)
    last_error: str | None = None
    while time.time() < deadline:
        if proc.poll() is not None:
            last_error = f"daemon process exited early with code {proc.returncode}"
            break
        try:
            status, status_error, status_endpoint = _probe_daemon_status(host, int(port))
            if isinstance(status, dict) and status.get("active_state") in {"active_trusted", "active_degraded"}:
                status.setdefault("endpoint", status_endpoint or status.get("endpoint"))
                return {"ok": bool(status.get("ok")), "started": True, "degraded": status.get("active_state") == "active_degraded", "pid": proc.pid, "status": status, "marker_path": str(marker_path), "stdout_log": str(stdout_path), "stderr_log": str(stderr_path), "command": cmd}
            last_error = status_error or "daemon probe returned no active state"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.2)
    return {"ok": False, "started": False, "pid": proc.pid, "error": last_error or "daemon did not answer before timeout", "marker_path": str(marker_path), "stdout_log": str(stdout_path), "stderr_log": str(stderr_path), "command": cmd}


def status_daemon(config: JaznConfig, *, host: str = DEFAULT_DAEMON_HOST, port: int = DEFAULT_DAEMON_PORT, marker_output: Path | None = None) -> dict[str, Any]:
    marker_path = Path(marker_output) if marker_output else daemon_default_marker_path(config.root)
    marker = read_json_file(marker_path)
    pid = None
    if marker:
        pid = marker.get("daemon_pid") or (marker.get("runtime_daemon") or {}).get("pid")
    pid_int = int(pid) if pid else None
    os_pid_alive = pid_is_alive(pid_int) if pid_int else False
    ping, ping_error, ping_endpoint = _probe_daemon_status(host, int(port))
    endpoint_reachable = ping is not None
    endpoint_pid_matches = _endpoint_confirms_pid(pid_int, ping)
    heartbeat_is_fresh, heartbeat_age_seconds, heartbeat_fresh_threshold_seconds = _heartbeat_fresh(marker)
    alive = bool(os_pid_alive or endpoint_pid_matches)
    if os_pid_alive:
        pid_alive_source = "os_process_probe"
    elif endpoint_pid_matches:
        pid_alive_source = "endpoint_pid_match"
    else:
        pid_alive_source = "unverified"
    timestamp_trusted = (ping or {}).get("timestamp_trusted") if isinstance(ping, dict) else None
    active_state = daemon_active_state(marker_found=marker is not None, pid_alive=alive, ping_ok=endpoint_reachable, timestamp_trusted=timestamp_trusted)
    active_state_reason = "endpoint_status"
    if active_state == "inactive" and marker is not None and os_pid_alive and heartbeat_is_fresh:
        active_state = "active_degraded"
        active_state_reason = "fresh_marker_and_live_pid_endpoint_unreachable"
    return {
        "schema_version": DAEMON_SCHEMA_VERSION,
        "ok": active_state == "active_trusted",
        "active_state": active_state,
        "degraded": active_state == "active_degraded",
        "runtime_version": PACKAGE_VERSION_FULL,
        "active_root": str(config.root),
        "marker_path": str(marker_path),
        "marker_found": marker is not None,
        "marker": marker,
        "pid": pid,
        "pid_alive": alive,
        "pid_alive_os_probe": os_pid_alive,
        "pid_alive_source": pid_alive_source,
        "endpoint_pid_matches": endpoint_pid_matches,
        "endpoint_reachable": endpoint_reachable,
        "ping_endpoint": ping_endpoint,
        "ping": ping,
        "ping_error": ping_error,
        "timestamp_trusted": timestamp_trusted,
        "heartbeat_fresh": heartbeat_is_fresh,
        "heartbeat_age_seconds": heartbeat_age_seconds,
        "heartbeat_fresh_threshold_seconds": heartbeat_fresh_threshold_seconds,
        "active_state_reason": active_state_reason,
        "recommended_repair": _daemon_degraded_recommendation(
            endpoint_reachable=endpoint_reachable,
            timestamp_trusted=timestamp_trusted,
            heartbeat_fresh=heartbeat_is_fresh,
        ),
        "truth_boundary": "Status active_trusted wymaga markera, potwierdzonego procesu, lokalnego endpointu /status i zaufanego czasu sieciowego albo jawnie wstrzykniętego trusted timestampu z loadera. Jeżeli endpoint chwilowo nie odpowie, świeży heartbeat i żywy PID dają najwyżej active_degraded, nigdy active_trusted.",
    }


def refresh_daemon_time(
    config: JaznConfig,
    *,
    host: str = DEFAULT_DAEMON_HOST,
    port: int = DEFAULT_DAEMON_PORT,
    timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    response: dict[str, Any] | None = None
    error: str | None = None
    try:
        response = http_json("GET", daemon_url(host, int(port), "/refresh-time"), timeout=timeout)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    status = status_daemon(config, host=host, port=port)
    return {
        "schema_version": DAEMON_SCHEMA_VERSION,
        "ok": error is None,
        "refresh_response": response,
        "refresh_error": error,
        "status": status,
    }


def chat_daemon(
    config: JaznConfig,
    user_text: str,
    *,
    host: str = DEFAULT_DAEMON_HOST,
    port: int = DEFAULT_DAEMON_PORT,
    session_id: str | None = None,
    no_carryover: bool = False,
    client: str = "chatgpt_daemon_bridge",
    timeout: float = DEFAULT_DAEMON_CHAT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    text = str(user_text or "").strip()
    if not text:
        return {"ok": False, "error_code": "empty_message", "schema_version": DAEMON_SCHEMA_VERSION}
    payload: dict[str, Any] = {"message": text, "client": client, "no_carryover": bool(no_carryover)}
    if session_id:
        payload["session_id"] = session_id
    try:
        result = http_json("POST", daemon_url(host, int(port), "/chat"), payload, timeout=timeout)
        result.setdefault("ok", True)
        return result
    except Exception as exc:
        return {
            "ok": False,
            "error_code": "daemon_chat_failed",
            "error": f"{type(exc).__name__}: {exc}",
            "schema_version": DAEMON_SCHEMA_VERSION,
            "status": status_daemon(config, host=host, port=port),
        }


def stop_daemon(
    config: JaznConfig,
    *,
    host: str = DEFAULT_DAEMON_HOST,
    port: int = DEFAULT_DAEMON_PORT,
    marker_output: Path | None = None,
    timeout: float = DEFAULT_STOP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    marker_path = Path(marker_output) if marker_output else daemon_default_marker_path(config.root)
    before = status_daemon(config, host=host, port=port, marker_output=marker_path)
    shutdown_response: dict[str, Any] | None = None
    shutdown_error: str | None = None
    try:
        shutdown_response = http_json("POST", daemon_url(host, int(port), "/shutdown"), {}, timeout=2.0)
    except Exception as exc:
        shutdown_error = f"{type(exc).__name__}: {exc}"
    deadline = time.time() + float(timeout)
    while time.time() < deadline:
        try:
            http_json("GET", daemon_url(host, int(port), "/status"), timeout=0.5)
            time.sleep(0.2)
        except Exception:
            break
    after = status_daemon(config, host=host, port=port, marker_output=marker_path)
    return {
        "schema_version": DAEMON_SCHEMA_VERSION,
        "ok": not bool(after.get("ok")),
        "before": before,
        "shutdown_response": shutdown_response,
        "shutdown_error": shutdown_error,
        "after": after,
    }
