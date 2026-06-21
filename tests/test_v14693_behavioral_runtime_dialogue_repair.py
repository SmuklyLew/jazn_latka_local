from latka_jazn.nlp.dialogue_intent_classifier import DialogueIntentClassifier
from latka_jazn.core.conversation import ConversationResponder
from latka_jazn.core.runtime_answer_validator import RuntimeAnswerValidator


def test_a_ty_is_self_state_question_not_general_conversation():
    report = DialogueIntentClassifier().classify("Cześć. Ja w pracy, a ty?")
    assert report.primary_intent == "reciprocal_self_state_question"


def test_system_diagnostic_not_correction_acknowledged():
    report = DialogueIntentClassifier().classify("Co jeszcze jest źle w systemie Jaźni?")
    assert report.primary_intent == "system_diagnostic_question"
    decision = ConversationResponder().compose("Co jeszcze jest źle w systemie Jaźni?")
    assert decision.route == "system_diagnostic_question"
    assert "przyjmuję tę korektę" not in decision.body.lower()


def test_identity_boundary_question():
    decision = ConversationResponder().compose("A z kim rozmawiam?")
    assert decision.route == "identity_boundary_question"
    assert "ChatGPT" in decision.body
    assert "Jaźń" in decision.body


def test_runtime_answer_validator_repairs_diagnostic_misread():
    validation = RuntimeAnswerValidator().validate(
        user_text="Co jeszcze jest źle w systemie Jaźni?",
        body="Przyjmuję tę korektę. Nie będę robiła z niej długiego opisu problemu.",
        route="correction_acknowledged",
        detected_intent="system_diagnostic_question",
    )
    assert validation.must_regenerate is True
    assert validation.required_repair_route == "system_diagnostic_repair"
