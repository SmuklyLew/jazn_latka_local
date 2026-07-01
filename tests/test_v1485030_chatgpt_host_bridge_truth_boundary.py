from latka_jazn.model_adapters.chatgpt_runtime_adapter import ChatgptRuntimeAdapter


def test_chatgpt_host_is_not_local_generation_capability() -> None:
    status = ChatgptRuntimeAdapter().describe()
    assert status["provider"] == "chatgpt_host"
    assert status["can_attempt_model_guided_speech"] is False
    assert status["can_generate_model_guided_speech"] is False
    assert status["validated"] is False
