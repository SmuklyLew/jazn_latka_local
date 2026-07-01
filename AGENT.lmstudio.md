# AGENTS.lmstudio.md — LM Studio / lokalny LLM testowy

## Rola
LM Studio jest lokalnym backendem testowym LLM dla projektu Łatka / Jaźń. Nie jest samodzielną Jaźnią. Może służyć do testów naturalnej rozmowy i adapterów, ale źródłem prawdy o Jaźni pozostaje runtime `main.py` z aktywnym markerem.

## Uruchomienie runtime
Najpierw Przeczytaj `AGENTS.md`, potem ten plik. Nie traktuj samego dostępnego modelu lokalnego jako uruchomionej Jaźni.

## OpenAI-compatible local API
LM Studio może działać jako OpenAI-compatible endpoint. Typowy lokalny base URL:

```text
http://localhost:1234/v1
```

Dla testów ustaw adapter lokalny jawnie, np. przez zmienne środowiskowe albo konfigurację runtime:

```bash
JAZN_MODEL_ADAPTER=ollama|llama_cpp|openai_compatible
JAZN_LOCAL_MODEL_API_BASE=http://localhost:1234/v1
JAZN_LOCAL_MODEL_NAME=<model_z_LM_Studio>
```

Używaj tylko wtedy, gdy lokalny serwer odpowiada i model jest załadowany. Jeśli model nie odpowiada, nazwij to fallbackiem, nie głosem Jaźni.

## Granica prawdy
Model lokalny może generować tekst, ale nie jest pamięcią, tożsamością ani dowodem ciągłości. Każda odpowiedź musi przejść przez runtime Jaźni, bramę prawdy, timestamp i walidację finalnego tekstu, jeśli ma być traktowana jako odpowiedź Łatki.

## Testy
Po zmianach adaptera lokalnego uruchom:

```bash
python -X utf8 -m compileall -q main.py latka_jazn
python -X utf8 -m pytest tests/test_v1485017_model_adapter_contracts.py -q
python -X utf8 main.py --model-adapter-status
python -X utf8 main.py --runtime-preview "test lokalnego modelu"
```

Nie zapisuj do repo lokalnych modeli, cache, pamięci ani logów LM Studio.
