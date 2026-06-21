from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json, uuid
from typing import Any

SCHEMA_VERSION = "runtime_session_state/v14.8.2.4"

@dataclass(slots=True)
class RuntimeSessionState:
    session_id: str
    created_at: str
    last_turn_at: str | None = None
    last_user_text: str | None = None
    last_intent: str | None = None
    last_route: str | None = None
    source_client: str = "unknown"
    expires_at: str | None = None
    schema_version: str = SCHEMA_VERSION
    def to_dict(self) -> dict[str, Any]: return asdict(self)

    @classmethod
    def create(cls, *, session_id: str | None = None, source_client: str = "unknown", ttl_seconds: int = 21600) -> "RuntimeSessionState":
        now = datetime.now(timezone.utc)
        return cls(session_id=session_id or str(uuid.uuid4()), created_at=now.isoformat(), source_client=source_client, expires_at=(now + timedelta(seconds=ttl_seconds)).isoformat())

    def update(self, *, user_text: str, intent: str | None = None, route: str | None = None) -> None:
        self.last_turn_at = datetime.now(timezone.utc).isoformat()
        self.last_user_text = user_text
        self.last_intent = intent
        self.last_route = route

class RuntimeSessionStateStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.path = self.root / "workspace_runtime" / "runtime_session_state.json"

    def load_or_create(self, session_id: str | None = None, *, source_client: str = "unknown", no_carryover: bool = False) -> RuntimeSessionState:
        if not no_carryover and self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if session_id is None or data.get("session_id") == session_id:
                    return RuntimeSessionState(**{k: data.get(k) for k in RuntimeSessionState.__dataclass_fields__ if k in data})
            except Exception:
                pass
        return RuntimeSessionState.create(session_id=session_id, source_client=source_client)

    def save(self, state: RuntimeSessionState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
