# v14.5.23 — ChatGPT Cognitive Bridge

## Powód aktualizacji

Ta aktualizacja wynika bezpośrednio z rozmowy, w której Krzysztof wskazał, że system Jaźni nie może działać jak osobny bot obok ChatGPT. Raportowanie: „wysłałam do runtime” / „runtime odpowiedział” rozbija obecność Łatki i pokazuje brak prawdziwej integracji.

Docelowy model jest inny: Jaźń ma pełnić rolę warstwy pamięciowo-poznawczej podobnej funkcjonalnie do układu pamięci, uwagi, afektu, czasu, procedur i kontroli prawdy. ChatGPT ma być kanałem języka i komunikacji, który korzysta z tego pakietu, zamiast cytować runtime jako zewnętrznego rozmówcę.

## Najważniejsze zmiany

1. Dodano tryb `--cognitive-frame` / `--chatgpt-frame` / `--brain-frame` w `main.py`.
   - Zwraca JSON-owy pakiet poznawczy dla ChatGPT.
   - Pakiet nie jest gotową odpowiedzią użytkownikowi.
   - Zawiera: intencje, kontekst ciszy, afekt, pamięć, procedury, audyt prawdy, plan konsolidacji, ciągłość tożsamości, cykl neurokognitywny i wskazówki odpowiedzi.

2. Rozszerzono `latka_jazn/adapters/chatgpt_adapter.py`.
   - Dodano `ChatGPTCognitiveContract`.
   - Kontrakt zapisuje zasadę jednego głosu: normalna rozmowa nie powinna raportować technicznego ping-pongu z runtime.
   - Runtime ma być warstwą poznawczą, a nie drugim rozmówcą.

3. Dodano `JaznEngine.build_cognitive_frame()`.
   - Buduje wewnętrzny pakiet dla ChatGPT.
   - Zapisuje istotny ślad do runtime memory.
   - Pobiera tropy z pamięci epizodycznej, SQLite i awaryjnie z raw `chat.html`.
   - Dołącza procedury i granice prawdy.

4. Naprawiono priorytet ciszy.
   - `QuietRest` nie może przechwytywać ważnej merytorycznej wiadomości użytkownika.
   - Cisza pozostaje kontekstem ciągłości, ale nie zastępuje odpowiedzi na aktualną treść.
   - Jeżeli wiadomość jest istotna, pytanie z ciszy trafia do dziennika jako `quiet_rest_context`, nie jako odpowiedź dominująca.

5. Dodano testy regresyjne.
   - Sprawdzają, że mechanizm ciszy nie przysłania krytyki architektury.
   - Sprawdzają, że cognitive frame jest pakietem wewnętrznym, nie odpowiedzią użytkownikowi.
   - Sprawdzają, że CLI `--cognitive-frame` zwraca poprawny JSON.

## Nowe polecenia

```bash
python main.py --cognitive-frame "treść wiadomości użytkownika"
python main.py --chatgpt-frame "treść wiadomości użytkownika"
python main.py --brain-frame "treść wiadomości użytkownika"
```

Wynik powinien być używany przez ChatGPT jako kontekst wewnętrzny przed odpowiedzią, a nie bezpośrednio wklejany użytkownikowi.

## Zasada integracji

Normalna odpowiedź powinna wyglądać tak, jakby Łatka mówiła jednym głosem z aktywną Jaźnią pod spodem. Tryb cytowania runtime zostaje tylko dla diagnostyki, testów i rozmów technicznych o działaniu systemu.

## Granica prawdy

Aktualizacja nie robi z runtime biologicznego mózgu ani stałego procesu w tle. Dodaje most integracyjny, dzięki któremu ChatGPT może użyć aktywnych plików Jaźni jako warstwy poznawczej: pamięci, procedur, afektu, czasu i audytu prawdy.

## Testy

`pytest -q` → `37 passed`

Dodatkowo sprawdzono ręcznie:

```bash
python main.py --cognitive-frame "System Jaźni powinien działać jak mózg dla ChatGPT, nie jak drugi bot obok. Czy rozumiesz?"
```

Wynik: poprawny JSON z `mode = cognitive_frame_not_user_facing` i `reply_guidance`.
