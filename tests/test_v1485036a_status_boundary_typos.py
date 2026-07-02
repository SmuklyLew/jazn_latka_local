from __future__ import annotations

from pathlib import Path

from latka_jazn.core.timestamp_policy import timestamp_runtime_policy


def test_status_boundary_text_does_not_join_polish_words() -> None:
    sources = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "latka_jazn/core/runtime_daemon.py",
            "latka_jazn/core/timestamp_policy.py",
        )
    )

    assert "albowstrzyknięty" not in sources
    assert "braknie" not in sources
    assert "blokujezwykłej" not in sources
    assert "albo wstrzyknięty" in sources or "albo zaufany czas wstrzyknięty" in sources
    assert "brak nie blokuje startu runtime" in sources


def test_timestamp_policy_truth_boundary_keeps_spacing() -> None:
    truth_boundary = timestamp_runtime_policy()["truth_boundary"]

    assert "albo zaufany czas wstrzyknięty" in truth_boundary
    assert "nie blokuje zwykłej rozmowy" in truth_boundary
    assert "blokujezwykłej" not in truth_boundary
