# v14.8.5.016.4 — chat-gpt final-only aliases supplement

## Cel

Ten suplement doprecyzowuje UX patcha `v14.8.5.016.4`.
Pierwsza wersja wymagała formy:

```powershell
py main.py --chat-gpt --chat-gpt-final-only
```

Dla człowieka czytelniejsze są krótsze formy bez zmiany routingu ani protokołu JSONL.

## Nowe formy użycia

Samodzielny skrót:

```powershell
py main.py --chat-gpt-final-only
```

Jawny most z krótkim aliasem:

```powershell
py main.py --chat-gpt --final-only
```

Forma kompatybilna z pierwszą wersją patcha nadal działa:

```powershell
py main.py --chat-gpt --chat-gpt-final-only
```

Domyślny most JSONL pozostaje bez zmian:

```powershell
py main.py --chat-gpt
```

## Granica zmiany

- brak zmian w routingu,
- brak zmian w sesjach, pamięci, walidatorach i runtime truth gate,
- `--chat-gpt-final-only` tylko ustawia tryb mostu i output `final_visible_text`,
- `--final-only` jest aliasem wymagającym `--chat-gpt`,
- `--final-only` bez `--chat-gpt` kończy parser error / exit code 2.

## Walidacja

```powershell
python -m compileall main.py latka_jazn tests
python -m pytest `
  tests/test_v1485013_chat_command_bridge_contract.py `
  tests/test_v14850164_chat_gpt_final_only_cli.py `
  tests/test_v1485015_runtime_access_contract.py `
  -q

"Działasz?" | py main.py --chat-gpt-final-only
"Działasz?" | py main.py --chat-gpt --final-only
"Działasz?" | py main.py --chat-gpt
```
