
from __future__ import annotations

from pathlib import Path

from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.core.route_registry import RouteRegistry
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator
from latka_jazn.core.template_registry import TemplateRegistry
from latka_jazn.core.runtime_response_synthesizer import RuntimeResponseSynthesizer
from latka_jazn.core.response_generation_mode import build_runtime_provenance
from latka_jazn.core.turn_checkpoint_writer import TurnCheckpointWriter
from latka_jazn.core.turn_trace_reader import TurnTraceReader
from latka_jazn.core.runtime_visible_answer_comparator import RuntimeVisibleAnswerComparator
from latka_jazn.nlp.external_dictionary_adapter import ExternalDictionaryAdapter
from latka_jazn.nlp.language_resource_registry import LanguageResourceRegistry
from latka_jazn.core.source_text_preservation_contract import SourceTextPreservationContract


def test_runtime_source_question_is_not_plain_chatgpt_interpretation():
    report = DialogueIntentClassifier().classify("Skąd bierzesz myśli Jaźni / z Jaźni?")
    assert report.primary_intent == "runtime_source_question"
    entry = RouteRegistry().resolve(report.primary_intent)
    assert entry.route == "runtime_source"
    assert "exact_runtime_text" in entry.required_components


def test_contextual_repair_request_goes_to_runtime_diagnostic():
    report = DialogueIntentClassifier().classify("Sprawdź gdzie i jak to zmienić na prawidłowe działanie.")
    assert report.primary_intent == "runtime_behavior_diagnostic_request"
    entry = RouteRegistry().resolve(report.primary_intent)
    assert entry.handler_name == "RuntimeDiagnosticHandler"


def test_validator_blocks_generic_template_for_specific_intent():
    validation = RuntimeAnswerValidator().validate(
        user_text="Co runtime odpowiedział?",
        body="Przyjmuję tę korektę i zapisuję ją jako kierunek naprawy.",
        route="correction_acknowledged",
        detected_intent="runtime_exact_quote_request",
    )
    assert validation.must_regenerate is True
    assert validation.can_show_to_user is False
    assert validation.missing_required_components


def test_template_origin_and_provenance_are_visible():
    template = TemplateRegistry().classify_body("Tu trzeba rozdzielić źródła i dokładną odpowiedź runtime.", detected_intent="runtime_source_question")
    assert template["template_id"] == "tpl_source_split"
    provenance = build_runtime_provenance(body="Tu trzeba rozdzielić źródła", route="runtime_source", detected_intent="runtime_source_question", handler_name="RuntimeSourceHandler", template_origin=template)
    data = provenance.to_dict()
    assert data["response_generation_mode"] in {"chatgpt_interpretation_required", "runtime_template"}
    assert data["template_id"] == "tpl_source_split"


def test_synthesizer_rewrites_source_question_with_boundary():
    body = "Najuczciwszy model jest hybrydowy."
    template = TemplateRegistry().classify_body(body, detected_intent="runtime_source_question")
    result = RuntimeResponseSynthesizer().synthesize(user_text="Skąd bierzesz myśli?", detected_intent="runtime_source_question", original_body=body, route="source", template_origin=template)
    assert result.should_override is True
    assert "Moje 'myśli'" in result.body
    assert "interpretację" in result.body


def test_dictionary_adapter_does_not_fake_online_lookup(tmp_path: Path):
    adapter = ExternalDictionaryAdapter(tmp_path, allow_network=False)
    local = adapter.lookup("Jaźń")
    assert local.source_name == "local_jazn_mini_lexicon"
    missing = adapter.lookup("nieistniejącyterminpróbny")
    assert missing.source_name == "not_checked_online"
    assert "Nie wykonano lookupu online" in missing.truth_boundary


def test_language_resource_registry_contains_online_sources_with_policy():
    data = LanguageResourceRegistry().to_dict()
    names = {x["name"] for x in data["resources"]}
    assert "Wiktionary" in names
    assert "plWordNet/Słowosieć" in names
    assert data["truth_boundary"].startswith("Rejestr wskazuje")


def test_source_text_preservation_contract_defaults_to_preserve():
    contract = SourceTextPreservationContract.build("[Verse]\nNie zmieniaj mnie", intent="creative_text_formatting")
    assert contract.preserve_exact_text_required is True
    assert contract.added_text_origin_required is True


def test_turn_checkpoint_and_visible_comparator(tmp_path: Path):
    writer = TurnCheckpointWriter(tmp_path)
    writer.build_and_append(
        turn_id="turn-test", trace_id="trace-test", timestamp_header="[czas]", user_text="co runtime?", runtime_text="runtime exact", visible_text="[czas]\nruntime exact",
        detected_intent="runtime_exact_quote_request", route="runtime_source", response_generation_mode="runtime_repair", template_origin={}, validator={}, source_origin={},
    )
    latest = TurnTraceReader(tmp_path).latest()
    assert latest["trace_id"] == "trace-test"
    comp = RuntimeVisibleAnswerComparator(tmp_path).compare("trace-test")
    assert comp["found"] is not False if "found" in comp else True
    assert comp["runtime_text_exact"] == "runtime exact"
