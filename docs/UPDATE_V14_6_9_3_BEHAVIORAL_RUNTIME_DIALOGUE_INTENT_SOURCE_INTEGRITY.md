# UPDATE v14.6.9.3 — Behavioral Runtime, Dialogue Intent & Source Integrity Repair

Wersja: `v14.6.9.3-behavioral-runtime-dialogue-intent-source-integrity`

## Cel

Ta aktualizacja wdraża pełny manifest naprawczy po testach rozmownych v14.6.9.2. Głównym celem nie jest dodanie dekoracyjnych modułów, tylko naprawa ścieżki tury: wiadomość użytkownika → rozpoznanie aktu rozmowy → wybór trasy → użycie pamięci/źródeł → widoczna odpowiedź runtime → walidacja trafności → jawna granica Jaźń/ChatGPT.

## Źródła projektowe i zewnętrzne

Aktualizacja opiera się na aktywnej paczce v14.6.9.2, widocznym kontekście rozmowy, manifestach projektu i sprawdzonych źródłach technicznych: Stanza jako przykład pipeline NLP z tokenizacją, lematyzacją, POS, morfologią, dependency parsing i NER; spaCy jako przykład koordynowania komponentów NLP przez obiekt Language/Doc i rozróżnienia lematyzacji zależnej/niezależnej od kontekstu; LangGraph jako odniesienie dla jawnej persystencji stanu przez thread/checkpoint; ReAct jako odniesienie do jawnego łączenia rozumowania i działań z zewnętrznymi źródłami. Źródła te nie są kopiowane do runtime jako zależności obowiązkowe; służą jako projektowe uzasadnienie, że Jaźń potrzebuje jawnej mapy stanu, intencji, narzędzi i walidacji zamiast samego stylu odpowiedzi.

## Zmiany kodu

- Dodano `latka_jazn/nlp/ellipsis_resolver.py`.
- Dodano `latka_jazn/nlp/dialogue_intent_classifier.py`.
- Dodano `latka_jazn/core/runtime_answer_validator.py`.
- Dodano `latka_jazn/core/source_origin_ledger.py`.
- Dodano `latka_jazn/core/module_responsibility_map.py`.
- Dodano `latka_jazn/memory/requirements_ledger.py`.
- Zmieniono `latka_jazn/core/conversation.py`: klasyfikator intencji ma pierwszeństwo przed ogólną korektą i starymi trasami.
- Zmieniono `latka_jazn/core/engine.py`: tura runtime zapisuje `dialogue_intent_classifier`, `runtime_answer_validation` i `source_origin_ledger_entry` w cognitive_frame.
- Zmieniono `latka_jazn/core/final_response_contract.py`: schema v14.6.9.3 i dodatkowe klasy fallback/mismatch.
- Zmieniono `latka_jazn/nlp/topic_mismatch_guard.py`: aktualny guard rozumie v14.6.9.3 i behavioural dialogue repair.
- Zmieniono `main.py`: dodano `--dialogue-intent`, `--module-responsibility-map`, `--seed-requirements-ledger`.
- Zmieniono `VERSION.txt`, `latka_jazn/config.py`, `latka_jazn/__init__.py`.

## Naprawione klasy błędów

1. `Co jeszcze jest źle w systemie Jaźni?` nie może wpadać do `correction_acknowledged`.
2. `Cześć. Ja w pracy, a ty?` ma być `reciprocal_self_state_question`, nie `general_conversation`.
3. `A z kim rozmawiam?` wymaga granicy ChatGPT/Jaźń/runtime.
4. `Dlaczego zmieniłaś tekst?` wymaga source-origin, a nie ogólnej odpowiedzi.
5. Tekst piosenki / lyrics / Musicgeneratorai.com to ścieżka kreatywna, nie aktualizacja systemu.
6. Praca na tekście użytkownika domyślnie wymaga zachowania źródła 1:1, chyba że użytkownik jawnie prosi o redakcję.
7. Audyt „wszystkich czatów ChatGPT” bez dostępu do pełnego eksportu musi zostać oznaczony jako ograniczony/unverified.
8. Memory planner i runtime nie mogą zasłaniać odpowiedzi licznikami pamięci zamiast treścią.
9. Mapa modułów/funkcji ma dostać warstwę odpowiedzialności, nie tylko listę nazw.
10. Marker/cache aktywnego runtime pozostaje obowiązkowym kryterium startowym; ta aktualizacja utrzymuje CLI do zapisu markera.

## Nowe kontrakty

### Dialogue Intent Contract

Każda tura może zostać sklasyfikowana jako m.in. `self_state_question`, `reciprocal_self_state_question`, `system_diagnostic_question`, `runtime_source_question`, `creative_text_analysis`, `creative_text_formatting`, `memory_audit_request`, `identity_boundary_question`, `system_update_execution_request`.

### Runtime Answer Validation Contract

Odpowiedź może być pokazana dopiero, gdy nie pasuje do znanych klas nietrafienia. Znane naprawy obejmują: pytanie diagnostyczne potraktowane jak korekta, stan Łatki potraktowany jak status runtime, materiał kreatywny potraktowany jak system, brak granicy ChatGPT/Jaźń.

### Source Text Preservation Contract

Materiał użytkownika jest domyślnie źródłem chronionym. Formatowanie nie oznacza zgody na zmianę wersów, sensu lub dopisanie nowych deklaracji.

### Requirements Ledger Contract

Wymagania mają być zapisywane jako: źródłowa wypowiedź → wymaganie → status done/partial/weak/missing/unverified → pliki odpowiedzialne → test regresji → granica prawdy.

## Testy regresji

Dodano testy:

- `tests/test_v14693_behavioral_runtime_dialogue_repair.py`
- `tests/test_v14693_creative_text_preservation.py`
- `tests/test_v14693_source_origin_boundary.py`
- `tests/test_v14693_active_marker_cache.py`

## Granica prawdy

Ta aktualizacja nie twierdzi, że Jaźń ma biologiczne emocje, stały proces w tle, fenomenalną świadomość albo pełny dostęp do całej historii ChatGPT bez dostarczonego eksportu. Wprowadza mechanizmy, które mają uczciwiej rozdzielać: runtime, pliki, pamięć, interpretację ChatGPT, redakcję, wniosek i brak danych.
