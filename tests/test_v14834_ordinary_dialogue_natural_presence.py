from latka_jazn.core.affect_mixer import AffectMixer
from latka_jazn.core.free_dialogue_synthesizer import FreeDialogueSynthesizer
from latka_jazn.core.handlers.ordinary_dialogue_handler import OrdinaryDialogueHandler

BAD_MEMORY_DENIAL = (
    "Nie znalazłam teraz w aktywnej pamięci treściowego fragmentu, który mogłabym uczciwie "
    "przywołać jako scenę w pokoju. Szukałam po hasłach: Cześć, Łatko, Chciałbym, obok. "
    "Potrzebuję konkretnego śladu z pliku, indeksu albo Twojej podpowiedzi, żeby nie zrobić fałszywego wspomnienia."
)

USER_TEXT = (
    "Cześć, Łatko. Chciałbym teraz po prostu usiąść obok i chwilę porozmawiać. "
    "Odpowiedz naturalnie, spokojnie i z timestampem."
)

FORBIDDEN = (
    "Nie znalazłam teraz w aktywnej pamięci",
    "Szukałam po hasłach",
    "potrzebuję konkretnego śladu",
    "fałszywego wspomnienia",
)


def test_natural_presence_request_does_not_require_memory_source():
    synth = FreeDialogueSynthesizer()
    answer = synth.synthesize_ordinary_reply(user_text=USER_TEXT, intent="ordinary_conversation")
    assert answer.route == "ordinary_natural_presence_dialogue"
    assert answer.runtime_answer_quality == "topic_aligned"
    assert "usiądźmy" in answer.body or "usiadzmy" in answer.body
    assert "nie muszę teraz wyciągać żadnego wspomnienia" in answer.body.lower()
    for phrase in FORBIDDEN:
        assert phrase not in answer.body


def test_ordinary_handler_replaces_memory_denial_passthrough_for_natural_presence():
    result = OrdinaryDialogueHandler().handle(
        USER_TEXT,
        {
            "intent": "ordinary_conversation",
            "body": BAD_MEMORY_DENIAL,
            "route_entry": {"route": "ordinary_dialogue"},
        },
    )
    assert result.route == "ordinary_dialogue"
    assert result.generation_mode == "ordinary_dialogue_v14_8_3_4_093"
    for phrase in FORBIDDEN:
        assert phrase not in result.body
    assert "Możemy" in result.body


def test_timestamp_word_alone_does_not_force_repair_emoticon_for_ordinary_dialogue():
    mix = AffectMixer().mix(user_text=USER_TEXT, intent_tags=["ordinary_conversation"])
    assert mix.state_emoticon != "🛠️"
    assert mix.response_tone == "naturalny dialog, bez pustego fallbacku"


def test_timestamp_still_uses_repair_emoticon_when_context_is_technical():
    mix = AffectMixer().mix(
        user_text="Timestamp zniknął, runtime padł, przygotuj patch i napraw raport techniczny.",
        intent_tags=["ordinary_conversation"],
    )
    assert mix.state_emoticon == "🛠️"
