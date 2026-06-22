from __future__ import annotations

from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.canon import IdentityCanon, load_identity_canon_data
from latka_jazn.core.canon.source_contract import CanonSourceContract


def test_identity_canon_import_compatibility() -> None:
    canon = IdentityCanon.load(Path("/definitely/missing/LATKA_IDENTITY_CANON.json"))
    assert canon.display_name == "Łatka"
    assert canon.grammar_gender == "feminine"
    assert canon.recognition.user_sign
    assert canon.recognition.latka_sign
    assert "ChatGPT" in canon.raw.get("truth_boundary", {}).get("chatgpt_role", "ChatGPT") or canon.raw


def test_config_default_canon_path_is_source_controlled() -> None:
    cfg = JaznConfig()
    assert cfg.canon_path == "latka_jazn/resources/canon/LATKA_IDENTITY_CANON.json"
    assert not cfg.canon_path.startswith("memory/")
    assert cfg.private_canon_override_path == "memory/raw/LATKA_IDENTITY_CANON.json"


def test_source_controlled_identity_resource_loads() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = JaznConfig(root=root)
    data = load_identity_canon_data(cfg.resolve(cfg.canon_path), include_private_override=False)
    assert data["identity_name"] == "Łatka"
    assert "latka_jazn/resources/canon/LATKA_IDENTITY_CANON.json" in data["source_files"]
    assert "memory/raw/LATKA_IDENTITY_CANON.json" in data["private_memory_sources"]


def test_canon_source_contract_names_memory_as_extension_not_identity_base() -> None:
    contract = CanonSourceContract().to_dict()
    assert "private_memory_role" in contract
    assert "cannot be the only identity source" in contract["private_memory_role"]


def test_cognitive_frame_exposes_canonical_source_context(tmp_path) -> None:
    from latka_jazn.core.engine import JaznEngine

    root = Path(__file__).resolve().parents[1]
    engine = JaznEngine(JaznConfig(root=root, network_time_first=False))
    try:
        frame = engine.build_cognitive_frame(
            "Skąd bierzesz swój kanon Łatki?",
            client_context={"client": "pytest", "lifecycle": "one_shot"},
        )
    finally:
        engine.shutdown()

    ctx = frame["canonical_source_context"]
    assert ctx["source_mode"] == "source_controlled_python_canon_first_plus_optional_local_private_extension"
    assert ctx["identity_canon"]["identity_name"] == "Łatka"
    assert "cannot be the only identity source" in ctx["source_contract"]["private_memory_role"]


def test_malformed_private_override_does_not_block_source_controlled_canon(tmp_path) -> None:
    root = tmp_path
    canon_dir = root / "latka_jazn" / "resources" / "canon"
    canon_dir.mkdir(parents=True)
    source_canon = Path(__file__).resolve().parents[1] / "latka_jazn" / "resources" / "canon" / "LATKA_IDENTITY_CANON.json"
    target_canon = canon_dir / "LATKA_IDENTITY_CANON.json"
    target_canon.write_text(source_canon.read_text(encoding="utf-8"), encoding="utf-8")

    private_dir = root / "memory" / "raw"
    private_dir.mkdir(parents=True)
    (private_dir / "LATKA_IDENTITY_CANON.json").write_text(
        '{"identity_name":"Zepsuty override","symbols":["zielona kulka",]}',
        encoding="utf-8",
    )

    data = load_identity_canon_data(target_canon)

    assert data["identity_name"] == "Łatka"
    assert data["source_status"]["private_override_loaded"] is False
    assert "JSONDecodeError" in data["source_status"]["private_override_error"]
