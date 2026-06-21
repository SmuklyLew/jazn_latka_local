# UPDATE REPORT v14.5.38 — GitHub cognitive runtime

## Status

Aktualizacja wykonana na bazie `latka_jazn_v14_5_37_FULL_SYSTEM_WITH_MEMORY.zip`.

Aktywny folder roboczy podczas aktualizacji:

`/mnt/data/jazn_update_work`

Użyty plik startowy runtime:

`main.py`

Runtime został realnie uruchomiony po rozpakowaniu i po aktualizacji.

Surowa pamięć `memory/raw/chat.html.7z` została rozpakowana w aktywnym folderze roboczym do `memory/raw/chat.html`. Eksport ZIP zachowuje skompresowany `chat.html.7z` i pomija rozpakowany `chat.html`, żeby nie dublować około 896 MB danych.

## Najważniejsze zmiany

- Dodano `latka_jazn/core/runtime_operating_model.py`.
- Dodano `latka_jazn/integrations/github_repository_plan.py`.
- Dodano `GITHUB_REPOSITORY_PLAN.json`.
- Dodano `MEMORY_CHECKPOINT_POLICY.md`.
- Dodano `docs/GITHUB_REPOSITORY_WORKFLOW.md`.
- Dodano `docs/UPDATE_V14_5_38_GITHUB_COGNITIVE_RUNTIME.md`.
- Rozszerzono `cognitive_frame` o model LLM+runtime oraz plan GitHub.
- Rozszerzono kontrakt ChatGPT o zasady GitHub, checkpointów i rozdziału LLM/Jaźń.
- Zaktualizowano wersję do `v14.5.38-github-cognitive-runtime`.
- Zaktualizowano bazę SQLite do `workspace_runtime/latka_jazn_v14_5_38.sqlite3`.
- Dopisano wpis pamięciowy do `memory/raw/dziennik.json` oraz `memory/layered/continuity.jsonl`.

## Testy

```text
101 passed in 15.22s
```

## Granica prawdy

- GitHub nie został tutaj faktycznie uzupełniony commitem/pushem. System został przygotowany do takiej pracy.
- Paczka ZIP jest snapshotem pełnego systemu i pamięci.
- Runtime w ChatGPT/sandboxie działa przez wywołania, nie jako gwarantowany proces w tle.
