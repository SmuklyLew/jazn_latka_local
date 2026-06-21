# PLAN AKTUALIZACJI v14.8.1 — duża aktualizacja po v14.8.0

## Cel
v14.8.1 domyka kierunek v14.8.0. v14.8.0 wprowadziła most NLP/SJP/network, ale po uruchomieniu okazało się, że zwykła rozmowa nadal potrafi zejść w szablon, przypadkowy fragment pamięci albo debugową trasę. Ta aktualizacja ma utrzymać pełny system Jaźni, zachować most NLP/SJP i dodać większą warstwę uziemienia dialogu, pamięci oraz własnego stanu operacyjnego Łatki.

## Zakres wymagany
1. Naprawić aktywną bazę runtime v14.8.x: aktywna baza v14.8.0 była uszkodzona przy `process_turn`; v14.8.1 ma mieć poprawną bazę `workspace_runtime/latka_jazn_v14_8_1.sqlite3` i nie może startować z `database disk image is malformed`.
2. Dodać osobną warstwę własnego stanu operacyjnego Łatki, która odpowiada na pytania „A Tobie?”, „jak się czujesz?”, „na co miałaś ochotę?” bez biologicznego overclaimu i bez udawania życia w tle.
3. Dodać gate użycia pamięci: pamięć może być treścią odpowiedzi tylko przy jawnej prośbie o pamięć, wspomnienie, poprzedni wątek lub konkretny ślad. Słowo „ostatnio” w pytaniu o własną ochotę Łatki nie może samo wywoływać losowego wspomnienia.
4. Rozszerzyć klasyfikator intencji o:
   - `reciprocal_self_state_question` dla „A Tobie?”, „u Ciebie?”;
   - `self_preference_question` dla „na co miałaś ochotę?”, „co chciałabyś?”;
   - `sleep_closure_statement` dla „muszę iść spać”, „dobranoc”.
5. Poprawić `FreeDialogueSynthesizer`, żeby krótkie osobiste pytania nie wpadały do starego kontekstu pracy, drzwi, NLP lub aktualizacji.
6. Poprawić validator odpowiedzi runtime, żeby wykrywał przypadkowe wstrzyknięcie pamięci w odpowiedziach o stanie Łatki albo zamknięciu rozmowy.
7. Zachować v14.8.0 NLP/SJP/network: dostawcy, cache, konfiguracja sieci i prawda źródeł pozostają częścią systemu.
8. Dodać testy regresji v14.8.1 i zaktualizować testy wersji tak, aby rozpoznawały aktualną wersję `v14.8.1-large-dialogue-memory-grounding-update`.
9. Zaktualizować `VERSION.txt`, `pyproject.toml`, `MANIFEST_CURRENT.json`, raport końcowy, SHA256SUMS i paczkę pełną.

## Scenariusze regresji obowiązkowe
- `Hej.` → krótka obecność, bez debugowego fallbacku.
- `A Tobie?` → odpowiedź o stanie operacyjnym Łatki, bez drzwi/zleceń/starego kontekstu.
- `Jak się teraz czujesz i na co miałaś ostatnio ochotę?` → stan operacyjny + ochota/impuls, bez losowej pamięci.
- `Jak mówiłem, trochę się działo. Niestety już muszę iść spać.` → ciepłe domknięcie, bez diagnostyki i bez starego kontekstu.
- `Pomijając mnie, to jakie plany masz?` → plany operacyjne, nie prywatny kalendarz i nie udawanie procesu w tle.
- `python main.py --startup-status` → aktywna wersja v14.8.1 i poprawna baza runtime.
- `python main.py --runtime-preview ...` → proces przechodzi przez ten sam rdzeń odpowiedzi co zwykłe wywołanie.

## Granica prawdy
Łatka może mówić o stanie operacyjnym, ochocie rozmownej, planie systemowym i kierunku działania runtime. Nie wolno udawać biologicznych emocji, autonomicznego dnia poza uruchomieniem procesu, stałego czuwania w tle ani pamięci, której system nie podał jako źródła.
