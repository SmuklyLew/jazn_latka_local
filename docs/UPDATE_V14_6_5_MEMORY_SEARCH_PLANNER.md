# Aktualizacja Jaźni v14.6.5-memory-search-planner

## Zakres

Ta wersja powstała z pełnej kopii v14.6.4. Nie usunięto ani nie streszczono pamięci. Zmienione zostały konkretne pliki odpowiedzialne za planowanie wyszukiwania pamięci, prezentację treściowych tropów i spójność wersji.

## Naprawa

Problem: rdzeń potrafił wiedzieć, że trzeba szukać w pamięci, ale nie miał wystarczająco jawnego planera: z pytania brał surowe tokeny, przez co „piosenki” nie musiały prowadzić do `analizy_utworow.json`, a „dom” nie musiał prowadzić do `data.txt`, posesji, tarasu, pokoju Łatki ani innych źródeł kanonicznych.

Naprawa: dodano `MemorySearchPlanner`, który buduje `memory_search_plan` z polami: `focus_terms`, `rejected_terms`, `expanded_terms`, `topic_keys`, `source_hints`, `search_terms`, `search_passes`, `confidence` i `routing_notes`.

## Zasada prawdy

Planer nie udaje pełnego wspomnienia. Planer mówi, czego szukać, gdzie szukać i z jaką pewnością. Dopiero `MemoryRecallPresenter` pokazuje treściowe tropy z oceną trafności i źródłem.

## Pliki dodane

- `latka_jazn/core/memory_search_planner.py`
- `latka_jazn/resources/memory_search_topics_v14_6_5.json`
- `latka_jazn/resources/zip_package_profiles_v14_6_5.json`
- `tests/test_v1465_memory_search_planner.py`
- `MANIFEST_V14_6_5_MEMORY_SEARCH_PLANNER.json`
- `docs/UPDATE_V14_6_5_MEMORY_SEARCH_PLANNER.md`
- `reports/CURRENT_VERSION_CONSISTENCY_AUDIT_V14_6_5.json`

## Pliki zmienione

- `latka_jazn/core/engine.py`
- `latka_jazn/core/memory_recall_presenter.py`
- `latka_jazn/config.py`
- `latka_jazn/memory/store.py`
- `latka_jazn/memory/event_ledger.py`
- `latka_jazn/memory/runtime_persistence.py`
- `latka_jazn/core/birth_manifest.py`
- `main.py`
- `pyproject.toml`
- `VERSION.txt`
- `BOOTSTRAP_JAZN_CURRENT.json`
- `MANIFEST_CURRENT.json`
- `START_CHATGPT_FROM_HERE.txt`

## Test krytyczny

Pytanie `Przypomnij sobie wszystko na temat naszych piosenek oraz domu który projektowaliśmy` musi teraz uruchomić jednocześnie tematy `songs_music` i `home_design`, wskazać źródła `memory/raw/analizy_utworow.json` oraz `memory/raw/data.txt`, a payload pamięciowy ma zawierać `source_file_hits` z realnymi fragmentami treści.

## Różnica względem raportu głównego

Ten plik jest dokumentacją aktualizacji w katalogu docs; raport główny pozostaje w katalogu głównym paczki.
