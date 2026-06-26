from __future__ import annotations

from pathlib import Path

from latka_jazn.bridge_secure_gateway import SecureGatewayPolicy, validate_gateway_request
from latka_jazn.memory.session_continuity import SessionContinuityManager
from latka_jazn.model_adapters.openai_state_tracker import OpenAIStateTracker


def test_large_jsonl_uses_fast_tail_stats_without_full_line_scan(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "memory" / "raw" / "runtime_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'{"a":1}\n' + b'x' * (17 * 1024 * 1024) + b'\n{"last":true}\n')

    def fail_line_stats(_path: Path):
        raise AssertionError("full line scan should not run for large JSONL during normal continuity update")

    monkeypatch.setattr(SessionContinuityManager, "_line_stats", staticmethod(fail_line_stats))
    manager = SessionContinuityManager(tmp_path, version="test")
    index = manager.update_index(reason="unit", source="test")
    entry = next(item for item in index["files"] if item["rel_path"] == "memory/raw/runtime_events.jsonl")
    assert entry["stats_mode"] == "fast_tail_stats_large_file"
    assert entry["line_count"] is None
    assert entry["tail_sha256"]


def test_openai_state_tracker_records_previous_response_id(tmp_path: Path) -> None:
    tracker = OpenAIStateTracker(tmp_path)
    state = tracker.update_from_response(session_id="s1", response={"id": "resp_123"}, store_policy=False)
    assert state.previous_response_id == "resp_123"
    loaded = tracker.load("s1")
    assert loaded.previous_response_id == "resp_123"
    assert loaded.last_response_id == "resp_123"


def test_secure_gateway_policy_requires_bearer_and_endpoint_allowlist() -> None:
    policy = SecureGatewayPolicy(max_body_bytes=10)
    bad = validate_gateway_request(endpoint="/admin", body_size=20, headers={}, expected_token="secret", policy=policy)
    assert bad["ok"] is False
    assert "endpoint_not_allowed" in bad["errors"]
    assert "body_too_large" in bad["errors"]
    assert "bearer_token_missing_or_invalid" in bad["errors"]

    good = validate_gateway_request(endpoint="/status", body_size=2, headers={"Authorization": "Bearer secret"}, expected_token="secret", policy=policy)
    assert good["ok"] is True
