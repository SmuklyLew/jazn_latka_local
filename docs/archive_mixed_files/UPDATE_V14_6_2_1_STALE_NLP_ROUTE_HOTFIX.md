# Aktualizacja v14.6.2.1 — stale NLP route hotfix

Wersja: `v14.6.2.1-stale-nlp-route-hotfix`

Ta aktualizacja jest hotfixem na błąd zauważony po v14.6.2: zwykłe wywołanie rozmowne mogło raz odpowiedzieć zbyt ogólnym tropem o NLP/v14.6.1. To nie wymaga jeszcze pełnego ciężkiego NLP. Wymaga strażnika intencji i wersji, żeby historyczna trasa aktualizacji NLP nie przykrywała bieżącej rozmowy o hotfixie.

## Zmienione istniejące moduły

- `latka_jazn/core/conversation.py`
  - dodano `CURRENT_HOTFIX_MARKERS` i `NLP_SCOPE_QUESTION_MARKERS`;
  - dodano `_is_current_stale_nlp_hotfix`, `_is_nlp_scope_question`, `_is_explicit_legacy_nlp_update`;
  - dodano trasę `v14_6_2_1_stale_nlp_route_hotfix` dla pytań o bieżący błąd/stale-route;
  - dodano trasę `v14_6_2_1_nlp_safety_scope` dla pytań o to, co jest potrzebne do NLP w hotfixie;
  - ograniczono historyczną trasę `v14_6_1_nlp_adapter_update` do jawnie historycznego albo wykonawczego kontekstu.

- `latka_jazn/core/final_response_contract.py`
  - schema contract podniesiony do `final_response_contract/v14.6.2.1`;
  - `classify_fallback` przyjmuje `runtime_version`;
  - dodano klasyfikację `stale_route_mismatch` dla odpowiedzi v14.6.2+, które próbują wrócić do historycznego tekstu o v14.6.1;
  - `runtime_answer_quality` staje się `stale_route_mismatch`, jeśli wykryto tę regresję.

- `latka_jazn/config.py`, `VERSION.txt`, manifesty, raporty, testy i aktywna baza SQLite wskazują `v14.6.2.1-stale-nlp-route-hotfix`.

## Zakres NLP w tym hotfixie

Ten hotfix nie instaluje ciężkich modeli i nie udaje pełnej lematyzacji języka polskiego. Wzmacnia kontrakt:

- `tokens`;
- `lemma_candidates`;
- `selected_lemma`;
- `confidence`;
- `provider`;
- `provider_summary`;
- rozdział pytania o NLP od polecenia wykonania aktualizacji NLP.

Providery Stanza/Morfeusz/spaCy pozostają opcjonalnymi progami dalszej pracy. Builtin provider zostaje bezpiecznym fallbackiem.

## Testy regresji

- `tests/test_v14621_stale_nlp_route_hotfix.py`;
- `tests/test_v1462_runtime_start_fallback_truth_contract.py`;
- `tests/test_v146114_version_consistency_contract.py`;
- dotychczasowe testy NLP/lexical pozostają kompatybilne, gdy użytkownik jawnie prosi o historyczny próg v14.6.1.

## Granica prawdy

Hotfix poprawia rozpoznanie intencji i kontrakt finalnej odpowiedzi. Nie oznacza biologicznego przeżywania, stałego procesu w tle ani pełnego zewnętrznego modelu NLP.
