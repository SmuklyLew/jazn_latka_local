from __future__ import annotations

import json
import subprocess
import sys


def _run(*args: str) -> dict:
    proc = subprocess.run([sys.executable, "main.py", *args], check=True, text=True, capture_output=True)
    return json.loads(proc.stdout)


def test_cli_polish_reasoning_sources():
    payload = _run("--polish-reasoning-sources")
    assert payload["polish_reasoning_sources"]["source_count"] >= 8
    assert payload["polish_reasoning_sources"]["policy"]["no_unlicensed_bulk_mirroring"] is True


def test_cli_polish_reasoning_frame_for_night_opening():
    payload = _run("--polish-reasoning-frame", "Witaj w tej mrocznej nocy.")
    frame = payload["polish_reasoning_frame"]
    assert frame["semantic_frame"]["primary_intent"] == "atmospheric_opening"
    assert frame["reply_policy"]["avoid_meta_commentary"] is True


def test_cli_wsjp_lookup_plan_does_not_scrape():
    payload = _run("--wsjp-lookup-plan", "mroczny")
    lookup = payload["lookup_plan"]
    assert lookup["source_id"] == "wsjp-pan"
    assert lookup["online_required"] is True
    assert "wsjp.pl" in lookup["url"]
    assert "nie twierdzi" in payload["truth_boundary"]
