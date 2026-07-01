from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .adapter_contract import AdapterContract, describe_with_contract
from .base import AdapterStatusSnapshot, ModelAdapterRequest, ModelAdapterResponse


LMSTUDIO_TRUTH_BOUNDARY = (
    "LM Studio jest lokalnym backendem językowym przez OpenAI-compatible API. "
    "Nie wymaga OPENAI_API_KEY i nie jest źródłem tożsamości, pamięci, stanu ani prawdy runtime Jaźni. "
    "Widoczna odpowiedź przechodzi przez istniejący runtime, walidację i truthful fallback."
)

LMSTUDIO_SYSTEM_PROMPT = (
    "Jesteś językową warstwą wykonawczą systemu Jaźni Łatki. Tożsamość, pamięć, stan, "
    "ograniczenia i prawda runtime pochodzą wyłącznie z przekazanego kontekstu. "
    "Odpowiadaj po polsku, naturalnie i krótko. Nie dodawaj timestampu. "
    "Nie ujawniaj rozumowania ani reasoning_content. Zwróć wyłącznie treść widocznej odpowiedzi."
)


class LmStudioRuntimeAdapter:
    name = "lmstudio_runtime_adapter"

    def __init__(
        self,
        *,
        model: str = "",
        api_base: str = "http://127.0.0.1:1234/v1",
        timeout_seconds: float = 45.0,
        max_output_tokens: int = 800,
        root: object | None = None,
    ) -> None:
        self.model = model.strip()
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self._endpoint_reachable: bool | None = None
        self._probe_state = "not_probed" if self.model else "not_configured"
        self._last_probe_error: str | None = None
        self._last_generation_succeeded = False

    def describe(self) -> dict[str, Any]:
        configured = bool(self.model)
        contract = AdapterContract(
            adapter_id=self.name,
            provider="lmstudio",
            kind="openai_compatible_local_api",
            available=configured,
            model_name=self.model or None,
            endpoint=self.api_base,
            can_generate_model_guided_speech=bool(configured and (self._probe_state == "probed_ok" or self._last_generation_succeeded)),
            configured=configured,
            endpoint_reachable=self._endpoint_reachable,
            probe_state=self._probe_state,
            last_probe_error=self._last_probe_error,
            can_attempt_model_guided_speech=configured,
            failure_reason=None if configured else "lmstudio_model_name_missing",
            requires_api_key=False,
            truth_boundary=LMSTUDIO_TRUTH_BOUNDARY,
        )
        return describe_with_contract(
            contract=contract,
            legacy={
                "name": self.name,
                "status": "configured" if configured else "not_configured",
                "model": self.model or "not_configured",
                "api_base": self.api_base,
                "preferred_endpoint": "/responses",
                "fallback_endpoint": "/chat/completions",
            },
        )

    def probe(self) -> AdapterStatusSnapshot:
        if not self.model:
            self._probe_state = "not_configured"
            return self._status_snapshot()
        request = ModelAdapterRequest(prompt="Odpowiedz: OK")
        for endpoint in ("/responses", "/chat/completions"):
            data, error = self._try_post(endpoint, self._probe_payload(endpoint, request))
            if error is None:
                text = self._extract_responses_text(data) if endpoint == "/responses" else self._extract_chat_text(data)[0]
                if text:
                    self._endpoint_reachable = True
                    self._probe_state = "probed_ok"
                    self._last_probe_error = None
                    return self._status_snapshot()
            self._last_probe_error = error or "probe_empty_output"
        self._endpoint_reachable = False
        self._probe_state = "probed_fail"
        return self._status_snapshot()
    def generate(self, request: ModelAdapterRequest) -> ModelAdapterResponse:
        if not self.model:
            return self._response(status="not_configured")

        attempts: list[dict[str, Any]] = []
        responses_payload = {
            "model": self.model,
            "stream": False,
            "instructions": LMSTUDIO_SYSTEM_PROMPT,
            "input": self._user_input(request),
            "max_output_tokens": self.max_output_tokens,
        }
        data, error = self._try_post("/responses", responses_payload)
        if error is not None:
            attempts.append({"endpoint": "/responses", "status": error})
        else:
            text = self._extract_responses_text(data)
            truncated = self._responses_truncated(data)
            attempts.append(
                {"endpoint": "/responses", "status": "completed" if text else "empty", "response_truncated": truncated}
            )
            if text:
                self._mark_generation_success()
                return self._response(
                    text=text,
                    status="completed",
                    model=str(data.get("model") or self.model),
                    sources=attempts,
                    endpoint_used="/responses",
                )

        chat_payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": LMSTUDIO_SYSTEM_PROMPT},
                {"role": "user", "content": self._user_input(request)},
            ],
            "max_tokens": self.max_output_tokens,
        }
        data, error = self._try_post("/chat/completions", chat_payload)
        if error is not None:
            attempts.append({"endpoint": "/chat/completions", "status": error})
            return self._response(status="lmstudio_provider_unavailable", sources=attempts)

        text, truncated = self._extract_chat_text(data)
        attempts.append(
            {"endpoint": "/chat/completions", "status": "completed" if text else "empty", "response_truncated": truncated}
        )
        if not text:
            return self._response(status="lmstudio_response_empty", sources=attempts)
        self._mark_generation_success()
        return self._response(
            text=text,
            status="completed",
            model=str(data.get("model") or self.model),
            sources=attempts,
            endpoint_used="/chat/completions",
        )

    def _probe_payload(self, endpoint: str, request: ModelAdapterRequest) -> dict[str, Any]:
        if endpoint == "/responses":
            return {"model": self.model, "stream": False, "instructions": LMSTUDIO_SYSTEM_PROMPT, "input": request.prompt, "max_output_tokens": 8}
        return {"model": self.model, "stream": False, "messages": [{"role": "system", "content": LMSTUDIO_SYSTEM_PROMPT}, {"role": "user", "content": request.prompt}], "max_tokens": 8}

    def _mark_generation_success(self) -> None:
        self._endpoint_reachable = True
        self._probe_state = "probed_ok"
        self._last_probe_error = None
        self._last_generation_succeeded = True

    def _try_post(self, endpoint: str, payload: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
        try:
            return self._post_json(endpoint, payload), None
        except HTTPError as exc:
            return {}, f"http_error_{exc.code}"
        except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            return {}, "provider_unavailable"

    def _post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            f"{self.api_base}{endpoint}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("LM Studio response must be a JSON object")
        return data

    @staticmethod
    def _extract_responses_text(data: dict[str, Any]) -> str:
        direct = data.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()

        parts: list[str] = []
        for item in data.get("output") or []:
            if not isinstance(item, dict) or LmStudioRuntimeAdapter._is_reasoning(item):
                continue
            for content in item.get("content") or []:
                if not isinstance(content, dict) or LmStudioRuntimeAdapter._is_reasoning(content):
                    continue
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()

    @staticmethod
    def _extract_chat_text(data: dict[str, Any]) -> tuple[str, bool]:
        choices = data.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            return "", False
        choice = choices[0]
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        content = message.get("content")
        parts: list[str] = []
        if isinstance(content, str):
            parts.append(content.strip())
        elif isinstance(content, list):
            for item in content:
                if not isinstance(item, dict) or LmStudioRuntimeAdapter._is_reasoning(item):
                    continue
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(part for part in parts if part).strip(), choice.get("finish_reason") == "length"

    @staticmethod
    def _responses_truncated(data: dict[str, Any]) -> bool:
        details = data.get("incomplete_details")
        reason = details.get("reason") if isinstance(details, dict) else None
        return str(data.get("status") or "").lower() == "incomplete" or reason in {
            "max_output_tokens",
            "length",
        }

    @staticmethod
    def _is_reasoning(payload: dict[str, Any]) -> bool:
        kind = str(payload.get("type") or payload.get("role") or "").lower()
        return "reasoning" in kind or "chain_of_thought" in kind

    @staticmethod
    def _user_input(request: ModelAdapterRequest) -> str:
        context = json.dumps(request.system_context or {}, ensure_ascii=False, separators=(",", ":"))
        return f"{request.prompt}\n\nKONTEKST_JAZNI_JSON:\n{context}"

    def _response(
        self,
        *,
        status: str,
        text: str = "",
        model: str | None = None,
        sources: list[dict[str, Any]] | None = None,
        endpoint_used: str | None = None,
    ) -> ModelAdapterResponse:
        return ModelAdapterResponse(
            text=text,
            provider="lmstudio",
            model=model or self.model or "not_configured",
            status=status,
            sources=sources or [],
            adapter_id=self.name,
            source_origin="model_adapter",
            endpoint_used=endpoint_used,
            status_snapshot=self._status_snapshot(),
            transport={"api_base": self.api_base, "endpoint_used": endpoint_used},
            truth_boundary=LMSTUDIO_TRUTH_BOUNDARY,
        )

    def _status_snapshot(self) -> AdapterStatusSnapshot:
        configured = bool(self.model)
        return AdapterStatusSnapshot(
            adapter_id=self.name,
            provider="lmstudio",
            configured=configured,
            endpoint_reachable=self._endpoint_reachable,
            probe_state=self._probe_state if configured else "not_configured",
            last_probe_error=self._last_probe_error,
            can_attempt_model_guided_speech=configured,
            can_generate_model_guided_speech=bool(configured and (self._probe_state == "probed_ok" or self._last_generation_succeeded)),
        )
