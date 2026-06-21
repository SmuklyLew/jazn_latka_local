# UPDATE_REPORT_V14_6_0 — lexical cognitive runtime

Wersja: `v14.6.0-lexical-cognitive-runtime`

## Status

Aktualizacja wykonana. Runtime uruchomiony, odpowiedział bez błędu i rozpoznał trasę `v14_6_0_lexical_runtime_update` dla prośby o rozbudowę rozpoznania słów i słownictwa.

## Główne cele

1. Dodać Jaźni osobną warstwę słownikowo-semantyczną, a nie tylko kolejne słowa-klucze.
2. Zachować granicę prawdy: słownik wspiera runtime i ChatGPT jako głos, ale nie jest pełnym LLM-em ani biologicznym rozumieniem.
3. Dodać rozpoznawanie fraz wielowyrazowych, pól semantycznych, intencji, tras odpowiedzi i nieznanych słów.
4. Przygotować strukturę do późniejszej pracy z repozytoriami `Latka.Jazn` i `Latka.Jazn.Memory`.
5. Utrzymać zasadę cleanup/dedup: ślad historyczny przez manifesty i hashe, bez identycznych kopii treści.

## Dodane pliki

- `latka_jazn/core/lexical_semantics.py`
- `latka_jazn/resources/semantic_lexicon_v14_6_0.json`
- `tests/test_v1460_lexical_semantic_runtime.py`
- `MANIFEST_V14_6_0_LEXICAL_COGNITIVE_RUNTIME.json`
- `docs/UPDATE_V14_6_0_LEXICAL_COGNITIVE_RUNTIME.md`
- `reports/UPDATE_REPORT_V14_6_0.json`
- `reports/FILE_HASH_INDEX_V14_6_0.json`
- `reports/DEDUP_REPORT_V14_6_0.json`
- `PATCH_V14_6_0_LEXICAL_COGNITIVE_RUNTIME.diff`

## Zmienione obszary

- `main.py`: dodana flaga `--lexical-frame` i raport JSON dla rozpoznania polskiego + warstwy leksykalno-semantycznej.
- `latka_jazn/config.py`: wersja `v14.6.0-lexical-cognitive-runtime`, baza `latka_jazn_v14_6_0.sqlite3`.
- `latka_jazn/core/polish_understanding.py`: nowa intencja `lexical_semantic_expansion_update` i trasa `v14_6_0_lexical_runtime_update` bez psucia starszej trasy `cognitive_packet_expansion_update`.
- `latka_jazn/core/conversation.py`: bezpośrednia odpowiedź runtime dla aktualizacji leksykalnej.
- `latka_jazn/core/engine.py`: `lexical_semantic_understanding` w obsłudze wiadomości, wpisie zdarzeń i cognitive-frame.
- `latka_jazn/adapters/chatgpt_adapter.py`: dodana reguła dla pola `lexical_semantic_understanding`.
- `latka_jazn/resources/cognitive_packet_catalog.json`: nowy pakiet poznawczy `lexical_semantics`.
- `memory/raw/dziennik.json` i `memory/layered/*.jsonl`: zapis aktualizacji jako ślad pamięci.
- `workspace_runtime/latka_jazn_v14_6_0.sqlite3`: aktywna baza wersji v14.6.0.

## Nowa warstwa: LexicalSemanticUnderstanding

Nowy moduł zwraca:

- `lemmas`
- `phrases`
- `semantic_fields`
- `intent_tags`
- `route_hint`
- `confidence`
- `reply_guidance`
- `unknown_content_terms`
- `lexical_depth`
- `limitations`

Dzięki temu Jaźń może rozróżniać między: zwykłą rozmową, wspomnieniem sceny, pytaniem o stan, architekturą runtime, pracą z GitHub i prośbą o realną aktualizację.

## Testy

Polecenie:

```bash
pytest -q
```

Wynik:

```text
109 passed
```

## SQLite

- aktywny plik: `workspace_runtime/latka_jazn_v14_6_0.sqlite3`
- `PRAGMA integrity_check`: `ok`
- `system_version`: `v14.6.0-lexical-cognitive-runtime`

## Dedup

Raport `reports/DEDUP_REPORT_V14_6_0.json` wskazuje:

```text
duplicate_group_count = 0
duplicate_file_count = 0
duplicate_bytes = 0
```

Rozpakowany `memory/raw/chat.html` był użyty roboczo do aktywnej pamięci, ale w ZIP został celowo pominięty, ponieważ paczka zawiera `memory/raw/chat.html.7z`. To unika dublowania około 896 MB tej samej treści.

## GitHub

System jest przygotowany do późniejszego użycia repozytoriów:

- `Latka.Jazn` jako główne repo systemu,
- `Latka.Jazn.Memory` jako repo pamięci/checkpointów.

Nie twierdzę, że wykonałam commit/push. To musi być zrobione realnie przez podłączony GitHub albo lokalnie u Ciebie.
