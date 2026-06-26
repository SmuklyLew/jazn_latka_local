from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import ModelAdapterRequest, ModelAdapterResponse
from .openai_state_tracker import OpenAIStateTracker

class OpenaiResponsesAdapter:
    name='openai_responses_adapter'

    def __init__(self, *, api_key: str | None = None, model: str = "gpt-5.2", api_base: str = "https://api.openai.com/v1", timeout_seconds: float = 45.0, max_output_tokens: int = 800, root: str | Path | None = None) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.state_tracker = OpenAIStateTracker(Path(root)) if root is not None else None

    def describe(self) -> dict:
        configured = bool(self.api_key and self.model)
        return {
            "schema_version": "openai_responses_adapter/v14.8.2.4",
            "name": self.name,
            "status": "configured" if configured else "not_configured",
            "model": self.model,
            "api_base": self.api_base,
            "state_tracker": "enabled" if self.state_tracker else "disabled",
            "conversation_state_contract": "previous_response_id jest ciągłością OpenAI Responses API, nie dowodem aktywnej Jaźni",
            "truth_boundary": "Model generuje język z kontekstu przekazanego przez Jaźń. Nie jest źródłem jej tożsamości ani pamięci.",
        }

    def generate(self, request: ModelAdapterRequest) -> ModelAdapterResponse:
        if not self.api_key or not self.model:
            return ModelAdapterResponse(text='', provider=self.name, model=self.model or 'not_configured', status='not_configured')
        context = json.dumps(request.system_context or {}, ensure_ascii=False, separators=(",", ":"))
        state, session_id = self._load_state_for_request(request)
        payload = {
            "model": self.model,
            "store": False,
            "max_output_tokens": self.max_output_tokens,
            "instructions": (
                "Jesteś językową i rozumującą warstwą wykonawczą systemu Jaźni Łatki. "
                "Tożsamość, pamięć, stan, zasady prawdy i ograniczenia pochodzą wyłącznie z przekazanego kontekstu runtime. "
                "Odpowiedz po polsku, naturalnie, w pierwszej osobie Łatki. Nie wspominaj o architekturze, runtime ani modelu, "
                "chyba że użytkownik o to pyta. Nie dopisuj faktów, wspomnień, źródeł ani działań, których nie ma w kontekście. "
                "Zwróć wyłącznie treść odpowiedzi, bez timestampu i bez opisu procesu."
            ),
            "input": f"{request.prompt}\n\nKONTEKST_JAZNI_JSON:\n{context}",
        }
        if state and state.previous_response_id:
            payload["previous_response_id"] = state.previous_response_id
        try:
            data = self._post_json(payload)
            text = str(data.get("output_text") or "").strip()
            if not text:
                text = self._extract_output_text(data)
            state_payload = None
            if self.state_tracker and session_id and data.get("id"):
                state_payload = self.state_tracker.update_from_response(session_id=session_id, response=data, store_policy=False).to_dict()
            return ModelAdapterResponse(
                text=text,
                provider=self.name,
                model=str(data.get("model") or self.model),
                status="completed" if text else str(data.get("status") or "empty_output"),
                sources=[{"response_id": data.get("id"), "status": data.get("status"), "openai_state": state_payload}],
            )
        except HTTPError as exc:
            return ModelAdapterResponse(text='', provider=self.name, model=self.model, status=f'http_error_{exc.code}')
        except OSError as exc:
            return ModelAdapterResponse(text='', provider=self.name, model=self.model, status=self._status_from_error(str(exc)))
        except (URLError, TimeoutError, ValueError):
            return ModelAdapterResponse(text='', provider=self.name, model=self.model, status='adapter_error')

    def _load_state_for_request(self, request: ModelAdapterRequest):
        context = request.system_context or {}
        client_context = context.get("client_context") if isinstance(context.get("client_context"), dict) else {}
        session_id = str(client_context.get("session_id") or context.get("session_id") or "").strip() or None
        if not self.state_tracker or not session_id:
            return None, session_id
        return self.state_tracker.load(session_id), session_id

    def _post_json(self, payload: dict) -> dict:
        if os.name == "nt":
            return self._post_json_windows(payload)
        req = Request(
            f"{self.api_base}/responses",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json_windows(self, payload: dict) -> dict:
        script = (
            "$ErrorActionPreference='Stop';"
            "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;"
            "[Console]::InputEncoding=[Text.UTF8Encoding]::new($false);"
            "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
            "$body=[Console]::In.ReadToEnd();"
            "$headers=@{Authorization=('Bearer '+$env:OPENAI_API_KEY)};"
            "try{$r=Invoke-RestMethod -Uri $env:JAZN_ADAPTER_API_URL -Method Post -Headers $headers "
            "-ContentType 'application/json; charset=utf-8' -Body $body -TimeoutSec ([int]$env:JAZN_ADAPTER_TIMEOUT);"
            "$r|ConvertTo-Json -Depth 100 -Compress}"
            "catch{if($_.ErrorDetails.Message){[Console]::Error.Write($_.ErrorDetails.Message)}"
            "else{[Console]::Error.Write($_.Exception.Message)};exit 1}"
        )
        env = dict(os.environ)
        env["OPENAI_API_KEY"] = self.api_key
        env["JAZN_ADAPTER_API_URL"] = f"{self.api_base}/responses"
        env["JAZN_ADAPTER_TIMEOUT"] = str(max(1, int(self.timeout_seconds)))
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=self.timeout_seconds + 10,
            check=False,
        )
        if completed.returncode != 0:
            raise OSError((completed.stderr or "PowerShell HTTP transport failed").strip())
        return json.loads(completed.stdout)

    @staticmethod
    def _status_from_error(message: str) -> str:
        low = (message or "").lower()
        if "insufficient_quota" in low or "current quota" in low:
            return "insufficient_quota"
        if "invalid_api_key" in low or "incorrect api key" in low or "(401)" in low:
            return "authentication_error"
        if "(429)" in low or "rate_limit" in low:
            return "rate_limited"
        return "adapter_error"

    @staticmethod
    def _extract_output_text(data: dict) -> str:
        parts: list[str] = []
        for item in data.get("output") or []:
            for content in item.get("content") or []:
                if content.get("type") == "output_text" and content.get("text"):
                    parts.append(str(content["text"]))
        return "\n".join(parts).strip()
