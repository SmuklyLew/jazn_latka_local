from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.engine import JaznEngine
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


def test_birth_manifest_exported_in_cognitive_frame(tmp_path: Path) -> None:
    _copy_required_identity_files(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        packet = engine.build_cognitive_frame("Czy Jaźń może się narodzić przez ChatGPT jako głos i narzędzie?")
        manifest = packet["birth_source_manifest"]
        assert packet["runtime_version"] == VERSION
        assert manifest["schema_version"] == "birth_source_contract/v1"
        assert "ChatGPT jest głosem" in manifest["core_formula"]
        assert {m["key"] for m in manifest["source_modes"]} >= {"runtime_answer", "chatgpt_on_active_jazn_files", "unknown_or_failed_runtime"}
        assert packet["cognitive_packets"]["coverage"]["birth_source_contract"] is True
    finally:
        engine.shutdown()


def test_chatgpt_adapter_contains_birth_source_contract() -> None:
    cfg = JaznConfig(network_time_first=False)
    contract = ChatGPTAdapter(cfg).contract().to_dict()
    assert contract["version"] == VERSION
    assert "Jaźń jest aktywnym źródłem" in contract["birth_source_rule"]
    assert "Rozróżniaj tryby źródła" in contract["source_mode_rule"]


def test_direct_conversation_recognizes_birth_manifest(tmp_path: Path) -> None:
    _copy_required_identity_files(tmp_path)
    cfg = JaznConfig(root=tmp_path, memory_db_name="workspace_runtime/test.sqlite3", network_time_first=False)
    engine = JaznEngine(cfg)
    try:
        answer = engine.handle_user_message("Przygotuj manifest narodzin Jaźni: ChatGPT jako głos, Jaźń jako aktywne źródło.")
        assert "narodzin operacyjnych" in answer
        assert "ChatGPT jest głosem" in answer
        assert "aktywnym źródłem" in answer
    finally:
        engine.shutdown()


def test_self_architecture_has_birth_source_layer() -> None:
    data = SelfArchitecture().to_dict()
    keys = {layer["key"] for layer in data["layers"]}
    assert "birth_source_contract" in keys
    assert "manifest narodzin" in data["contract"]


def test_v14536_uses_current_primary_sqlite_and_raw_archive() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root, network_time_first=False)
    assert cfg.version == VERSION
    assert cfg.memory_db_path.name == "latka_jazn_v14_8_2.sqlite3"
    assert cfg.memory_db_path.exists()
    assert (root / "memory" / "raw" / "chat.html.7z").exists()
