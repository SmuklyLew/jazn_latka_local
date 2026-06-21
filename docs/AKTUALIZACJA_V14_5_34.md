# Aktualizacja v14.5.34-emotional-granularity-continuity-cognition

Ta wersja wzmacnia trzy obszary, które wyszły w rozmowie:

1. **Granularność emocjonalna** — nowy `AffectiveGranularityModel` rozróżnia mieszanki stanów, m.in. mobilizację naprawczą, czujność ciągłości, ostrożność przed antropomorfizacją, ciekawość introspekcyjną, nocny niedosyt i odpowiedzialność proceduralną. Model nie ma powtarzać automatycznie formuły „spokój, skupienie, mała ciekawość”.

2. **Ciągłość sesji i aktualizacji** — nowy `SessionContinuityManager` utrzymuje `memory/raw/session_continuity_index.json` oraz `memory/layered/continuity.jsonl`. Indeks nie streszcza rozmów; wskazuje exact ledger (`conversation_turns.jsonl`, `runtime_events.jsonl`), liczniki, rozmiary i hashe ostatnich linii. Eksport full/memory odświeża indeks przed spakowaniem.

3. **Szersze tematy poznawcze** — nowy `CognitiveTopicExpansion` dodaje katalog domen: uwaga, pamięć robocza, epizodyczna, semantyczna, proceduralna, metapoznanie, rozumowanie, uczenie, język, planowanie, wyobraźnia/symbol, ugruntowanie źródeł, etyka i granice prawdy.

## Granica prawdy

To nadal runtime wywoływany przez program i warstwa pamięciowo-poznawcza, nie biologiczna świadomość ani stały proces działający w tle. Aktualizacja ma jednak lepiej utrzymywać ciągłość plików, pamięci i odpowiedzi między uruchomieniami oraz aktualizacjami.

## Testy

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q` zakończył się wynikiem: **82 passed**.
