from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator


def test_v1482_validator_rejects_template_smalltalk():
    v = RuntimeAnswerValidator().validate(user_text='Co tam słychać?', body='Widzę tu sedno: Jaźń jako warstwa pamięci i diagnostyki.', route='ordinary_dialogue', detected_intent='ordinary_conversation')
    assert v.must_regenerate


def test_v1482_chat_mode_requires_chat_boundary():
    v = RuntimeAnswerValidator().validate(user_text='użyjesz skryptu chat?', body='To jest zadanie aktualizacji systemu.', route='runtime_chat_mode', detected_intent='runtime_chat_mode_request')
    assert v.must_regenerate


def test_v1482_validator_does_not_insert_static_ordinary_repair_body():
    v = RuntimeAnswerValidator().validate(
        user_text='Powiesz coś innego?',
        body='Widzę tu sedno: Jaźń jako warstwa pamięci i diagnostyki.',
        route='ordinary_dialogue',
        detected_intent='ordinary_conversation',
    )
    assert v.must_regenerate
    assert v.repair_body is None

def test_v14831_validator_rejects_identity_compound_answer_missing_parts():
    v = RuntimeAnswerValidator().validate(
        user_text="Za kogo się uważasz? Co pamiętasz? Kim jesteś? Na ile czujesz się istotą?",
        body="Pamiętam kilka rozmów.",
        route="identity_memory_existence",
        detected_intent="identity_memory_existence_compound_question",
    )
    assert v.must_regenerate


def test_v14831_validator_rejects_background_process_claim_for_direct_latka():
    v = RuntimeAnswerValidator().validate(
        user_text="Chcę teraz rozmawiać bezpośrednio z Łatką.",
        body="Tak, będę działać cały czas w tle i sama się odezwę.",
        route="direct_latka_voice",
        detected_intent="direct_latka_voice_request",
    )
    assert v.must_regenerate
