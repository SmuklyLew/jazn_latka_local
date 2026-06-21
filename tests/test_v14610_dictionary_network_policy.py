from pathlib import Path
from latka_jazn.config import JaznConfig
from latka_jazn.nlp.external_dictionary_adapter import ExternalDictionaryAdapter
from latka_jazn.nlp.providers.mediawiki_wiktionary_provider import MediaWikiWiktionaryProvider

ROOT = Path(__file__).resolve().parents[1]

def test_config_network_defaults_are_true():
    cfg = JaznConfig(root=ROOT)
    assert cfg.allow_network is True
    assert cfg.dictionary_allow_network is True
    assert cfg.dictionary_online_lookup_timeout_seconds > 0

def test_dictionary_adapter_network_disabled_is_explicit(tmp_path):
    adapter = ExternalDictionaryAdapter(tmp_path, allow_network=False)
    result = adapter.lookup('nieistniejące_hasło_testowe')
    assert result.cache_status == 'miss_network_disabled'
    assert any(s.get('status') == 'network_disabled' for s in result.provider_statuses)

def test_engine_config_passes_network_flag():
    from latka_jazn.core.engine import JaznEngine
    cfg = JaznConfig(root=ROOT)
    engine = JaznEngine(cfg)
    try:
        assert engine.external_dictionary_adapter.allow_network is True
    finally:
        engine.shutdown()

def test_mediawiki_provider_has_timeout_and_disabled_status():
    provider = MediaWikiWiktionaryProvider(allow_network=False, user_agent='test', timeout_seconds=1.5)
    result = provider.lookup('jaźń')
    assert result.status == 'network_disabled'
    assert provider.http.timeout_seconds == 1.5
