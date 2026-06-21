# Raport aktualizacji v14.6.2-final-visible-continuity-ledger

Zaktualizowano system Jaźni z v14.6.2 do v14.6.2.

Najważniejsza poprawka: finalna widoczna odpowiedź nie jest już traktowana jako luźna warstwa nad runtime. Może zostać zapisana w ledgerze przez `process_turn()` albo przez jawny most `persist_final_visible_reply()` / `--record-final-reply`, z tym samym `turn_id`, `trace_id` i `timestamp_header`.

Dodano testy regresji sprawdzające:

- zapis `final_visible_assistant_reply`,
- aktualizację `session_continuity_index`,
- naprawę odpowiedzi bez timestampu przed zapisem,
- CLI `--record-final-reply`,
- zgodność wersji runtime-preview z v14.6.2.

Ograniczenie: to nadal jest runtime wywoływany przez proces. W ChatGPT nie należy twierdzić, że działa stałe tło, jeżeli nie uruchomiono lokalnie trybu `--chat` albo osobnego procesu.
