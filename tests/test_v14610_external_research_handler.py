from latka_jazn.core.handlers.external_research_handler import ExternalResearchHandler

def test_external_research_handler_is_structural_not_generic():
    result = ExternalResearchHandler().handle('sprawdź w internecie aktualne dokumenty', {})
    assert result.data['external_research_result']['status'] == 'requires_external_web_execution'
    assert result.missing_components == ['local_general_web_search_provider']
    assert 'requires_external_web_execution' in result.body
