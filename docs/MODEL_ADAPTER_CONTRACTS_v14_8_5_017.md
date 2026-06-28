# Model adapter contracts — v14.8.5.017

## Granica odpowiedzialności

Runtime Jaźni jest właścicielem tożsamości, pamięci, routingu, stanu, polityki odpowiedzi i walidacji. Model adapter jest wyłącznie backendem generowania języka na podstawie kontekstu przekazanego przez runtime. Wybranie providera nie zmienia tożsamości Łatki i nie stanowi dowodu pamięci ani ciągłości procesu.

Każdy aktywny adapter raportuje: `adapter_id`, `provider`, `kind`, `available`, `model_name`, `endpoint`, `can_generate_model_guided_speech`, `failure_reason`, `requires_api_key`, `availability_basis` i `truth_boundary`.

`available` oznacza kompletność konfiguracji potrzebnej do wywołania adaptera. Nie jest live probe endpointu. Stan sieci i odpowiedź providera są raportowane dopiero przez realne wywołanie.

## Null adapter

Domyślny `null_model_adapter` jest prawdomównym fallbackiem offline. Jest dostępny bez modelu i bez klucza API, lecz `can_generate_model_guided_speech=false`. Zwraca pusty tekst oraz `requires_external_model_execution` zamiast udawać model.

Zwykły runtime, `--chat`, `--chat-gpt`, `--runtime-preview`, testy null adaptera i `--model-adapter-status` nie wymagają `OPENAI_API_KEY`.

## OpenAI Responses API

Istniejący `openai_responses_adapter` pozostaje backendem opcjonalnym, wybieranym jawnie przez `JAZN_MODEL_ADAPTER=openai` albo komendę `--chat-open-ai`.

Szkielet konfiguracji:

```text
JAZN_MODEL_ADAPTER=openai
JAZN_MODEL_NAME=<model>
JAZN_MODEL_API_BASE=https://api.openai.com/v1
OPENAI_API_KEY=<sekret tylko w środowisku>
```

Brak klucza daje `available=false`, `can_generate_model_guided_speech=false` i `failure_reason=openai_api_key_missing`. Klucz jest wymagany wyłącznie dla jawnego użycia backendu OpenAI; status nigdy nie ujawnia jego wartości.

## Ollama

Istniejący `local_llm_adapter` obsługuje lokalny endpoint Ollama `/api/generate`.

```text
JAZN_MODEL_ADAPTER=ollama
JAZN_LOCAL_MODEL_NAME=<lokalny-model>
JAZN_LOCAL_MODEL_API_BASE=http://127.0.0.1:11434
```

Brak nazwy modelu daje `available=false`. Samo ustawienie konfiguracji nie dowodzi, że lokalny serwer odpowiada.

## llama.cpp

W v14.8.5.017 llama.cpp jest wyłącznie szkieletem kontraktu dla lokalnego endpointu OpenAI-compatible:

```text
JAZN_MODEL_ADAPTER=llama_cpp
JAZN_LLAMA_CPP_MODEL_NAME=<lokalny-model>
JAZN_LLAMA_CPP_API_BASE=http://127.0.0.1:8080/v1
```

Factory zwraca adapter `contract_only_not_implemented`, który nie wykonuje HTTP i nie generuje tekstu. Pełna implementacja transportu llama.cpp wymaga osobnego patcha i testów; nie należy jej dopisywać w PATCH 2.
