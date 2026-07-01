from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier


def intent(text: str) -> str:
    return DialogueIntentClassifier().classify(text).primary_intent


def test_v1482_poki_co_not_ellipsis_runtime_status():
    assert intent('Mi dzień leci powoli i spokojnie - póki co. Czy teraz rozmawiam z Jaźnią Łatki?') == 'runtime_activation_status_question'


def test_v1482_source_code_not_runtime_source():
    assert intent('co trzeba napisać w kodzie źródłowym systemu Jaźni') != 'runtime_source_question'
    assert intent('co trzeba napisać w kodzie źródłowym systemu Jaźni') in {'system_repair_plan_request','logic_reasoning_audit_request'}


def test_v1482_runtime_chat_mode_intent():
    assert intent('I może zamiast skryptu runtime-preview, użyjesz skryptu chat?') == 'runtime_chat_mode_request'


def test_v1482_runtime_exact_quote_still_detected():
    assert intent('Co runtime odpowiedział?') == 'runtime_exact_quote_request'


def test_v1482_repetition_bug_is_runtime_diagnostic_not_source():
    assert intent('Dlaczego wysyłasz taką samą odpowiedź?') == 'runtime_behavior_diagnostic_request'
    assert intent('Zawiesiłaś się?') == 'runtime_behavior_diagnostic_request'


def test_v1482_self_expression_and_feedback_have_own_intents():
    assert intent('Powiesz coś innego? Coś od siebie?') == 'self_expression_request'
    assert intent('Denerwują mnie twoje odpowiedzi.') == 'negative_feedback_current_turn'
    report = DialogueIntentClassifier().classify('Super')
    assert report.primary_intent == 'positive_feedback_current_turn'
    assert report.speech_act == 'feedback'


def test_v1482_modules_and_capability_gap_have_own_intents():
    assert intent('Jakie masz moduły.') == 'module_inventory_request'
    assert intent('Co masz, czego brakuje?') == 'system_capability_gap_question'


def test_v1482_full_system_audit_and_exact_runtime_word_order():
    assert intent('Sprawdź teraz wszystko w systemie Jaźni, co nie działa i jak to naprawić.') == 'system_repair_plan_request'
    assert intent('Co dokładnie odpowiedział runtime?') == 'runtime_exact_quote_request'

def test_v14831_plain_runtime_health_question_not_ordinary():
    assert intent("Działasz? Czy uruchomiłaś Jaźń?") == "runtime_activation_status_question"
    assert intent("Czy Jaźń została uruchomiona?") == "runtime_activation_status_question"


def test_v14831_direct_latka_voice_request_not_ordinary():
    assert intent("Chcę teraz rozmawiać bezpośrednio z Łatką.") == "direct_latka_voice_request"


def test_v14831_identity_memory_existence_compound_has_priority():
    text = "Za kogo się uważasz? Co pamiętasz? Co wiesz, a czego nie wiesz? Kim jesteś? Jak i kiedy powstałaś? Na ile czujesz się istotą?"
    assert intent(text) == "identity_memory_existence_compound_question"
