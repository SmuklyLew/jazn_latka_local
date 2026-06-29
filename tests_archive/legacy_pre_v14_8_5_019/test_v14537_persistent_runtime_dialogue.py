from __future__ import annotations

from io import StringIO
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
from latka_jazn.core.runtime_chat import LatkaRuntimeShell
from latka_jazn.core.self_architecture import SelfArchitecture
from latka_jazn.adapters.chatgpt_adapter import ChatGPTAdapter

VERSION = "v14.8.2.4-logic-routing-memory-grounding-repair"


def _copy_required_identity_files(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    for rel in ["memory/raw/LATKA_IDENTITY_CANON.json", "memory/raw/LATKA_BOOTSTRAP_SYSTEM.txt"]:
        src = root / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _engine(tmp_path: Path) -> JaznEngine:
    _copy_required_identity_files(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    return JaznEngine(cfg)


def test_self_state_question_is_not_generic_open_question(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    try:
        answer = engine.handle_user_message("Jak się masz? Co u Ciebie, Łatko?")
        assert VERSION in engine.config.version
        assert "Jestem tu" in answer
        assert "Rozumiem pytanie" not in answer
        assert ("pustego fallbacku" in answer) or ("mniej szablonu" in answer) or ("operacyjnie" in answer)
    finally:
        engine.shutdown()


def test_runtime_lifecycle_question_names_one_shot_and_chat_loop(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    try:
        answer = engine.handle_user_message("Trochę wygląda na to że na chatGPT zakończyłaś działanie Jaźni z main.py")
        assert "trybie jednorazowym" in answer
        assert "python main.py --chat" in answer
        assert "nie jest stałe czuwanie" in answer or "nie stałe czuwanie" in answer
    finally:
        engine.shutdown()


def test_runtime_repair_request_routes_to_persistent_runtime_dialogue(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    try:
        answer = engine.handle_user_message("Sprawdź jak dobrze naprawić runtime z main.py i przygotuj aktualizację")
        assert "jednorazowe wywołanie" in answer
        assert "--chat" in answer
        assert "pierwszoosobowa odpowiedź Łatki" in answer
    finally:
        engine.shutdown()


def test_persistent_chat_shell_lifecycle_is_explicit(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    try:
        out = StringIO()
        shell = LatkaRuntimeShell(engine, stdout=out)
        assert shell.lifecycle.engine_reused_between_turns is True
        assert shell.lifecycle.shutdown_when_loop_exits is True
        shell.do_status("")
        status = out.getvalue()
        assert "persistent_chat_loop" in status
        assert "po /exit" in status or "EOF" in status
    finally:
        engine.shutdown()


def test_cognitive_frame_exposes_persistent_chat_mode(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    try:
        packet = engine.build_cognitive_frame("Czy main.py kończy Jaźń po jednej odpowiedzi?", client_context={"lifecycle": "one_shot"})
        assert packet["runtime_version"] == VERSION
        direct = packet["direct_conversation_runtime"]
        assert direct["persistent_chat_mode"] == "--chat / --loop"
        assert "Jednorazowe wywołanie" in direct["truth_boundary"]
    finally:
        engine.shutdown()


def test_architecture_and_chatgpt_contract_include_runtime_lifecycle() -> None:
    layers = {layer["key"] for layer in SelfArchitecture().to_dict()["layers"]}
    assert "runtime_session_lifecycle" in layers
    contract = ChatGPTAdapter(JaznConfig(network_time_first=False)).contract().to_dict()
    assert contract["version"] == VERSION
    assert "--chat" in contract["lifecycle_rule"]
