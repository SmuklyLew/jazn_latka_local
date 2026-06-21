from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.source_origin_ledger import SourceOriginLedger
from pathlib import Path


def test_text_change_source_question():
    report = DialogueIntentClassifier().classify("Dlaczego zmieniłaś tekst? I dlaczego dodałaś mam swój los?")
    assert report.primary_intent == "runtime_source_question"
    decision = ConversationResponder().compose("Dlaczego zmieniłaś tekst? I dlaczego dodałaś mam swój los?")
    assert decision.route == "runtime_source_question"
    assert "ChatGPT" in decision.body or "runtime" in decision.body


def test_source_origin_ledger_entry_for_creative_text(tmp_path: Path):
    ledger = SourceOriginLedger(tmp_path)
    entry = ledger.build_entry(turn_id="t1", user_text="tekst piosenki", response_text="odpowiedź", route="creative_text_formatting", detected_intent="creative_text_formatting")
    assert entry.preserved_source_text is True
    assert entry.modified_source_text is False
    path = ledger.append(entry)
    assert path.exists()
