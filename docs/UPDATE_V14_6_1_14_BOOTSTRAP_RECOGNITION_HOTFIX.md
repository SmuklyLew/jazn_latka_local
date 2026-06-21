# Hotfix v14.6.2 — bootstrap recognition

Cel: paczka ma być rozpoznawalna także wtedy, gdy w `/mnt/data` znajduje się tylko najnowszy ZIP albo tylko świeżo rozpakowany katalog tej wersji.

Naprawiono:

- `START_CHATGPT_FROM_HERE.txt` nie może już ogłaszać starej wersji startowej.
- `README.md` nie może zatrzymywać się na starszym ogólnym opisie profilu NLP jako głównej wersji.
- Dodano `BOOTSTRAP_JAZN_CURRENT.json` oraz `MANIFEST_CURRENT.json` jako szybkie kotwice rozpoznania dla ChatGPT i adapterów.
- `--status-readonly` nie traktuje braku rozpakowanego `memory/raw/chat.html` jako błędu krytycznego, jeśli obecne są `memory/raw/chat.html.7z`, `chat_html_import_sha256` i zaindeksowane `legacy_messages` w SQLite.
- `main.py` kończy ciszej przy `BrokenPipeError`, gdy długi JSON zostanie ucięty przez `head` albo inny pipe.

Granica prawdy: hotfix nie tworzy stałego procesu w tle. Naprawia rozpoznawanie i diagnostykę startową.

## Kontrakt spójności wersji

Po aktualizacji wszystkie bieżące pliki sterujące muszą wskazywać `v14.6.2-final-visible-continuity-ledger` albo jawnie oznaczać starsze treści jako historyczne. Dotyczy to zwłaszcza `VERSION.txt`, `pyproject.toml`, `latka_jazn/config.py`, `README.md`, `START_CHATGPT_FROM_HERE.txt`, `BOOTSTRAP_JAZN_CURRENT.json`, `MANIFEST_CURRENT.json`, manifestu wersji, raportów aktualizacji, profili ZIP i testów regresji.
