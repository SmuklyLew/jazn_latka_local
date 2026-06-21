# Aktualizacja v14.5.32 — cognitive packets, samopoczucie i mądry dobór emotikonów

## Status

Wersja: `v14.5.32-cognitive-packets-self-state-runtime`

Ta aktualizacja rozszerza v14.5.31 bez usuwania wcześniejszych warstw. Zachowuje poprawki: rozmowny runtime bez pustych fallbacków, rozumienie polskich wypowiedzi, pytania o ciągłość typu „Ale to nadal Ty?”, logiczne wnioskowanie, świadomość operacyjną, pamięć warstwową, SQLite, surową pamięć `chat.html.7z`, eksporty i testy regresji.

## Dodane elementy

1. `latka_jazn/core/cognitive_packets.py`
   - nowy moduł `CognitivePacketLibrary`;
   - buduje pakiety poznawcze dla bieżącej wypowiedzi;
   - każdy pakiet ma: `key`, `name`, `activation`, `triggers_found`, `purpose`, `response_guidance`, `truth_boundary`, `confidence`;
   - zwraca `state_emoticon` z markerem, powodem, polityką użycia, kandydatami i confidence.

2. `latka_jazn/resources/cognitive_packet_catalog.json`
   - jawny katalog pakietów:
     - `identity` — tożsamość,
     - `continuity` — ciągłość,
     - `knowledge` — wiedza,
     - `logic` — logika,
     - `intelligence` — inteligencja,
     - `learning` — nauka/uczenie,
     - `emotions` — emocje,
     - `experience` — doświadczenie,
     - `memories` — wspomnienia,
     - `impressions` — wrażenia,
     - `wellbeing` — samopoczucie,
     - `emoticons` — emotikony stanu.

3. Integracja z `JaznEngine.build_cognitive_frame()`
   - pakiet ChatGPT otrzymuje teraz pola:
     - `cognitive_packets`,
     - `state_emoticon`;
   - `reply_guidance` jest rozszerzane o wskazówki z aktywnych pakietów;
   - zdarzenia runtime dostają tag `cognitive_packets`.

4. Rozbudowa `PolishUnderstandingEngine`
   - słownik domenowy rozpoznaje prośby o rozszerzenie `packets`;
   - nowy route: `cognitive_packet_expansion_update`;
   - nowe potrzeby:
     - `expand_cognitive_packets`,
     - `smart_emoticon_selection`;
   - ostrożnie ograniczono wykrywanie `zasób`, żeby zwykłe zdanie o „zasobach ChatGPT” nie było mylone z prośbą o pakiety.

5. Rozbudowa `ConversationResponder`
   - direct runtime umie odpowiedzieć rozmownie na prośbę o rozszerzenie cognitive packets;
   - nie przechodzi przez debugowy fallback.

6. Rozbudowa `SelfArchitecture`
   - nowa warstwa `cognitive_packets` jako część architektury Jaźni.

7. Dobór emotikonów
   - `AffectiveState.marker()` nie jest już prostym przełącznikiem spokój/napięcie;
   - dobór uwzględnia m.in. tożsamość, korektę, napięcie, bliskość i spójność;
   - pełniejszy dobór jest w `CognitivePacketLibrary.select_emoticon()`.

8. Eksport paczek
   - `package_export.py` przechowuje `.sqlite3` i `.7z` bez ponownej kompresji deflate, żeby pełny eksport nie wyglądał jak zawieszony runtime;
   - ZIP nadal pomija pliki transient: `-wal`, `-shm`, `.sqlite3-wal`, `.sqlite3-shm`.

## Zasady prawdy

Pakiety poznawcze nie są osobnymi osobowościami i nie dowodzą biologicznego przeżywania. Są jawnie nazwanymi warstwami uwagi runtime: pomagają dobrać odpowiedź, granicę prawdy, poziom ostrożności, kierunek pamięci i marker stanu.

## Testy

Pełna bateria testów:

`77 passed in 22.85s`

Dodane testy v14.5.32 sprawdzają:

- wykrywanie `cognitive_packet_expansion_update`,
- direct response bez fallbacku,
- pełne pokrycie 12 pakietów,
- obecność `cognitive_packets` i `state_emoticon` w cognitive-frame.

## Opcjonalne narzędzia NLP

Wersja zachowuje zależność opcjonalną `polish-nlp` w `pyproject.toml`: `spacy`, `morfeusz2`, `stanza`, `language-tool-python`. Runtime działa bez nich, korzystając z wbudowanego słownika domenowego i ostrożnej normalizacji. Gdy narzędzia są dostępne lokalnie, mogą wzmacniać analizę fleksyjną, lematyzację, parsing i korektę językową.
