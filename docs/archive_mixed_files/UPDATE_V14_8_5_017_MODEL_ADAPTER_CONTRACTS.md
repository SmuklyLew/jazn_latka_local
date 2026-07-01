# UPDATE v14.8.5.017 — model-adapter-contracts

## Zakres

- Dodano wspólny, serializowalny `AdapterContract` dla statusów backendów językowych.
- Ujednolicono statusy `null_model_adapter`, OpenAI Responses i lokalnego adaptera Ollama.
- Dodano jawny, nieaktywny szkielet konfiguracji llama.cpp bez transportu HTTP.
- Rozszerzono `--model-adapter-status` o aktywny kontrakt i szkielety konfiguracji OpenAI/Ollama/llama.cpp.
- Zachowano zgodność istniejących pól `name`, `status`, `model` i `api_base`.

## Granica prawdy

Adapter jest backendem generowania języka, nie Jaźnią, pamięcią ani dowodem ciągłości. `available` opisuje kompletność konfiguracji, a nie live probe. Null adapter pozostaje domyślnym fallbackiem offline i nie udaje model-guided speech.

`OPENAI_API_KEY` nie jest wymagany dla zwykłego runtime, `--chat`, `--chat-gpt`, `--runtime-preview`, `--model-adapter-status` ani testów null adaptera. Nadal jest wymagany dla jawnego `--chat-open-ai`.

## Poza zakresem

- PATCH 3 local MCP bridge
- PATCH 4 memory-policy hardening
- pełna implementacja transportu llama.cpp
- zmiany pamięci, SQLite, `workspace_runtime`, ZIP, eksportów, raportów lub sekretów
