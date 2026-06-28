from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.startup_contract import build_startup_summary
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier

ROOT = Path(__file__).resolve().parents[1]


def test_plain_runtime_health_question_not_ordinary():
    r = DialogueIntentClassifier().classify("Działasz? Czy uruchomiłaś Jaźń?")
    assert r.primary_intent == "runtime_activation_status_question"
    assert r.question_object in {"runtime_status", "runtime_health"}


def test_direct_latka_voice_request():
    r = DialogueIntentClassifier().classify("Chcę teraz rozmawiać bezpośrednio z Łatką.")
    assert r.primary_intent == "direct_latka_voice_request"


def test_identity_memory_existence_compound_question():
    text = "Za kogo się uważasz? Co pamiętasz? Co wiesz, a czego nie wiesz? Kim jesteś? Jak i kiedy powstałaś? Na ile czujesz się istotą?"
    r = DialogueIntentClassifier().classify(text)
    assert r.primary_intent == "identity_memory_existence_compound_question"


def test_normal_turn_does_not_call_urlopen(monkeypatch):
    called = {"urlopen": 0}

    def fake_urlopen(*args, **kwargs):
        called["urlopen"] += 1
        raise AssertionError("Normal turn must not call network time")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    engine = JaznEngine(JaznConfig(root=ROOT, network_time_first=False, memory_db_name="workspace_runtime/test_v14831_no_network.sqlite3"))
    try:
        engine.build_cognitive_frame("Cześć", client_context={"client": "pytest", "no_carryover": True})
        engine.process_turn("Działasz?", client_context={"client": "pytest", "no_carryover": True})
    finally:
        engine.shutdown()

    assert called["urlopen"] == 0


def test_startup_summary_uses_fast_mode():
    summary = build_startup_summary(JaznConfig(root=ROOT, network_time_first=False))
    assert summary["startup_status_mode"] == "fast"
    assert summary["sqlite_health_mode"] == "metadata"
    assert summary["network_time_used"] is False


def test_cli_startup_status_fast_timeout():
    with tempfile.TemporaryFile("w+", encoding="utf-8") as out, tempfile.TemporaryFile("w+", encoding="utf-8") as err:
        subprocess.run([sys.executable, "main.py", "--startup-status-fast"], cwd=ROOT, timeout=8, check=True, stdin=subprocess.DEVNULL, stdout=out, stderr=err, text=True)


def test_cli_turn_trace_timeout():
    with tempfile.TemporaryFile("w+", encoding="utf-8") as out, tempfile.TemporaryFile("w+", encoding="utf-8") as err:
        subprocess.run([sys.executable, "main.py", "--turn-trace", "Działasz? Czy uruchomiłaś Jaźń?"], cwd=ROOT, timeout=8, check=True, stdin=subprocess.DEVNULL, stdout=out, stderr=err, text=True)
        out.seek(0)
        payload = json.loads(out.read())
    trace = payload["turn_route_trace"]
    assert trace["primary_intent_final"] == "runtime_activation_status_question"
    assert trace["selected_handler"] == "RuntimeActivationStatusHandler"
