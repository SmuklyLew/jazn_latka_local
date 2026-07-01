from __future__ import annotations

import json

import pytest

from latka_jazn.config import JaznConfig
from latka_jazn.core.model_guided_response_synthesizer import ModelGuidedResponseSynthesizer
from latka_jazn.model_adapters.base import ModelAdapterRequest
from latka_jazn.model_adapters.lmstudio_runtime_adapter import (
    LMSTUDIO_SYSTEM_PROMPT,
    LmStudioRuntimeAdapter,
)


def _request() -> ModelAdapterRequest:
    return ModelAdapterRequest(prompt="Powiedz krótko, że jesteś obok.", system_context={"route": "ordinary_dialogue"})


def _adapter() -> LmStudioRuntimeAdapter:
    return LmStudioRuntimeAdapter(model="local-test-model", api_base="http://127.0.0.1:1234/v1")


def test_describe_without_model_is_truthfully_not_configured() -> None:
    status = LmStudioRuntimeAdapter().describe()

    assert status["status"] == "not_configured"
    assert status["failure_reason"] == "lmstudio_model_name_missing"
    assert status["available"] is False
    assert status["can_generate_model_guided_speech"] is False
    assert status["requires_api_key"] is False


def test_describe_with_model_is_configured_without_openai_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    status = _adapter().describe()

    assert status["status"] == "configured"
    assert status["provider"] == "lmstudio"
    assert status["kind"] == "openai_compatible_local_api"
    assert status["can_attempt_model_guided_speech"] is True
    assert status["can_generate_model_guided_speech"] is False
    assert status["requires_api_key"] is False


@pytest.mark.parametrize(
    ("name", "value", "field"),
    [
        ("JAZN_LMSTUDIO_MODEL", "alias-model", "lm_studio_model_name"),
        ("JAZN_LMSTUDIO_API_BASE", "http://127.0.0.1:9999/v1/", "lm_studio_api_base"),
        ("JAZN_LMSTUDIO_TIMEOUT_SECONDS", "7.5", "lm_studio_timeout_seconds"),
        ("JAZN_LMSTUDIO_MAX_OUTPUT_TOKENS", "321", "lm_studio_max_output_tokens"),
    ],
)
def test_lmstudio_compact_env_aliases(monkeypatch, name: str, value: str, field: str) -> None:
    for key in [
        "JAZN_LM_STUDIO_MODEL",
        "JAZN_LMSTUDIO_MODEL",
        "JAZN_LM_STUDIO_API_BASE",
        "JAZN_LMSTUDIO_API_BASE",
        "JAZN_LM_STUDIO_TIMEOUT",
        "JAZN_LMSTUDIO_TIMEOUT_SECONDS",
        "JAZN_LM_STUDIO_MAX_OUTPUT_TOKENS",
        "JAZN_LMSTUDIO_MAX_OUTPUT_TOKENS",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(name, value)

    actual = getattr(JaznConfig(), field)

    expected: object = value.rstrip("/")
    if field == "lm_studio_timeout_seconds":
        expected = 7.5
    elif field == "lm_studio_max_output_tokens":
        expected = 321
    assert actual == expected


def test_responses_endpoint_parses_output_text(monkeypatch) -> None:
    adapter = _adapter()
    calls: list[tuple[str, dict]] = []

    def fake_post(endpoint: str, payload: dict) -> dict:
        calls.append((endpoint, payload))
        return {"model": "loaded-model", "output_text": "Jestem obok."}

    monkeypatch.setattr(adapter, "_post_json", fake_post)
    response = adapter.generate(_request())

    assert response.status == "completed"
    assert response.text == "Jestem obok."
    assert response.model == "loaded-model"
    assert [endpoint for endpoint, _ in calls] == ["/responses"]
    assert calls[0][1]["instructions"] == LMSTUDIO_SYSTEM_PROMPT
    assert "KONTEKST_JAZNI_JSON" in calls[0][1]["input"]
    assert "Authorization" not in json.dumps(calls[0][1])


def test_responses_endpoint_parses_nested_output_content_and_ignores_reasoning(monkeypatch) -> None:
    adapter = _adapter()
    monkeypatch.setattr(
        adapter,
        "_post_json",
        lambda endpoint, payload: {
            "output": [
                {"type": "reasoning", "content": [{"type": "reasoning_text", "text": "ukryte rozumowanie"}]},
                {
                    "type": "message",
                    "content": [
                        {"type": "reasoning_content", "text": "też ukryte"},
                        {"type": "output_text", "text": "Widoczna odpowiedź."},
                    ],
                },
            ]
        },
    )

    response = adapter.generate(_request())

    assert response.text == "Widoczna odpowiedź."
    assert "ukryte" not in response.text


def test_fallback_chat_completions_parses_content_and_never_calls_ollama(monkeypatch) -> None:
    adapter = _adapter()
    endpoints: list[str] = []

    def fake_post(endpoint: str, payload: dict) -> dict:
        endpoints.append(endpoint)
        if endpoint == "/responses":
            raise OSError("responses unavailable")
        assert payload["messages"][0] == {"role": "system", "content": LMSTUDIO_SYSTEM_PROMPT}
        assert payload["max_tokens"] == 800
        return {
            "model": "loaded-model",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": "Odpowiedź z fallbacku.", "reasoning_content": "nie pokazuj"},
                }
            ],
        }

    monkeypatch.setattr(adapter, "_post_json", fake_post)
    response = adapter.generate(_request())

    assert endpoints == ["/responses", "/chat/completions"]
    assert all("/api/generate" not in endpoint for endpoint in endpoints)
    assert response.text == "Odpowiedź z fallbacku."
    assert "nie pokazuj" not in response.text


def test_finish_reason_length_marks_source_as_truncated_without_reasoning(monkeypatch) -> None:
    adapter = _adapter()

    def fake_post(endpoint: str, payload: dict) -> dict:
        if endpoint == "/responses":
            return {"output": []}
        return {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"content": "Ucięta odpowiedź.", "reasoning_content": "sekret"},
                }
            ]
        }

    monkeypatch.setattr(adapter, "_post_json", fake_post)
    response = adapter.generate(_request())

    assert response.text == "Ucięta odpowiedź."
    assert response.sources[-1]["response_truncated"] is True
    assert "sekret" not in response.text


def test_connection_errors_return_provider_unavailable(monkeypatch) -> None:
    adapter = _adapter()
    monkeypatch.setattr(adapter, "_post_json", lambda endpoint, payload: (_ for _ in ()).throw(OSError("offline")))

    response = adapter.generate(_request())

    assert response.status == "lmstudio_provider_unavailable"
    assert response.text == ""
    assert [item["endpoint"] for item in response.sources] == ["/responses", "/chat/completions"]


def test_empty_responses_return_lmstudio_response_empty(monkeypatch) -> None:
    adapter = _adapter()
    monkeypatch.setattr(adapter, "_post_json", lambda endpoint, payload: {"output": []} if endpoint == "/responses" else {"choices": []})

    response = adapter.generate(_request())

    assert response.status == "lmstudio_response_empty"
    assert response.text == ""


def test_protected_intent_skips_lmstudio_call_and_keeps_runtime_fallback(monkeypatch) -> None:
    adapter = _adapter()
    monkeypatch.setattr(adapter, "_post_json", lambda endpoint, payload: pytest.fail("protected intent called LM Studio"))

    result = ModelGuidedResponseSynthesizer().synthesize(
        adapter=adapter,
        user_text="Podaj dokładny tekst runtime.",
        draft_body="Dokładny tekst runtime.",
        detected_intent="runtime_exact_quote_request",
        route="runtime_truth",
        cognitive_frame={},
        response_policy={},
    )

    assert result.used is False
    assert result.body == "Dokładny tekst runtime."
    assert result.status == "skipped"
    assert result.reason == "intent_requires_exact_runtime_or_external_source"
