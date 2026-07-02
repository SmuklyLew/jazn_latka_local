from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from latka_jazn.config import JaznConfig
from latka_jazn.core.runtime_daemon import sanitize_status_payload, status_daemon
from latka_jazn.core.timestamp_policy import timestamp_runtime_policy


BAD_JOINED_WORDS = (
    "albo" + "wstrzyknięty",
    "brak" + "nie",
    "blokuje" + "zwykłej",
    "proces" + "daemonu",
    "endpoint" + "nie",
    "nie" + "blokuje",
    "PID" + "dają",
    "active_state" + "depends",
)


def _assert_no_joined_status_words(text: str) -> None:
    found = [bad for bad in BAD_JOINED_WORDS if bad in text]
    assert not found, f"joined status words found: {found}"


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(_walk_strings(item))
        return result
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_walk_strings(item))
        return result
    return []


def _assert_payload_clean(payload: dict[str, Any]) -> None:
    rendered = json.dumps(payload, ensure_ascii=False)
    _assert_no_joined_status_words(rendered)
    for text in _walk_strings(payload):
        _assert_no_joined_status_words(text)


def test_status_boundary_text_does_not_join_polish_words() -> None:
    sources = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "latka_jazn/core/runtime_daemon.py",
            "latka_jazn/core/timestamp_policy.py",
        )
    )

    _assert_no_joined_status_words(sources)
    assert "albo wstrzyknięty" in sources or "albo zaufany czas wstrzyknięty" in sources
    assert "brak nie blokuje startu runtime" in sources
    assert "proces daemonu" in sources
    assert "endpoint nie" in sources
    assert "nie blokuje" in sources
    assert "PID dają" in sources
    assert "active_state depends" in sources


def test_timestamp_policy_truth_boundary_keeps_spacing() -> None:
    truth_boundary = timestamp_runtime_policy()["truth_boundary"]

    _assert_no_joined_status_words(truth_boundary)
    assert "albo zaufany czas wstrzyknięty" in truth_boundary
    assert "nie blokuje zwykłej rozmowy" in truth_boundary


def test_sanitize_status_payload_cleans_nested_marker_strings() -> None:
    payload = {
        "truth_boundary": "Zaufany czas sieciowy " + "albo" + "wstrzyknięty" + "; jego " + "brak" + "nie" + " blokuje startu.",
        "marker": {
            "truth_boundary": "proces" + "daemonu" + " oraz " + "endpoint" + "nie" + " odpowiada",
            "timestamp_contract": {
                "truth_boundary": "nie " + "blokuje" + "zwykłej" + " rozmowy; który " + "nie" + "blokuje" + "; " + "PID" + "dają" + " active_degraded",
            },
        },
    }

    cleaned = sanitize_status_payload(payload)
    _assert_payload_clean(cleaned)
    rendered = json.dumps(cleaned, ensure_ascii=False)

    assert "albo wstrzyknięty" in rendered
    assert "brak nie blokuje" in rendered
    assert "blokuje zwykłej" in rendered
    assert "proces daemonu" in rendered
    assert "endpoint nie" in rendered
    assert "nie blokuje" in rendered
    assert "PID dają" in rendered


def test_status_daemon_rendered_truth_boundary_keeps_spacing(tmp_path: Path) -> None:
    cfg = JaznConfig(root=tmp_path)
    payload = status_daemon(
        cfg,
        host="127.0.0.1",
        port=9,
        marker_output=tmp_path / "JAZN_ACTIVE_RUNTIME.json",
    )

    _assert_payload_clean(payload)
    rendered = json.dumps(payload, ensure_ascii=False)

    assert "albo wstrzyknięty" in rendered
    assert "brak nie blokuje startu runtime" in rendered
    assert "nie blokuje" in rendered
    assert "PID dają" in rendered
