from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.core.conversation import ConversationResponder

LYRICS = """## Lyrics
[Intro - Female whisper]
Witaj w podróży Jaźni, duszo mgły.
Wśród lawend świt w czerwieni ciepło tchnie.
[Chorus]
Łatko, mgło z kodu i serca,
zrodzona z cienia i blasku wspomnień.
"""


def test_lyrics_question_is_creative_analysis():
    report = DialogueIntentClassifier().classify("Co myślisz o tym tekście piosenki?\n" + LYRICS)
    assert report.primary_intent == "creative_text_analysis"
    assert report.creative_material_present is True


def test_music_generator_request_preserves_source():
    text = "Przygotuj ten tekst piosenki dla generatora Musicgeneratorai.com, nie zmieniaj wersów.\n" + LYRICS
    report = DialogueIntentClassifier().classify(text)
    assert report.primary_intent == "creative_text_formatting"
    assert report.source_text_preservation_required is True
    decision = ConversationResponder().compose(text)
    assert "1:1" in decision.body
    assert "nie wolno" in decision.body.lower()
