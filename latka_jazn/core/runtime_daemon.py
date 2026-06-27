from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
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
from latka_jazn.version import PACKAGE_VERSION, schema_version

DEFAULT_DAEMON_HOST = "127.0.0.1"
DEFAULT_DAEMON_PORT = 8787
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 30.0
DEFAULT_START_TIMEOUT_SECONDS = 12.0
DEFAULT_STOP_TIMEOUT_SECONDS = 5.0
DEFAULT_HTTP_TIMEOUT_SECONDS = 2.0
DAEMON_SCHEMA_VERSION = schema_version("persistent_daemon_runtime")
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


def daemon_timestamp_contract(config: JaznConfig) -> dict[str, Any]:
    # /status i heartbeat muszą być szybkie. Nie wykonujemy tu sieciowego czasu,
    # bo blokowałoby to lokalny daemon przy awarii DNS/sieci. Zwykłe odpowiedzi
    # nadal przechodzą przez ścisłą bramę timestampu w JaznRuntimeSession.
    clock = WarsawClock(config.timezone)
    sample = clock.now(network_first=False, allow_fallback=True)
    contract = clock.sample_contract(sample)
    contract["source"] = "daemon_status_network_time_not_checked"
    contract["trusted"] = False
    contract["error"] = "daemon status is responsive-only; run --network-time-check or a real turn to verify network timestamp"
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

    def touch(self) -> None:
        self.last_heartbeat_at_utc = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class JaznDaemonServer(ThreadingHTTPServer):
    daemon_threads = True

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

    def get_session(self, session_id: str | None, *, no_carryover: bool = False, client: str = "daemon_http") -> tuple[JaznRuntimeSession, str]:
        if session_id:
            if session_id not in self.sessions:
                self.sessions[session_id] = JaznRuntimeSession(self.config, session_id=session_id, no_carryover=no_carryover, source_client=client)
            return self.sessions[session_id], "payload"
        generated = f"daemon-{uuid.uuid4()}"
        self.sessions[generated] = JaznRuntimeSession(self.config, session_id=generated, no_carryover=no_carryover, source_client=client)
        return self.sessions[generated], "generated"

    def marker_payload(self, *, status: str | None = None) -> dict[str, Any]:
        self.state.sessions = len(self.sessions)
        self.state.status = status or self.state.status
        active = build_active_runtime_status(self.config.root, marker_output=self.marker_path)
        timestamp_contract = daemon_timestamp_contract(self.config)
        active_state = "active_trusted" if timestamp_contract.get("trusted") is True else "active_degraded"
        return {
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
            "start_file": "main.py",
            "version": PACKAGE_VERSION,
            "truth_boundary": "Ten marker oznacza działający lokalny proces daemonu tylko wtedy, gdy PID żyje, heartbeat jest świeży, /status odpowiada z localhost i active_state nie ukrywa trybu degraded.",
        }

    def write_marker(self, *, status: str | None = None) -> dict[str, Any]:
        self.state.touch()
        payload = self.marker_payload(status=status)
        write_json_atomic(self.marker_path, payload)
        daemon_pid_path(self.config.root).parent.mkdir(parents=True, exist_ok=True)
        daemon_pid_path(self.config.root).write_text(str(self.state.pid), encoding="utf-8")
        return payload

    def start_heartbeat(self) -> None:
        def loop() -> None:
            while not self.shutdown_requested.is_set():
                try:
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
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if not self._loopback_only():
            return
        path = self.path.split("?", 1)[0]
        if path in {"/", "/status", "/health"}:
            self.server.state.request_count += 1
            payload = self.server.write_marker()
            payload["endpoint_ok"] = True
            payload["ok"] = payload.get("active_state") == "active_trusted"
            payload["endpoint"] = path
            self._json_response(payload)
            return
        self._json_response({"ok": False, "error": "not_found", "path": path}, status=404)

    def do_POST(self) -> None:
        if not self._loopback_only():
            return
        path = self.path.split("?", 1)[0]
        self.server.state.request_count += 1
        if path in {"/chat", "/message"}:
            payload = self._read_json_or_text()
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
        existing = http_json("GET", daemon_url(host, int(port), "/status"), timeout=1.0)
        if existing.get("active_state") in {"active_trusted", "active_degraded"}:
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
            status = http_json("GET", daemon_url(host, int(port), "/status"), timeout=2.0)
            if status.get("active_state") in {"active_trusted", "active_degraded"}:
                return {"ok": bool(status.get("ok")), "started": True, "degraded": status.get("active_state") == "active_degraded", "pid": proc.pid, "status": status, "marker_path": str(marker_path), "stdout_log": str(stdout_path), "stderr_log": str(stderr_path), "command": cmd}
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
    ping: dict[str, Any] | None = None
    ping_error: str | None = None
    try:
        ping = http_json("GET", daemon_url(host, int(port), "/status"), timeout=2.0)
    except Exception as exc:
        ping_error = f"{type(exc).__name__}: {exc}"
    endpoint_reachable = ping is not None
    endpoint_pid_matches = _endpoint_confirms_pid(pid_int, ping)
    alive = bool(os_pid_alive or endpoint_pid_matches)
    if os_pid_alive:
        pid_alive_source = "os_process_probe"
    elif endpoint_pid_matches:
        pid_alive_source = "endpoint_pid_match"
    else:
        pid_alive_source = "unverified"
    timestamp_trusted = (ping or {}).get("timestamp_trusted") if isinstance(ping, dict) else None
    active_state = daemon_active_state(marker_found=marker is not None, pid_alive=alive, ping_ok=endpoint_reachable, timestamp_trusted=timestamp_trusted)
    return {
        "schema_version": DAEMON_SCHEMA_VERSION,
        "ok": active_state == "active_trusted",
        "active_state": active_state,
        "degraded": active_state == "active_degraded",
        "runtime_version": config.version,
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
        "ping": ping,
        "ping_error": ping_error,
        "timestamp_trusted": timestamp_trusted,
        "truth_boundary": "Status active_trusted wymaga markera, potwierdzonego procesu, lokalnego endpointu /status i zaufanego czasu sieciowego. Na Windows PID może być potwierdzony przez zgodny PID z lokalnego endpointu, ale bez trusted timestampu pozostaje active_degraded.",
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
