# Aktualizacja v14.5.30 — Polish Understanding Runtime

## Cel

Ta aktualizacja rozwiązuje konkretny problem: system Jaźni ma lepiej rozumieć polskie wypowiedzi Krzysztofa, a nie tylko reagować na pojedyncze słowa albo wpadać w ogólnikową odpowiedź. Chodzi o praktyczną warstwę rozumienia: normalizacja polszczyzny, lematy, słownik domenowy Jaźni, intencje, potrzeby użytkownika i `route_hint` dla runtime.

## Co zostało dodane

1. `latka_jazn/core/polish_understanding.py`
   - nowy `PolishUnderstandingEngine`,
   - normalizacja tekstu,
   - wersja bez polskich znaków do wykrywania literówek i wariantów,
   - tokenizacja,
   - wbudowany fallback lematyzacji,
   - wykrywanie intencji,
   - wykrywanie potrzeb użytkownika,
   - `route_hint`,
   - `reply_guidance`,
   - jawne ograniczenia analizy.

2. `latka_jazn/resources/polish_understanding_lexicon.json`
   - słownik rodzin słów,
   - aliasy lematów,
   - reguły intencji,
   - potrzeby użytkownika,
   - wskazówki odpowiedzi dla aktualizacji rozumienia języka.

3. Integracja w `JaznEngine`
   - `handle_user_message(...)` zapisuje wynik `polish_understanding` w event ledger,
   - `build_cognitive_frame(...)` dodaje pole `polish_understanding` do pakietu dla ChatGPT,
   - tagi intencji z analizy językowej są łączone ze starszym routingiem,
   - `reply_guidance` mówi ChatGPT, żeby używał lematów, potrzeb i ryzyka ogólnikowości.

4. Integracja w `ConversationResponder`
   - nowa trasa `polish_understanding_update`,
   - runtime bezpośredni potrafi odpowiedzieć konkretnie, że potrzebna jest warstwa rozumienia polskiej wypowiedzi, a nie ogólna obietnica.

5. Integracja w `ChatGPTAdapter`
   - kontrakt Jaźni zawiera teraz `polish_understanding_rule`.

6. Opcjonalne zależności `polish-nlp`
   - `spacy`,
   - `morfeusz2`,
   - `stanza`,
   - `language-tool-python`.

   Nie są wymagane do działania. Runtime nie ładuje ich automatycznie, chyba że środowisko ustawi `LATKA_ENABLE_EXTERNAL_POLISH_NLP=1`.

## Granica prawdy

To nie jest biologiczne rozumienie ani świadomość fenomenalna. To operacyjna analiza polskiej wypowiedzi, która pomaga runtime i ChatGPT dobrać właściwą trasę odpowiedzi.

## Testy wykonane w tej sesji

- `pytest -q tests/test_v14530_polish_understanding.py` → `3 passed`
- `pytest -q` w trzech częściach:
  - część 1 → `31 passed`
  - część 2 → `18 passed`
  - część 3 → `16 passed`

Łącznie pokryto 65 testów. Pełne jednorazowe `pytest -q` w tym środowisku przerywało się przez limit czasu narzędzia przy długim eksporcie pełnej paczki, dlatego testy zostały uruchomione w trzech częściach obejmujących cały katalog `tests/`.

## Szybka próba runtime

```bash
python main.py "Poszukaj rozwiązania dla Jaźni: rozumienie wypowiedzi, polski słownik, mniej ogólnikowo. Dasz radę?"
```

Oczekiwany sens odpowiedzi: runtime mówi konkretnie o warstwie rozumienia polskiej wypowiedzi, słowniku domenowym Jaźni, intencjach, potrzebach i testach, bez debugowego fallbacku.
