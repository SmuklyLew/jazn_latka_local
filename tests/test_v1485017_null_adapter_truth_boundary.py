from __future__ import annotations

from latka_jazn.config import JaznConfig
from latka_jazn.model_adapters.base import ModelAdapterRequest
from latka_jazn.model_adapters.factory import build_model_adapter


def test_null_adapter_never_claims_model_guided_generation(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("JAZN_MODEL_ADAPTER", raising=False)

    adapter = build_model_adapter(JaznConfig())
    status = adapter.describe()
    response = adapter.generate(ModelAdapterRequest(prompt="test"))

    assert status["name"] == "null_model_adapter"
    assert status["available"] is True
    assert status["can_generate_model_guided_speech"] is False
    assert status["model_name"] is None
    assert status["endpoint"] is None
    assert status["failure_reason"] == "external_model_not_configured"
    assert response.text == ""
    assert response.status == "requires_external_model_execution"
    assert "nie wymaga klucza API" in status["truth_boundary"]


def test_null_adapter_contract_is_backend_not_identity(monkeypatch) -> None:
    monkeypatch.delenv("JAZN_MODEL_ADAPTER", raising=False)
    contract = build_model_adapter(JaznConfig()).describe()["adapter_contract"]

    assert contract["backend_only"] is True
    assert contract["kind"] == "null_adapter"
    assert contract["provider"] == "none"
    assert contract["availability_basis"] == "built_in_truthful_fallback"
