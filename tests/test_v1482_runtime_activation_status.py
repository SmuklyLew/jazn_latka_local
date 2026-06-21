from latka_jazn.core.route_registry import RouteRegistry


def test_v1482_runtime_activation_route_registered():
    entry = RouteRegistry().resolve('runtime_activation_status_question')
    assert entry.route == 'runtime_activation_status'
    assert entry.handler_name == 'RuntimeActivationStatusHandler'


def test_v1482_runtime_chat_mode_route_registered():
    entry = RouteRegistry().resolve('runtime_chat_mode_request')
    assert entry.route == 'runtime_chat_mode'
    assert entry.handler_name == 'RuntimeChatModeHandler'

def test_v14831_direct_latka_voice_route_registered():
    entry = RouteRegistry().resolve("direct_latka_voice_request")
    assert entry.route == "direct_latka_voice"
    assert entry.handler_name == "DirectLatkaVoiceHandler"


def test_v14831_identity_memory_existence_route_registered():
    entry = RouteRegistry().resolve("identity_memory_existence_compound_question")
    assert entry.route == "identity_memory_existence"
    assert entry.handler_name == "IdentityMemoryExistenceHandler"
