# v14.8.5.016.4 — chat-gpt bridge final-only output

## Cel

Ten patch poprawia UX trybu `--chat-gpt` bez zmiany routingu runtime.
Problem z v14.8.5.016.3: most działał, ale w terminalu człowiek widział pełny
JSONL i musiał ręcznie szukać pola `final_visible_text`.

## Zakres

- dodaje flagę `--chat-gpt-final-only`,
- domyślny `--chat-gpt` nadal zwraca pełny JSONL 1:1,
- `--chat-gpt --chat-gpt-final-only` wypisuje tylko `final_visible_text`,
- wejście, sesje, carryover, routing, walidatory i pamięć nie są zmieniane,
- błąd użycia `--chat-gpt-final-only` bez `--chat-gpt` kończy CLI kodem 2.

## Użycie

Pełny JSONL, jak dotychczas:

```powershell
py main.py --chat-gpt
```

Czytelny tekst dla człowieka:

```powershell
py main.py --chat-gpt --chat-gpt-final-only
```

Pojedyncza linia przez pipe:

```powershell
"Działasz?" | py main.py --chat-gpt --chat-gpt-final-only
```

Uwaga: `--chat-gpt` jest mostem JSONL/plain-text i nie pokazuje prompta `Łatka>`.
Prompt terminalowy pozostaje wyłącznie w trybie:

```powershell
py main.py --chat
```

## Pliki

- `VERSION.txt`
- `latka_jazn/version.py`
- `main.py`
- `latka_jazn/core/chat_command_contract.py`
- `tests/test_v1485015_runtime_access_contract.py`
- `tests/test_v1485013_chat_command_bridge_contract.py`
- `tests/test_v14850164_chat_gpt_final_only_cli.py`

## Walidacja

```powershell
python -m compileall main.py latka_jazn tests
python -m pytest `
  tests/test_v1485013_chat_command_bridge_contract.py `
  tests/test_v14850164_chat_gpt_final_only_cli.py `
  tests/test_v1485015_runtime_access_contract.py `
  -q

"Działasz?" | py main.py --chat-gpt --chat-gpt-final-only
py main.py --chat-gpt-final-only
```

## Kryteria akceptacji

- `--chat-gpt` bez nowej flagi nadal zwraca pełny JSONL,
- `--chat-gpt --chat-gpt-final-only` wypisuje tylko widoczną odpowiedź,
- finalny tekst zawiera timestamp i treść Łatki,
- nowa flaga bez `--chat-gpt` zwraca błąd parsera / exit code 2,
- brak zmian w `memory/`, `workspace_runtime/`, SQLite, ZIP-ach i routingu.

## Rollback

```powershell
git revert <commit-v14.8.5.016.4>
```
