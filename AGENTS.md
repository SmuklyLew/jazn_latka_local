# AGENTS.md — router agentów Łatka / Jaźń

Ten plik jest wejściowym routerem dla narzędzi i agentów pracujących w repozytorium. Nie jest manifestem runtime ani pamięcią Jaźni.

## Aktywne źródła

- `MANIFEST_CURRENT.json` — jedyny aktywny manifest statycznego snapshotu projektu.
- `RUNTIME_STATE.json` — snapshot plików mutable runtime/private-memory; nie jest manifestem paczki.
- `workspace_runtime/JAZN_ACTIVE_RUNTIME.json` — marker aktywnego runtime; nie jest manifestem.
- `memory/` — dane pamięci/runtime; pliki z `manifest` w nazwie są metadanymi pamięci albo bazami SQLite, nie instrukcjami agenta ani aktywnymi manifestami projektu.
- `docs/archive/manifest_history/` — archiwum dawnych manifestów; czytaj tylko przy audycie historii/migracji.

## Wybór instrukcji agenta

- ChatGPT/openai.com: użyj `AGENTS.chatgpt.md`.
- Codex / agent kodujący: użyj `AGENTS.codex.md`.
- LM Studio / lokalne testy LLM i rozmowy: użyj `AGENTS.lmstudio.md`.

## Zasada prawdy

Nie udawaj uruchomionej Jaźni. Aktywną Łatkę wolno potwierdzić dopiero po realnym markerze, pełnym folderze, `main.py`, statusie daemonu albo poprawnym `final_visible_text` z runtime.

## Zakaz mylenia archiwów

Pliki w `docs/archive/**`, `memory/**`, `workspace_runtime/**`, `patchs/**`, `reports/**` i paczki ZIP są historią, pamięcią, runtime albo eksportem. Nie wybieraj ich jako aktywnego manifestu ani aktywnej instrukcji, jeśli użytkownik nie prosi o audyt historii.
