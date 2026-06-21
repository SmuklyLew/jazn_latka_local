from __future__ import annotations
from dataclasses import asdict
from typing import Any
from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.runtime_session_state import RuntimeSessionStateStore

SCHEMA_VERSION = "runtime_session/v14.8.2.4"

class JaznRuntimeSession:
    """Wspólny rdzeń one-shot, --runtime-preview, --chat i --chat-jsonl.

    Różnice między trybami dotyczą tylko cyklu życia procesu i formatu I/O; każda tura
    przechodzi przez JaznEngine.process_turn().
    """
    def __init__(self, config: JaznConfig | None = None, *, session_id: str | None = None, no_carryover: bool = False) -> None:
        self.config = config or JaznConfig()
        self.engine = JaznEngine(self.config)
        self.state_store = RuntimeSessionStateStore(self.config.root)
        self.state = self.state_store.load_or_create(session_id=session_id, source_client="runtime_session", no_carryover=no_carryover)
        self.no_carryover = no_carryover

    def process_user_text(self, user_text: str, *, client: str = "runtime_session") -> dict[str, Any]:
        ctx = {"client": client, "lifecycle": "runtime_session", "session_id": self.state.session_id, "no_carryover": self.no_carryover}
        if not self.no_carryover and self.state.last_user_text:
            ctx["previous_user_text"] = self.state.last_user_text
            ctx["previous_detected_intent"] = self.state.last_intent
            ctx["previous_runtime_route"] = self.state.last_route
        envelope = self.engine.process_turn(user_text, client_context=ctx)
        env = envelope.to_dict()
        decision = (env.get("cognitive_frame") or {}).get("conversation_decision") or {}
        self.state.update(user_text=user_text, intent=str(decision.get("detected_user_intent") or "unknown"), route=str(decision.get("route") or "unknown"))
        self.state_store.save(self.state)
        return {"schema_version": SCHEMA_VERSION, "session": self.state.to_dict(), "final_visible_text": env.get("final_visible_text"), "trace": env.get("trace"), "conversation_decision": decision}

    def close(self) -> None:
        self.state_store.save(self.state)
        self.engine.shutdown()
