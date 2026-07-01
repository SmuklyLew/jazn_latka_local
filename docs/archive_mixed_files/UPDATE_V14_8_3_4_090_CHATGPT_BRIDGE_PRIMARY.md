# v14.8.3.4.090 — ChatGPT bridge primary

## Cel

Ta aktualizacja usuwa aktywne użycie `--chat-jsonl` jako osobnej flagi CLI i ustanawia `--chat-gpt` jako główny wsadowy most między ChatGPT a runtime Jaźni.

## Zmiany funkcjonalne

- `python main.py --chat-gpt --session-id <id>` jest głównym trybem JSONL/mostu ChatGPT.
- Preferowane pole wejścia to `message`.
- Awaryjnie akceptowane są `text`, `user_text`, `content`, `prompt`.
- Obsługiwany jest także format `messages[].content` znany z mostów czatowych.
- Zwykła linia tekstu bez JSON nadal działa jako jedna wiadomość użytkownika.
- Pusta wiadomość nie jest przekazywana do runtime; most zwraca kontrolowany JSON błędu.
- Uszkodzony JSON rozpoczynający się od `{` albo `[` nie jest traktowany jako zwykły tekst; most zwraca kontrolowany JSON błędu.
- JSON niebędący obiektem, np. lista, zwraca kontrolowany JSON błędu.
- Każda poprawna odpowiedź zawiera blok `chatgpt_bridge` z protokołem, polem wejścia, klientem, lifecycle i informacją o usuniętej fladze.

## Granica prawdy

`--chat-gpt` nie oznacza stałego procesu w tle. To nadal tryb wsadowy/stdin: jedna linia wejścia daje jedną linię JSON wyjścia, a proces kończy się po EOF albo `/exit`. Do żywej lokalnej rozmowy właściwy pozostaje `--chat`.

## Migracja

Stare:

```bash
python main.py --chat-jsonl --session-id <id>
```

Nowe:

```bash
python main.py --chat-gpt --session-id <id>
```

Stara flaga `--chat-jsonl` pokazuje komunikat migracyjny i kończy się kodem `2`.

## Testy minimalne

```bash
python -m compileall -q latka_jazn main.py
python -m pytest -q tests/test_v14832_unified_chat_session_core.py tests/test_v14834090_chat_gpt_final_visible_rendering.py tests/test_v148265_eof_chat_lifecycle_contract.py
python main.py --chat-gpt --session-id local-check
```

## Notatka manifestu

Po zastosowaniu patcha w pełnym aktywnym folderze należy odświeżyć `MANIFEST_CURRENT.json`, `SHA256SUMS` i raport audytu manifestu narzędziem aktualnym dla layoutu `conversation_archive_v1+fts_v1+staging_v1+runtime_write_v1`.
