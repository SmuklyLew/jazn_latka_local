from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_runtime_preview_does_not_mark_safe_word_fallback_as_empty_fallback() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "main.py", "--runtime-preview", "Czy nowa paczka v14.6.2 jest rozpoznana?"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    payload = json.loads(result.stdout)
    assert "fallback" in payload["runtime_text"].lower()  # opis bezpiecznego fallbacku NLP jest dozwolony
    assert payload["fallback_detected"] is False
