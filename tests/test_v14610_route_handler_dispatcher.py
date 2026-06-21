from latka_jazn.core.route_handler_dispatcher import RouteHandlerDispatcher
from latka_jazn.core.route_registry import RouteRegistry

class FakeDictionary:
    def lookup(self, term):
        from latka_jazn.nlp.dictionary_entry import DictionaryLookupResult
        return DictionaryLookupResult(term=term, normalized_term=term.lower(), definitions=['test definition'], lemma_candidates=[term.lower()], found=True, confidence=0.9, source_name='fake', sources=[{'provider':'fake'}])

def test_dispatcher_executes_dictionary_handler():
    entry = RouteRegistry().resolve('dictionary_lookup_request')
    result = RouteHandlerDispatcher().dispatch(entry, 'co znaczy "Jaźń"?', {'dictionary_adapter': FakeDictionary(), 'required_components': entry.required_components})
    assert result.handler_name == 'DictionaryLookupHandler'
    assert result.data.get('dictionary_lookup')
    assert 'Sprawdziłam słownikowo' in result.body

def test_dispatcher_external_research_requires_web_execution():
    entry = RouteRegistry().resolve('external_research_request')
    result = RouteHandlerDispatcher().dispatch(entry, 'sprawdź w internecie aktualne źródła', {})
    assert result.handler_name == 'ExternalResearchHandler'
    assert result.data['external_research_result']['status'] == 'requires_external_web_execution'
