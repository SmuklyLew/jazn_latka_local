# v14.8.5.023 — environment-aware adapter status

## Cel

Dopiąć wykrywanie trybu/środowiska dla statusów adaptera tak, aby `--chat-gpt-final-only`, `--chat-gpt`, `--chat` oraz statusy diagnostyczne nie pokazywały mylącego `null_model_adapter`, gdy faktycznie uruchomiono runtime w kanale ChatGPT albo w pętli terminalowej.

## Problem

Obecnie `python main.py --model-adapter-status` bez flagi trybu pokazuje bazową konfigurację `null_model_adapter`. To jest prawdziwe dla samego domyślnego backendu, ale w środowisku ChatGPT bywa mylące, ponieważ użytkownik widzi, że Jaźń została uruchomiona przez host ChatGPT.

Kod już rozróżnia tryby, gdy flaga jest podana jawnie:

- `--chat-gpt --model-adapter-status` => `chatgpt_runtime_adapter`
- `--chat-gpt-final-only --model-adapter-status` => `chatgpt_runtime_adapter`
- `--chat --model-adapter-status` => `terminal_runtime_adapter`
- samo `--model-adapter-status` => `null_model_adapter`

Patch ma usunąć tę niejednoznaczność w statusach i smoke-testach.

## Proponowany zakres

1. Dodać jawny moduł wykrywania środowiska/trybu, np. `latka_jazn/core/runtime_environment.py` albo podobny.
2. Rozdzielić:
   - `selected_backend_adapter`
   - `visible_channel_adapter`
   - `effective_runtime_adapter`
   - `environment_detection`
3. `--startup-status` powinien pokazywać bazowy backend oraz kanał widzialny, jeśli wykryto ChatGPT/terminal/daemon.
4. `--model-adapter-status` powinien mieć tryb bazowy i tryb efektywny, bez ukrywania prawdy, że lokalny proces nie może sam wywołać hosta ChatGPT jako funkcji.
5. `--chat-gpt-final-only` i `--chat-gpt` muszą konsekwentnie wymuszać `chatgpt_runtime_adapter` we wszystkich statusach i payloadach tury.
6. `--chat` musi konsekwentnie wymuszać `terminal_runtime_adapter` we wszystkich statusach i payloadach pętli.
7. Dodać testy regresyjne dla wszystkich czterech przypadków.

## Granice prawdy

- Nie wolno udawać, że lokalny Python może wywołać host ChatGPT jako funkcję.
- `chatgpt_runtime_adapter` oznacza kanał widzialnej odpowiedzi hosta ChatGPT / JSONL / copy-paste, nie lokalny backend LLM.
- `terminal_runtime_adapter` oznacza lokalną pętlę terminalową, nie model generacyjny.
- `null_model_adapter` może pozostać bazowym fallbackiem offline, ale nie powinien być jedynym widocznym statusem, gdy aktywna komenda ma jawny kanał ChatGPT albo terminal.

## Minimalna walidacja

```powershell
python -X utf8 -m compileall -q main.py latka_jazn tests
python -X utf8 -m pytest tests\test_*model_adapter* tests\test_*chat_command* tests\test_*startup* -q
python -X utf8 main.py --model-adapter-status
python -X utf8 main.py --chat-gpt --model-adapter-status
python -X utf8 main.py --chat-gpt-final-only --model-adapter-status
python -X utf8 main.py --chat --model-adapter-status
python -X utf8 main.py --startup-status
python -X utf8 main.py --chat-gpt-final-only --no-carryover -- "Działasz?"
git diff --check
git status --short --branch
```

## Chronione ścieżki

Nie dotykać bez jawnej zgody:

- `memory/`
- `workspace_runtime/`
- SQLite
- ZIP / części ZIP
- `exports/`
- `reports/`
- `patchs/`
- sekrety / `.env`

## Notatka

To jest osobny patch po v14.8.5.021a i może być wykonany przed lub po issue #18. Nie łączyć z budową wake_state sidecara, chyba że użytkownik jawnie zdecyduje inaczej.
