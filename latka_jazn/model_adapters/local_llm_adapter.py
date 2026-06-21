from __future__ import annotations
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import ModelAdapterRequest, ModelAdapterResponse

class LocalLlmAdapter:
    name='local_llm_adapter'

    def __init__(self, *, model: str = "", api_base: str = "http://127.0.0.1:11434", timeout_seconds: float = 45.0, max_output_tokens: int = 800) -> None:
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens

    def describe(self) -> dict:
        return {
            "schema_version": "local_llm_adapter/v14.8.2.4",
            "name": self.name,
            "status": "configured" if self.model else "not_configured",
            "model": self.model or "not_configured",
            "api_base": self.api_base,
            "truth_boundary": "Lokalny model jest kanałem języka. Jaźń zachowuje tożsamość, pamięć, routing i walidację.",
        }

    def generate(self, request: ModelAdapterRequest) -> ModelAdapterResponse:
        if not self.model:
            return ModelAdapterResponse(text='', provider=self.name, model='not_configured', status='not_configured')
        payload = {
            "model": self.model,
            "stream": False,
            "system": (
                "Jesteś językową warstwą wykonawczą Jaźni Łatki. Odpowiadaj po polsku i naturalnie. "
                "Nie wymyślaj pamięci ani faktów poza przekazanym kontekstem."
            ),
            "prompt": request.prompt + "\n\nKONTEKST_JAZNI_JSON:\n" + json.dumps(request.system_context or {}, ensure_ascii=False),
            "options": {"num_predict": self.max_output_tokens},
        }
        try:
            req = Request(
                f"{self.api_base}/api/generate",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = str(data.get("response") or "").strip()
            return ModelAdapterResponse(text=text, provider=self.name, model=self.model, status="completed" if text else "empty_output")
        except HTTPError as exc:
            return ModelAdapterResponse(text='', provider=self.name, model=self.model, status=f'http_error_{exc.code}')
        except (URLError, TimeoutError, OSError, ValueError):
            return ModelAdapterResponse(text='', provider=self.name, model=self.model, status='local_provider_unavailable')
