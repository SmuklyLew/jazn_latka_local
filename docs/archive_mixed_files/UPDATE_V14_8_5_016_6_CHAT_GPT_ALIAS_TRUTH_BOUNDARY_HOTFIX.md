# UPDATE v14.8.5.016.6 — ChatGPT alias truth-boundary hotfix

## Cel

Mały patch kosmetyczno-audytowy po `v14.8.5.016.5`. Uczytelnia opis `chat_command_contract.truth_boundary` dla aliasów final-only mostu ChatGPT i dodaje regresję, żeby w JSONL nie pojawiła się zlepiona forma `--chat-gpt--final-only`.

## Zakres

- Nie zmienia routingu.
- Nie zmienia `--chat-gpt`, `--chat-gpt-final-only` ani `--chat-gpt --final-only`.
- Nie zmienia model adaptera.
- Nie zmienia polityki timestampu ani pamięci.
- Aktualizuje tylko opis kontraktu, wersję, dokumentację i test.

## Oczekiwany kontrakt

W `chat_command_contract.truth_boundary` mają istnieć osobno:

- `--chat-gpt-final-only`
- `--chat-gpt --final-only`

Nie może istnieć zlepiona postać:

- `--chat-gpt--final-only`

## Testy

Minimalny zestaw walidacji:

```powershell
python -m compileall main.py latka_jazn tests
python -m pytest `
  tests/test_v1485013_chat_command_bridge_contract.py `
  tests/test_v14850164_chat_gpt_final_only_cli.py `
  tests/test_v14850165_conversation_decision_body_consistency.py `
  tests/test_v1485015_runtime_access_contract.py `
  -q
```

Smoke:

```powershell
python main.py --active-cache-status
python main.py --model-adapter-status
"Działasz?" | py main.py --chat-gpt
"Działasz?" | py main.py --chat-gpt-final-only
```

## Kryterium akceptacji

- `runtime_version=v14.8.5.016.6`
- `cache_miss_reasons=[]`
- `--chat-gpt-final-only` działa jak wcześniej
- `--chat-gpt --final-only` działa jak wcześniej
- pełny JSONL zawiera czytelny opis aliasów bez `--chat-gpt--final-only`
