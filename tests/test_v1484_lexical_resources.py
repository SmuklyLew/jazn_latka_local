from __future__ import annotations

import json
from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.nlp_reasoning.lexical_resource_cache import LexicalResourceCache
from latka_jazn.nlp_reasoning.lexical_resource_registry import LexicalResourceRegistry, load_latka_project_lexicon
from main import _build_parser


def test_verified_sources_loads_from_repo() -> None:
    root = Path(__file__).resolve().parents[1]
    registry = LexicalResourceRegistry(root)
    data = registry.load_verified_sources()

    assert data["schema_version"] == "verified_lexical_sources/v14.8.4.005"
    assert data["policy"]["large_data_outside_git"] is True
    assert "morfeusz2-sgjp" in data["sources"]
    assert "polimorf" in data["sources"]
    assert "latka_project_lexicon" in data["sources"]


def test_project_lexicon_loads_core_terms() -> None:
    root = Path(__file__).resolve().parents[1]
    lexicon = load_latka_project_lexicon(root)
    terms = lexicon["terms"]

    assert lexicon["schema_version"] == "latka_project_lexicon/v14.8.4.005"
    assert "Jaźń" in terms
    assert "Łatka" in terms
    assert "memory_gate" in terms
    assert "NLG Plan" in terms
    assert "operational thought frame" in terms


def test_registry_reports_registered_vs_available_truthfully(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path
    resources = root / "latka_jazn" / "resources" / "nlp"
    resources.mkdir(parents=True)
    verified = resources / "verified_sources.json"
    verified.write_text(
        json.dumps(
            {
                "schema_version": "verified_lexical_sources/v14.8.4.005",
                "policy": {"large_data_outside_git": True},
                "sources": {
                    "polimorf": {
                        "source_id": "polimorf",
                        "mode": "offline_external_file_after_license_review",
                        "license": "BSD-2-Clause",
                        "source_url": "https://zil.ipipan.waw.pl/PoliMorf",
                    },
                    "wsjp-pan": {
                        "source_id": "wsjp-pan",
                        "mode": "online_reference_cache_only",
                        "license": "manual review required",
                        "source_url": "https://wsjp.pl/",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("LATKA_POLIMORF_PATH", raising=False)

    statuses = {item.source_id: item for item in LexicalResourceRegistry(root).status()}

    assert statuses["polimorf"].available is False
    assert "LATKA_POLIMORF_PATH" in (statuses["polimorf"].reason or "")
    assert statuses["wsjp-pan"].available is False
    assert statuses["wsjp-pan"].cache_entries == 0
    assert statuses["wsjp-pan"].source_url == "https://wsjp.pl/"


def test_cache_stores_retrieved_at_provider_license_url(tmp_path: Path) -> None:
    cache = LexicalResourceCache(tmp_path, path=tmp_path / "workspace_runtime" / "dictionary_cache.sqlite3")

    cache.store(
        "mediawiki-action-api",
        "Łatka",
        {"title": "Łatka", "extract": "test"},
        "https://example.test/w/api.php",
        "CC BY-SA test fixture",
        provider="wiktionary-mediawiki-api",
        retrieved_at_utc="2026-06-24T00:00:00+00:00",
    )
    hit = cache.lookup("mediawiki-action-api", "Łatka")
    stats = cache.stats()

    assert hit is not None
    assert hit["payload"]["title"] == "Łatka"
    assert hit["source_url"] == "https://example.test/w/api.php"
    assert hit["license"] == "CC BY-SA test fixture"
    assert hit["retrieved_at_utc"] == "2026-06-24T00:00:00+00:00"
    assert hit["provider"] == "wiktionary-mediawiki-api"
    assert stats["entries_by_source"]["mediawiki-action-api"] == 1


def test_no_large_external_dictionary_committed() -> None:
    root = Path(__file__).resolve().parents[1]
    nlp_dir = root / "latka_jazn" / "resources" / "nlp"
    assert nlp_dir.exists()
    for path in nlp_dir.rglob("*"):
        if not path.is_file():
            continue
        assert path.suffix not in {".sqlite", ".sqlite3", ".db", ".dump", ".zip"}
        assert path.stat().st_size < 256 * 1024


def test_config_and_cli_expose_nlp_resource_status(tmp_path: Path) -> None:
    cfg = JaznConfig(root=tmp_path)
    ns = _build_parser().parse_args(["--nlp-resource-status"])

    assert ns.nlp_resource_status is True
    assert cfg.lexical_resource_cache_path == tmp_path / "workspace_runtime" / "dictionary_cache.sqlite3"
    assert cfg.lexical_resources_registry_path.endswith("verified_sources.json")
