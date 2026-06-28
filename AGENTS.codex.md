# AGENTS.codex.md — Codex / agent kodujący

## Cel
Codex pracuje jako agent inżynierski projektu Łatka / Jaźń. Ma czytać kod, przygotowywać patch, uruchamiać testy i pilnować prawdy runtime. Nie ma udawać Łatki ani zastępować uruchomionego runtime.

## Start zadania
1. Przeczytaj `AGENTS.md`, potem ten plik.
2. Sprawdź `git status`.
3. Ustal branch/commit/tag i aktywny folder.
4. Nie używaj `docs/archive/manifest_history/**` jako aktywnego manifestu. Aktywny manifest to tylko `MANIFEST_CURRENT.json`; stan mutable to `RUNTIME_STATE.json`.
5. Nie traktuj `memory/**manifest*` ani `memory/sqlite/**/conversation_archive_manifest.sqlite3` jako aktywnych manifestów agenta; to metadane pamięci/runtime albo baza SQLite.
6. Nie modyfikuj `memory/`, `workspace_runtime/`, SQLite, sekretów ani ZIP-ów bez wyraźnej zgody.

## Runtime Jaźni
Przed twierdzeniem, że Jaźń działa, sprawdź marker i status:

```bash
python -X utf8 main.py --active-cache-status
python -X utf8 main.py --startup-status
python -X utf8 main.py --model-adapter-status
python -X utf8 main.py --daemon-status
```

Do jednej tury używaj:

```bash
python -X utf8 main.py --chat-gpt-final-only -- "wiadomość"
```

Do pełnej diagnostyki:

```bash
python -X utf8 main.py --runtime-preview "wiadomość"
python -X utf8 main.py --dev-preview "wiadomość"
```

## Patch workflow
Przed zmianami zrób bezpieczny punkt odniesienia: branch/tag albo zanotowany commit. Dla patcha używaj:

```bash
git apply --check patch.patch
git apply patch.patch
```

Po zmianach uruchom minimalnie:

```bash
python -X utf8 -m compileall -q main.py latka_jazn tools
python -X utf8 -m pytest <właściwe testy> -q
python -X utf8 main.py --chat-gpt-final-only -- "smoke test"
python -X utf8 main.py --active-cache-status
python -X utf8 main.py --model-adapter-status
```

Jeśli zmieniono manifesty, uruchom:

```bash
python -X utf8 tools/refresh_current_manifest.py
```

i sprawdź, że aktywne ścieżki nie wskazują na dawne manifesty poza `docs/archive/manifest_history/**`.

## Archiwa i manifesty
Dawne manifesty muszą być przenoszone do `docs/archive/manifest_history/**` z zachowaniem treści i mapy w `docs/archive/manifest_history/INDEX.json`. Nie zostawiaj dawnych manifestów w aktywnych katalogach, bo agenty mogą pomylić historię z aktualnym runtime.

Wyjątek techniczny: pliki w `memory/**` z `manifest` w nazwie nie są manifestami sterującymi agentami. To metadane pamięci, importu albo bazy SQLite; nie wolno ich przenosić w ramach porządkowania manifestów bez osobnej migracji pamięci i testów integralności SQLite.

## Commit
Do commita dodawaj tylko pliki powiązane z zadaniem. Nie dodawaj przypadkowo cache, pamięci, runtime, SQLite, części ZIP ani eksportów. Po commicie pokaż `git status`, `git log --oneline -1`, testy i ograniczenia.
