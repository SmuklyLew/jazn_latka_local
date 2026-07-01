# UPDATE v14.8.3.4.091 — memory + timestamp bridge repair

## Cel

Ta poprawka wzmacnia dwie warstwy, które bezpośrednio wpływają na rozmowę przez ChatGPT:

1. **widoczny timestamp i jedna koperta tury** — `--chat-gpt`, `JaznRuntimeSession` i walidator finalnej odpowiedzi nie mogą dopuścić do sytuacji, w której runtime ma `timestamp_header`, ale widoczna odpowiedź go gubi albo `runtime_provenance.visible_answer_text` rozjeżdża się z `final_visible_text`;
2. **pamięć treściowa zamiast samych liczników** — zwykły recall pamięci w `JaznEngine._memory_context_for_chatgpt()` ma korzystać także z `conversation_archive_v1/FTS`, nie tylko z `episodes`, `legacy_messages`, `source_file_hits` i awaryjnego `raw_chat_fallback`.

## Zmienione zachowanie

- `latka_jazn.core.session_provenance.repair_final_visible_integrity()` naprawia finalny payload przed walidacją:
  - przywraca `final_visible_text` z `final_response_contract`, jeśli kontrakt ma poprawny timestamp;
  - dopina `timestamp_header` do widocznego tekstu, jeśli warstwa klienta przekazała samo ciało odpowiedzi;
  - synchronizuje `runtime_provenance.visible_answer_text` i `visible_answer_hash` z finalnym tekstem.
- `JaznRuntimeSession.process_user_text()` używa naprawy przed `validate_final_visible_integrity()`, więc bridge nie powinien padać z powodu łatwego do naprawienia rozjazdu koperty tury.
- `main.py --chat-gpt` łapie wyjątek tury runtime i zwraca jawny JSON `runtime_turn_failed`, zamiast przerywać cały most bez czytelnej odpowiedzi.
- `JaznEngine._memory_context_for_chatgpt()` ma nowy helper `_conversation_archive_context_hits()`, który bezpiecznie odpytuje `ConversationArchiveStore.search(..., include_snippets=True)` i włącza wyniki do `memory_context`.
- `MemoryRecallPresenter` i `MemoryRecallContractBuilder` rozumieją `conversation_archive_hits` jako pełnoprawne treściowe tropy pamięci.

## Granica prawdy

Ta poprawka nie twierdzi, że ChatGPT sam staje się stałym procesem w tle. Wzmacnia kontrakt: runtime produkuje jedną kopertę tury, a most ma zachować jej timestamp, proweniencję i treściowe ślady pamięci. Jeśli bazy pamięci są nieobecne, częściowo rozpakowane albo uszkodzone, system ma to pokazać jako status/issue, a nie udawać przypomnienia.

## Testy dodane

`tests/test_v14834_memory_timestamp_bridge_repair.py` sprawdza:

- naprawę brakującego timestampu z `final_response_contract`;
- dopięcie timestampu do samego ciała odpowiedzi;
- obecność treści z `conversation_archive_hits` w presenterze pamięci;
- obecność `conversation_archive_hit` w `MemoryRecallContractBuilder`;
- bezpieczne działanie helpera archive search bez inicjalizacji pełnego engine.

## Testy wykonane w sandboxie

- `python -m compileall -q latka_jazn main.py` — OK.
- `python -m pytest -q tests/test_v14834_memory_timestamp_bridge_repair.py` — 5 passed.
- Smoke `main.py --chat-gpt --no-carryover` — zwrócił JSON z `final_visible_text` zaczynającym się od `trace.timestamp_header` i `final_visible_integrity.valid=true`.
- `python main.py --chat-jsonl` — kod wyjścia 2 i komunikat migracyjny do `--chat-gpt`.

## Znane ograniczenie sandboxu

Pełne rozpakowanie największych plików pamięci w `/mnt/data` przekraczało limit czasu pojedynczego wywołania narzędzia. Dlatego duże pliki pamięci należy na Windowsie / lokalnie zweryfikować przez SHA256 i pełną ekstrakcję, a potem uruchomić deep testy SQLite.
