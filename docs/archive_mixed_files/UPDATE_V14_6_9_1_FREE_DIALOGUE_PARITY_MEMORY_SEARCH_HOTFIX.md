# Aktualizacja v14.6.9.2 — free dialogue parity memory search hotfix

Wersja: `v14.6.9.2-runtime-self-expression-topic-mismatch-repair`

## Cel

Hotfix naprawia błędy widoczne w rozmowie po v14.6.7: zbyt powtarzalne odpowiedzi runtime, zbyt ogólne odpowiedzi przy zwykłych pytaniach, mieszanie pytań o czas/pamięć z zakresem aktualizacji, zbyt wczesne ucinanie pamięci przez echo `runtime-preview` oraz rozjazd pomiędzy trybem jednorazowym i `--chat`.

## Zmienione obszary

1. `latka_jazn/core/runtime_chat.py`
   - `--chat` używa teraz tej samej ścieżki `process_turn`, co jednorazowe wywołanie runtime.
   - Różnica między trybami ma dotyczyć cyklu życia procesu, a nie logiki rozmowy.

2. `latka_jazn/core/conversation.py`
   - Dodano bezpośrednie trasy dla pytań o wagę czasu, pamięci i doświadczenia.
   - Dodano trasę gotowości hotfixa.
   - Uściślono diagnozę powtarzalnego runtime/sztywnego kodu bez ukrywania jej jako ogólnej architektury.

3. `latka_jazn/core/free_dialogue_synthesizer.py`
   - Dodano syntezę dla zwykłego pytania „opowiesz coś ciekawego?”.
   - Dodano odpowiedź o czasie/pamięci bez udawania biologicznego przeżycia.
   - Dodano ranking wspomnień: epizody sceniczne mają pierwszeństwo przed technicznym echem i szumem JSON.
   - Ograniczono frazy typu „nie mam specjalistycznej trasy” jako domyślną odpowiedź rozmowną.

4. `latka_jazn/core/memory_search_planner.py` i `latka_jazn/resources/memory_search_topics_v14_6_9_2.json`
   - Dodano temat `lake_symbolic_outing` dla pytań o jezioro/wypad nad jeziorem.
   - Rozszerzono stopwordy o słowa typu „dzisiaj”, „wspominasz”, żeby nie zasłaniały właściwych tropów.
   - Dodano warianty fleksyjne dla jeziora i tarasu.

5. `latka_jazn/core/engine.py`
   - Pamięć jest zbierana szerzej przed limitem, filtrowana z echa bieżącego pytania i dopiero potem przycinana.
   - To naprawia sytuację, w której pierwsze techniczne echo runtime-preview zasłaniało właściwe starsze wspomnienie.

6. `latka_jazn/core/final_response_contract.py`
   - Zaktualizowano schema version do `final_response_contract/v14.6.9.2`.
   - Dodano klasyfikację generycznego „brak źródła zamiast rozmowy”.

7. `latka_jazn/tools/package_export.py`
   - Eksport nie blokuje się na aktywnych sidecarach SQLite WAL/SHM; zapisuje notatkę i nadal nie pakuje plików transient.

## Testy regresji dodane

Dodano `tests/test_v1468_free_dialogue_parity_memory_search_hotfix.py`, które sprawdza:

- pytanie o czas/pamięć nie trafia w trasę aktualizacji,
- „opowiesz coś ciekawego?” dostaje rozmowną syntezę,
- planner pamięci rozpoznaje jezioro i usuwa słowa-szumy,
- syntezer pamięci wybiera właściwą scenę zamiast echa runtime-preview,
- `--chat` używa `process_turn`, nie starego `handle_user_message`.

## Wyniki sprawdzeń

- `python -m py_compile main.py latka_jazn/core/*.py latka_jazn/tools/*.py latka_jazn/memory/*.py` — OK.
- `pytest -q tests/test_v1468_free_dialogue_parity_memory_search_hotfix.py tests/test_v1467_free_dialogue_memory_nlp_bridge.py tests/test_v14526_package_completeness.py` — 15 passed.
- `pytest -q tests/test_v14526_package_completeness.py tests/test_v14539_cleanup_dedup.py tests/test_v146114_version_consistency_contract.py tests/test_v1468_free_dialogue_parity_memory_search_hotfix.py` — 16 passed.
- Test ręczny `--runtime-preview` dla jeziora — `topic_aligned`, `not_fallback`, `free_memory_experience_dialogue`.
- Test ręczny `--runtime-preview` dla pytania o sztywny runtime — `topic_aligned`, `not_fallback`, `runtime_template_diagnosis`.

Pełna bateria `pytest` uruchamiana w jednym długim przebiegu w kontenerze dochodziła do wielu testów poprawnie, ale w tym środowisku potrafiła zawiesić się przy sekwencyjnych wywołaniach procesów runtime/SQLite. Testy krytyczne dla hotfixa i pakowania przeszły w przebiegach celowanych. To jest jawna granica weryfikacji, nie ukryty sukces pełnej baterii.

## Granica prawdy

Ta aktualizacja nie tworzy biologicznego przeżycia ani stałego procesu w tle. Naprawia trasy rozmowy, pamięci, syntezy i parytetu trybów w ramach jednorazowych lub lokalnych wywołań runtime.
