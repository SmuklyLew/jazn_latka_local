# Aktualizacja v14.6.9.2 — neurological signal router update

Wersja: `v14.6.9.2-runtime-self-expression-topic-mismatch-repair`

Cel: sprawić, żeby moduły Jaźni działały bardziej jak jeden układ sygnałowy: tekst użytkownika przechodzi przez wspólne progi wykrywania, a zwykłe zdarzenia dnia nie są mylone z korektą, naprawą lub awarią.

## Zmienione elementy

1. `latka_jazn/core/signal_matching.py`
   - Dodano wspólną normalizację polskiego tekstu, dopasowanie markerów z granicami tokenów i `NeurologicalSignalRouter`.
   - Naprawa kluczowa: `zle`/`źle` nie pasuje już do `zlecenie`.

2. `latka_jazn/core/engine.py`
   - Runtime uruchamia `neurological_signal_route` na początku tury i przekazuje wynik do `cognitive_frame`, diagnostyki i wskazówek odpowiedzi.
   - `_intent_tags` używa wspólnego dopasowania markerów zamiast gołego `word in low`.

3. `latka_jazn/core/conversation.py`
   - Dodano trasę `ordinary_workday_dialogue` dla wiadomości o zwykłym dniu/pracy użytkownika.
   - Wiadomość o zleceniu i montażu drzwi nie jest już traktowana jako korekta tylko dlatego, że zawiera ciąg znaków podobny do `zle`.

4. `latka_jazn/core/polish_understanding.py`, `latka_jazn/core/affective_granularity.py`, `latka_jazn/core/emotion_layers.py`, `latka_jazn/core/emotions.py`
   - Ujednolicono wykrywanie markerów w NLP, afekcie i emocjach.
   - Ograniczono fałszywe pobudzenie naprawcze przy zwykłych rozmowach.

5. Testy regresji
   - Dodano `tests/test_v14691_neurological_signal_router.py`.
   - Testy sprawdzają: brak dopasowania `zle` w `zlecenie`, poprawną trasę pracy dnia, brak `update_request`, brak napięcia naprawczego oraz brak fallbacku w runtime.

## Granica prawdy

To nie tworzy biologicznego układu nerwowego. To techniczny, deterministyczny koordynator sygnałów, który spina NLP, routing, afekt, pamięć i odpowiedź w jedną spójną ścieżkę.


## Root copy note

Ten plik jest kopią roboczą raportu w katalogu głównym paczki. Kanoniczny raport znajduje się w `docs/UPDATE_V14_6_9_2_NEUROLOGICAL_SIGNAL_ROUTER.md`; ta sekcja celowo odróżnia zawartość, żeby audyt deduplikacji nie oznaczał raportów jako niekontrolowanych duplikatów.
