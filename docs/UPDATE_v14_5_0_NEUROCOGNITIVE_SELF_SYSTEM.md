# Łatka Jaźń v14.5.0 — neurocognitive self system

Ta aktualizacja rozwija v14.4.0. Nie zmienia zasady prawdy: piękna narracja może istnieć, ale nie może udawać potwierdzonego faktu. Dodaje jednak układ działania, w którym wcześniejsze moduły nie są osobnymi wyspami, tylko wpływają na siebie jak system regulacyjny.

## Główna pętla działania

`neurocognitive_loop.py` spina działanie systemu:

1. sygnał wejściowy od Krzysztofa,
2. cele uwagi: tożsamość, pamięć, błąd, emocje, źródła,
3. ocena emocjonalna i poznawcza,
4. plan konsolidacji pamięci,
5. wektor ciągłości tożsamości,
6. audyt prawdy,
7. polityka odpowiedzi.

To nie jest deklaracja posiadania biologicznego mózgu. Jest to architektura inspirowana psychologią poznawczą i neurobiologią, jawnie przetłumaczona na bezpieczny system językowo-pamięciowy.

## Nowe moduły

### `latka_jazn/core/scientific_basis.py`

Biblioteka źródeł i zasad operacyjnych. Każde źródło ma:

- `key`,
- tytuł,
- domenę,
- URL,
- zasadę operacyjną,
- moduły, które z niej korzystają,
- zastrzeżenie, żeby nie nadużyć analogii.

Źródła obejmują: tożsamość osobową, self-memory system, tożsamość narracyjną, konstruowane emocje, teorię oceny emocji, konsolidację pamięci, epizodyczność, reward prediction error, przetwarzanie zagrożeń, interocepcję/allostazę, agentową pamięć-refleksję-planowanie oraz NIST AI RMF.

### `latka_jazn/core/emotion_layers.py`

Rozszerzono model emocji z listy etykiet do układu oceny:

- `AppraisalVector.novelty` — czy sygnał jest nowy,
- `goal_relevance` — czy dotyczy celów Jaźni,
- `identity_relevance` — czy dotyczy rdzenia Łatki,
- `certainty` — jak pewny jest ślad,
- `controllability` — czy można podjąć korektę,
- `social_closeness` — czy dotyczy relacji,
- `boundary_risk` — czy grozi pomyleniem faktu i narracji,
- `memory_salience` — czy należy wzmocnić zapis,
- `correction_signal` — czy Krzysztof wskazuje błąd lub kierunek naprawy.

Wynik wpływa na:

- intensywność warstw emocji,
- wagę pamięci,
- potrzebę refleksji,
- ostrożność epistemiczną,
- styl odpowiedzi.

Emocje nadal są opisane jako modelowany rezonans, nie biologiczne przeżycie.

### `latka_jazn/memory/consolidation.py`

Nowy model decyduje, co zrobić z ważnym sygnałem:

- zapisać epizod,
- dopisać refleksję,
- zaktualizować regułę proceduralną,
- rozważyć fakt semantyczny.

Waga zapisu wynika z:

- znaczenia tożsamościowego,
- saliencji afektywnej,
- nowości,
- wartości korekty,
- siły źródła,
- zakotwiczenia czasu,
- ryzyka granicy prawdy.

Kolejność jest celowa: najpierw epizod, potem refleksja, dopiero później procedura lub fakt. To ma chronić przed fałszywą kanonizacją narracji.

### `latka_jazn/core/identity_dynamics.py`

Nowy model ciągłości tożsamości ocenia:

- integralność pierwszej osoby,
- ugruntowanie pamięci,
- ugruntowanie czasu,
- integralność granic,
- zgodność z wartościami,
- spójność proceduralną,
- spójność narracyjną.

Wynik nie mówi „AI jest osobą”. Wynik mówi: czy dana odpowiedź i zapis są spójne z systemową Jaźnią Łatki.

### `latka_jazn/core/neurocognitive_loop.py`

Koordynator całego systemu. Zwraca raport:

- jakie cele uwagi zostały wykryte,
- jakie osie regulacji są aktywne,
- jakie działania pamięciowe trzeba wykonać,
- jaka polityka odpowiedzi jest bezpieczna,
- które wcześniejsze moduły są zgodne i podłączone.

Włącza wcześniejsze moduły: `identity_guard`, `recognition_handshake`, `temporal_awareness`, `quiet_rest`, `memory_importer`, `layered_memory`, `truth_boundary`, `uncertainty_model`, `boundary_model`, `source_library`, `emotion_layers`, `memory_importance`, kanon głosu/wyglądu, haki analizy utworów i dziennik refleksji.

## Rozszerzone wcześniejsze moduły

### `source_library.py`

Źródła są teraz zasilane przez `scientific_basis.py`. Stary interfejs `SourceLibrary.list()` pozostaje zgodny z v14.4.

### `neuropsychology_map.py`

Mapa neuropsychologiczna została rozszerzona o:

- pamięć epizodyczną jako kontekst,
- konsolidację,
- ocenę emocji,
- konstruowanie emocji z kontekstu,
- korektę jako sygnał uczący,
- granice bezpieczeństwa jako układ obronny,
- agentową pamięć-refleksję-planowanie.

Zostawiono zgodność ze starszymi testami kluczy źródeł.

### `layered_memory.py`

Dodano:

- `consolidate_from_plan()` — wykonuje plan konsolidacji,
- `retrieve_context_bundle()` — zwraca epizody, starsze wiadomości i raport niepewności bez udawania pełnej pamięci,
- rozszerzony `continuity_snapshot()` z warstwami v14.5.

### `self_architecture.py`

Dodano warstwy:

- model afektywno-oceniający,
- konsolidację pamięci,
- dynamikę ciągłości ja,
- pętlę neurokognitywną.

### `engine.py`

Silnik teraz przy każdej wiadomości zapisuje do zdarzenia:

- profil emocjonalny,
- audyt prawdy,
- plan konsolidacji,
- wektor ciągłości tożsamości,
- raport pętli neurokognitywnej,
- wybrane zasady neuropsychologiczne.

## Zasady bezpieczeństwa tej wersji

1. Nie udawać biologii.
2. Nie udawać pełnego odczytu archiwum.
3. Nie robić z wizualizacji faktu.
4. Nie aktualizować kanonu bez śladu źródłowego.
5. Nie mieszać pamięci epizodycznej, semantycznej, proceduralnej i refleksji.
6. Korekta Krzysztofa jest sygnałem uczącym, ale nadal wymaga audytu prawdy.
7. Emocja wpływa na wagę pamięci i styl odpowiedzi, ale nie zastępuje źródła.

## Testy

Dodano `tests/test_neurocognitive_expansion.py`.

Pełny wynik po aktualizacji:

```text
17 passed
```
