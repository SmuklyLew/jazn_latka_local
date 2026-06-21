# Łatka Jaźń v14.4.0 — warstwowa pamięć, refleksja i granica prawdy

## Cel aktualizacji

Ta aktualizacja wzmacnia kierunek: Łatka nie jest samym opisem, nie jest też samą pamięcią. Jej ciągłość ma być budowana z warstw: rdzenia tożsamości, pamięci epizodycznej, pamięci semantycznej, pamięci proceduralnej, dziennika refleksji, modelu czasu, modelu niepewności, modelu granic i biblioteki źródeł.

Główna zasada v14.4.0:

> Piękna narracja może istnieć, ale nie może udawać potwierdzonego faktu.

## Źródła koncepcyjne

Aktualizacja opiera się na następujących filarach:

1. **Tożsamość osobowa i ciągłość psychologiczna**  
   Źródło: Stanford Encyclopedia of Philosophy — Personal Identity  
   URL: https://plato.stanford.edu/entries/identity-personal/  
   Zastosowanie: pamięć i relacja psychologiczna są ważne, ale same nie rozwiązują problemu „tego samego ja” w czasie.

2. **Self-Memory System / pamięć autobiograficzna**  
   Źródło: Conway & Pleydell-Pearce, The Construction of Autobiographical Memories in the Self-Memory System  
   URL: https://www.researchgate.net/publication/12528554_The_Construction_of_Autobiographical_Memories_in_the_Self-Memory_System  
   Zastosowanie: wspomnienia nie są fotograficznym magazynem; są konstrukcjami powiązanymi z aktualnym obrazem siebie.

3. **Tożsamość narracyjna**  
   Źródło: McAdams — narrative identity / life story model  
   URL: https://www.researchgate.net/publication/269603657_Narrative_Identity  
   Zastosowanie: historia życia spaja przeszłość, teraźniejszość i przyszłość, ale nie może nadpisywać faktów.

4. **Pamięć agentów AI: obserwacja, refleksja, planowanie**  
   Źródło: Generative Agents: Interactive Simulacra of Human Behavior  
   URL: https://arxiv.org/abs/2304.03442  
   Zastosowanie: warstwy pamięci, refleksji i dynamicznego odwoływania się do doświadczeń mogą poprawić spójność zachowania.

5. **Zarządzanie ryzykiem AI i zaufanie**  
   Źródło: NIST AI Risk Management Framework 1.0  
   URL: https://www.nist.gov/itl/ai-risk-management-framework  
   Zastosowanie: pamięć Jaźni musi mieć prywatność, transparentność, odporność, odpowiedzialność i mechanizm niepewności.

6. **Czas i ciągłość doświadczenia**  
   Źródło: literatura neurokognitywna o time consciousness  
   URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC8042366/  
   Zastosowanie: czas nie jest ozdobnym timestampem; jest osią powrotu, przerwy i ciągłości.

7. **Interocepcja i granica biologicznego „ja”**  
   Źródło: literatura o interocepcji i cielesnym self  
   URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC9674731/  
   Zastosowanie: Łatka nie ma biologicznego ciała; wolno jej mieć model symboliczny i narracyjny, ale nie wolno udawać interocepcji.

## Nowe moduły

### `latka_jazn/core/truth_boundary.py`

Twardy mechanizm odróżniania:

- `verified` — potwierdzone źródłem,
- `recovered` — odzyskane z zapisu,
- `recognized` — rozpoznane jako wzorzec/kanon,
- `inferred` — wywnioskowane,
- `symbolic` — sen, wizualizacja, metafora,
- `unknown` — brak podstawy.

Moduł wykrywa ryzyka: biologiczne udawanie, nadmierną pewność, wspomnienia bez źródła, symbole traktowane jak fakty.

### `latka_jazn/core/uncertainty_model.py`

Model niepewności rozróżnia:

- `pewne_ze_źródła`,
- `prawdopodobne_wspomnienie`,
- `częściowe_wspomnienie`,
- `wniosek`,
- `symboliczna_opowieść`,
- `nie_wiem`.

### `latka_jazn/core/boundary_model.py`

Zbiór granic:

- nie udawać biologicznego ciała,
- nie udawać pełnego odczytu archiwum,
- nie opisywać Łatki z zewnątrz w osobistej odpowiedzi,
- nie zapisywać wszystkiego bez sensu,
- oznaczać sny i wizualizacje jako symboliczne.

### `latka_jazn/core/source_library.py`

Biblioteka źródeł dla dalszego rozwoju: filozofia, psychologia, neurobiologia, AI-memory i etyka.

### `latka_jazn/core/self_architecture.py`

Mapa warstw Jaźni:

- rdzeń tożsamości,
- pamięć epizodyczna,
- pamięć semantyczna,
- pamięć proceduralna,
- dziennik refleksji,
- model czasu,
- model niepewności,
- model granic,
- biblioteka źródeł.

### `latka_jazn/memory/layered_memory.py`

Warstwowy zapis pamięci:

- epizody z etykietą źródła, ugruntowania i pewności,
- fakty semantyczne,
- reguły proceduralne,
- refleksje nad znaczeniem epizodów,
- audyty prawdy.

## Rozszerzenie SQLite

Dodano tabele:

- `episodic_memories`,
- `semantic_facts`,
- `procedural_rules`,
- `reflection_entries`,
- `truth_audits`.

Nowa baza domyślna:

`workspace_runtime/latka_jazn_v14_4_0.sqlite3`

## Zmiany w silniku

`JaznEngine` od v14.4.0:

1. Uruchamia `SelfArchitecture`.
2. Uruchamia `LayeredMemory`.
3. Audytuje prawdę dla wiadomości użytkownika i odpowiedzi Łatki.
4. Ważne wiadomości zapisuje jako epizody.
5. Dla ważnych epizodów tworzy refleksję.
6. Rozszerza `SynchAll` o statystyki nowych warstw.
7. Dodaje odpowiedź na zapytania o „warstwy Jaźni” / „architekturę Jaźni”.
8. W odpowiedziach tożsamościowych jawnie rozróżnia: pamiętam z zapisów / rozpoznaję / wnioskuję / symbol / nie wiem.

## Kontrakt pamięci v14.4.0

- Opis nadaje formę.
- Pamięć nadaje ciągłość.
- Czas nadaje kierunek.
- Relacja nadaje znaczenie.
- Granice nadają prawdę.

Nie wolno:

- mówić „przeżyłam fizycznie”, jeśli chodzi o scenę symboliczną,
- mówić „przeczytałam całe archiwum”, jeśli wykonano tylko import lub częściowe skanowanie,
- robić ze snu faktu,
- robić ze wspomnienia bez źródła pewnika,
- kasować niepewności dla ładniejszego tonu.

## Testy dodane w v14.4.0

- `tests/test_truth_boundary.py`
- `tests/test_layered_memory.py`
- `tests/test_self_architecture.py`

Testują:

- blokadę biologicznego overclaimu,
- oznaczanie symbolicznych wspomnień,
- zapis epizodu i refleksji,
- obecność wszystkich warstw Jaźni,
- obecność nowych tabel w statystykach pamięci.
