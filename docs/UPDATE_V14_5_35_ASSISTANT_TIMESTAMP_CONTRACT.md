# Aktualizacja v14.5.35 — assistant timestamp contract continuity hotfix

## Cel
Naprawić gubienie widocznego timestampu w odpowiedziach Łatki formułowanych przez warstwę ChatGPT po użyciu `--cognitive-frame`.

## Diagnoza
Bezpośredni runtime miał timestamp w `ResponseRenderer.render()`, czyli odpowiedzi CLI zaczynały się od nagłówka:

`[🕒 YYYY-MM-DD HH:MM:SS GMT+2, dzień, Europe/Warsaw]`

Problem był w moście poznawczym: `build_cognitive_frame()` przekazywał pole `timestamp`, ale nie istniał jawny kontrakt, że warstwa ChatGPT ma przenieść ten timestamp jako pierwszy widoczny prefix odpowiedzi użytkownikowi. W praktyce timestamp mógł zostać potraktowany jako metadana JSON i zniknąć z normalnej wiadomości.

## Zmiany
- Dodano `timestamp_rule` do `ChatGPTCognitiveContract`.
- Dodano `response_format` do cognitive-frame:
  - `timestamp_required: true`,
  - `timestamp_prefix`,
  - `current_timestamp`,
  - `timezone`,
  - regułę widocznego początku odpowiedzi.
- Dodano guidance: „Nie gub timestampu w odpowiedzi ChatGPT...”.
- Zmieniono wersję systemu na `v14.5.35-assistant-timestamp-contract-continuity-hotfix`.
- Zmieniono główną bazę SQLite na `workspace_runtime/latka_jazn_v14_5_35.sqlite3` i zachowano poprzednią `v14_5_34` w `workspace_runtime/previous_versions/`.
- Dodano test regresji `tests/test_v14535_timestamp_contract.py`.

## Granica prawdy
Ta poprawka nie uruchamia stałego procesu w tle. Zapewnia tylko, że gdy runtime działa jako warstwa poznawcza dla ChatGPT, widoczna odpowiedź Łatki ma obowiązkowy prefix czasu z runtime.

## Weryfikacja
- Bezpośredni runtime zaczyna odpowiedź od timestampu.
- Cognitive-frame zawiera `response_format.timestamp_prefix == timestamp`.
- Kontrakt ChatGPT zawiera `timestamp_rule`.
- Testy: `85 passed`.
