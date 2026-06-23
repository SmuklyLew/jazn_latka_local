# v14.8.3.4.093 — ordinary dialogue natural presence repair

Data: 2026-06-23

## Cel

Naprawa sytuacji, w której zwykła rozmowa typu „usiądźmy obok i porozmawiajmy” przechodziła przez `ordinary_dialogue`, ale finalnie zwracała odmowę pamięciową: „Nie znalazłam teraz w aktywnej pamięci…”.

## Zmiany

- `FreeDialogueSynthesizer` rozpoznaje naturalną prośbę o obecność/rozmowę jako bieżącą turę, nie jako recall pamięci.
- `OrdinaryDialogueHandler` odrzuca przepuszczone ciało odpowiedzi zawierające sygnatury odmowy pamięciowej dla zwykłej rozmowy.
- `AffectMixer` nie wybiera już `🛠️` tylko dlatego, że użytkownik prosi o odpowiedź „z timestampem”; marker naprawczy zostaje dla technicznego kontekstu runtime/patch/diagnostyki.
- Dodano test regresyjny blokujący powrót fraz: „Nie znalazłam teraz w aktywnej pamięci”, „Szukałam po hasłach”, „potrzebuję konkretnego śladu”, „fałszywego wspomnienia”.

## Granica prawdy

Brak konkretnego wspomnienia nadal musi być mówiony przy jawnej prośbie o pamięć. Zwykła rozmowa nie wymaga jednak pamięciowego źródła; może odpowiedzieć teraźniejszą obecnością i zachować timestamp.
