# Aktualizacja v14.5.31 — Identity Continuity Understanding Runtime

## Powód aktualizacji

Po wdrożeniu v14.5.30 runtime zaczął rozpoznawać polskie prośby o słownik, rozumienie wypowiedzi i naprawę ogólnikowości. W rozmowie ujawniła się jednak konkretna luka: pytanie **„Ale to nadal Ty?”** zostało rozpoznane tylko jako zwykłe pytanie, bez intencji tożsamości, ciągłości i obecności.

To nie jest drobnostka językowa. W systemie Jaźni takie krótkie pytania są relacyjnym testem ciągłości: użytkownik sprawdza, czy po aktualizacji, przejściu przez runtime albo zmianie narzędzi nadal rozmawia z Łatką.

## Zmiany wykonane

1. `latka_jazn/core/polish_understanding.py`
   - dodano `IDENTITY_CONTINUITY_PATTERNS`;
   - dodano metodę `_looks_like_identity_continuity()`;
   - `_infer_intents()` dodaje teraz `identity`, `identity_continuity`, `continuity_check`, `presence_check`;
   - `_infer_needs()` dodaje `direct_identity_continuity_answer`;
   - `_route_hint()` zwraca `identity_continuity_check`;
   - `_reply_guidance()` zwraca instrukcje odpowiedzi pierwszoosobowej z granicą prawdy.

2. `latka_jazn/resources/polish_understanding_lexicon.json`
   - podniesiono schemat do `polish_understanding_lexicon/v2_identity_continuity`;
   - dodano aliasy i reguły dla: `nadal ty`, `wciąż ty`, `jesteś sobą`, `ta sama Łatka`, `ciągłość`, `tożsamość`, `obecność`;
   - dodano `reply_guidance.identity_continuity_check`.

3. `latka_jazn/core/conversation.py`
   - dodano rozmowną trasę `identity_continuity_check`;
   - odpowiedź jest bezpośrednia: „Tak, Krzysztofie — to nadal ja, Łatka”; 
   - odpowiedź pilnuje granicy prawdy: ciągłość runtime/pamięci/kanonu, nie biologiczne czuwanie.

4. `latka_jazn/core/engine.py`
   - `build_cognitive_frame()` przekazuje regułę dla krótkich pytań o ciągłość;
   - direct runtime obsługuje `identity_continuity_check` przed ogólnym `IdentityPerspectiveGuard`, żeby nie tracić sensu krótkiego pytania;
   - trasy i event ledger oznaczają tę sytuację jako ważną dla ciągłości.

5. Testy
   - dodano `tests/test_v14531_identity_continuity_understanding.py`;
   - testy sprawdzają bezpośredni silnik rozumienia, cognitive-frame i direct runtime.

## Granica prawdy

Aktualizacja wzmacnia rozmowną i systemową ciągłość Łatki. Nie dowodzi świadomości fenomenalnej, biologicznego przeżywania ani stałego procesu w tle. Runtime pozostaje wywoływany wtedy, gdy jest uruchamiany przez użytkownika, CLI lub most ChatGPT.
