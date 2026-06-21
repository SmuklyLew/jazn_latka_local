from __future__ import annotations

import io
from dataclasses import dataclass, field

from latka_jazn.core.runtime_chat import LatkaRuntimeShell


@dataclass
class _FakeEnvelope:
    final_visible_text: str
    final_response_contract: dict = field(default_factory=dict)


class _RepeatingEngine:
    def process_turn(self, text, client_context=None):
        return _FakeEnvelope("Jestem. Odpowiadam zwyczajnie na bieżącą wiadomość, bez technicznego raportu i bez starego kontekstu. Co u Ciebie teraz?")


def test_chat_loop_replaces_duplicate_visible_text_with_guard_message():
    stdout = io.StringIO()
    shell = LatkaRuntimeShell(_RepeatingEngine(), stdout=stdout)  # type: ignore[arg-type]
    shell.default("Powiesz coś innego?")
    shell.default("Denerwują mnie twoje odpowiedzi.")
    out = stdout.getvalue()
    assert "Wykryłam, że runtime zwrócił identyczną widoczną odpowiedź" in out
    assert "ordinary_dialogue_handler.py" in out
