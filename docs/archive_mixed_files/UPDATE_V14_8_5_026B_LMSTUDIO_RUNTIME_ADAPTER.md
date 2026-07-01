# v14.8.5.026B - LM Studio runtime adapter

Etap 026B domyka LM Studio jako lokalny backend językowy istniejącego runtime Jaźni.

## Zakres

- `lmstudio_runtime_adapter` preferuje `POST /v1/responses`.
- Gdy Responses nie zwraca widocznego tekstu, adapter używa `POST /v1/chat/completions`.
- Adapter nie wymaga `OPENAI_API_KEY`, nie używa OpenAI cloud API i nie wywołuje endpointu Ollamy `/api/generate`.
- `reasoning_content`, reasoning items i chain-of-thought nie są kopiowane do widocznej odpowiedzi.
- Tożsamość, pamięć, stan, routing, walidacja i truthful fallback pozostają własnością runtime Jaźni.

## Konfiguracja

Obsługiwane są oba warianty nazw:

- `JAZN_LM_STUDIO_MODEL` / `JAZN_LMSTUDIO_MODEL`
- `JAZN_LM_STUDIO_API_BASE` / `JAZN_LMSTUDIO_API_BASE`
- `JAZN_LM_STUDIO_TIMEOUT` / `JAZN_LMSTUDIO_TIMEOUT_SECONDS`
- `JAZN_LM_STUDIO_MAX_OUTPUT_TOKENS` / `JAZN_LMSTUDIO_MAX_OUTPUT_TOKENS`

Domyślny base URL to `http://127.0.0.1:1234/v1`.

## Granica prawdy

Status `configured` oznacza kompletną konfigurację modelu i endpointu, a nie wynik live probe. Jeżeli oba endpointy są niedostępne, adapter zwraca `lmstudio_provider_unavailable`; runtime nie udaje odpowiedzi modelowej i zachowuje własny fallback.
