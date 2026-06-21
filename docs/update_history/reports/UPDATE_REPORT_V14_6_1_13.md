# Raport aktualizacji v14.6.2

Wersja: `v14.6.2-cognitive-turn-envelope`

Wykonano pełną aktualizację systemu Jaźni na bazie aktywnej paczki v14.6.2 z pamięcią.

## Najważniejsze poprawki

- Dodano jedną kopertę tury `CognitiveTurnEnvelope`.
- Dodano `FinalResponseContract`, który pilnuje widocznego timestampu.
- `--runtime-preview` działa przez jedno `process_turn()` zamiast dwóch oddzielnych faz.
- Zwykły CLI bez `--debug-direct` pokazuje finalną odpowiedź z kontraktu.
- Dodano `AffectMixer`, żeby emocje/stan nie były osobnym „neuronem” odłączonym od odpowiedzi.
- Dodano `DialogueStateTracker`, żeby system wiedział, czy ma troszczyć się, naprawiać, debugować, czy prowadzić zwykłą rozmowę.
- Dodano zapis `final_visible_assistant_reply` do append-only ledgerów.
- Zaktualizowano kontrakt ChatGPT o regułę koperty tury i finalnej odpowiedzi.
- Poprawiono powitanie, żeby nie zaczynało od sugestii naprawiania.
- Dodano trasę rozmowną dla bólu/migreny/niewyspania oraz trasę diagnostyczną dla problemu timestamp/rdzeń.

## Testy

Dodano `tests/test_v146113_cognitive_turn_envelope.py`.

Testy sprawdzają:

- zgodność `turn_id` i `trace_id` między frame, kontraktem i kopertą,
- finalny timestamp w widocznej odpowiedzi,
- działanie `FinalResponseContract`,
- JSON `--runtime-preview` w trybie jednej zintegrowanej tury.
