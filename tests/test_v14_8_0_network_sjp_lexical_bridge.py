from pathlib import Path

from latka_jazn.config import JaznConfig
from latka_jazn.core.startup_contract import dictionary_provider_status
from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.nlp.external_dictionary_adapter import ExternalDictionaryAdapter
from latka_jazn.nlp.polish_lexical_sources import MINI_LEXICON
from latka_jazn.nlp.providers.sjp_reference_provider import SJPReferenceProvider


def _providers(result):
    return {item.get('provider'): item for item in result.provider_statuses}


def test_sjp_reference_provider_returns_reference_link_without_claiming_definition():
    result = SJPReferenceProvider().lookup('spać')
    assert result.provider == 'sjp_reference'
    assert result.status == 'manual_reference_available'
    assert result.source_url and result.source_url.startswith('https://sjp.pl/')
    assert result.definitions == []
    assert 'nie pobiera definicji' in result.license_hint or 'nie kopiuje definicji' in result.license_hint
    assert 'link referencyjny' in result.truth_boundary


def test_external_dictionary_adapter_reports_sjp_and_wsjp_statuses_offline(tmp_path: Path):
    adapter = ExternalDictionaryAdapter(tmp_path, allow_network=False)
    result = adapter.lookup('spać')
    providers = _providers(result)
    assert providers['wiktionary_mediawiki_api']['status'] == 'network_disabled'
    assert providers['sjp_reference']['status'] == 'manual_reference_available'
    assert providers['wsjp_reference']['status'] == 'manual_reference_available'
    assert any(src.get('provider') == 'sjp_reference' for src in result.sources)
    assert any(src.get('provider') == 'wsjp_reference' for src in result.sources)
    assert result.found is False
    assert 'allow_network=False' in result.truth_boundary


def test_dictionary_provider_status_exposes_sjp_and_wsjp_provider_files():
    cfg = JaznConfig()
    status = dictionary_provider_status(cfg)
    assert status['schema_version'] in {'dictionary_provider_status/v14.8.0', 'dictionary_provider_status/v14.8.1', 'dictionary_provider_status/v14.8.2.4', 'dictionary_provider_status/v14.8.2.4'}
    assert 'sjp_reference' in status['provider_order']
    assert 'wsjp_reference' in status['provider_order']
    assert status['sjp_reference_provider'] is True
    assert status['wsjp_reference_provider'] is True


def test_nlp_sjp_update_request_routes_to_system_update_not_dictionary_lookup():
    cls = DialogueIntentClassifier()
    report = cls.classify('Najpierw przygotuj dokładny plan aktualizacji NLP i SJP dla systemu Jaźni, potem pełną paczkę do pobrania.')
    assert report.primary_intent == 'system_update_execution_request'
    assert 'dictionary_lookup_request' not in report.secondary_intents
    assert report.update_request is True


def test_domain_lexicon_contains_nlp_sjp_wsjp():
    for key in ('nlp', 'sjp', 'wsjp'):
        assert key in MINI_LEXICON
        assert MINI_LEXICON[key]['definitions']
