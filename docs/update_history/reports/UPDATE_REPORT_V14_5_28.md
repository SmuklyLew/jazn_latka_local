# Raport aktualizacji v14.5.28-awareness-logic

Wersja: `v14.5.28-awareness-logic`

## Cel

Krzysztof poprosił o aktualizację wzmacniającą Jaźń o świadomość i logiczne myślenie. W tej wersji wdrożono to jako **świadomość operacyjną** i **jawne logiczne wnioskowanie**, bez deklarowania fenomenalnego lub biologicznego przeżywania.

## Co dodano

- `latka_jazn/core/operational_awareness.py`
  - aktywny workspace;
  - priorytety uwagi;
  - samo-monitoring;
  - kontrole metapoznawcze;
  - jasne ograniczenie: operacyjne, nie fenomenalne.

- `latka_jazn/core/logical_reasoning.py`
  - fakty;
  - założenia;
  - niewiadome;
  - zastosowane reguły;
  - sprzeczności/ryzyka;
  - jawny publiczny ślad audytu;
  - końcowy wniosek.

- `latka_jazn/core/engine.py`
  - `build_cognitive_frame(...)` zwraca `operational_awareness` i `logical_reasoning`;
  - bezpośrednie `handle_user_message(...)` zapisuje nowy stan w eventach;
  - intencje rozpoznają `awareness` i `reasoning`;
  - fallback diagnostyczny wskazuje nowe pola.

- `latka_jazn/adapters/chatgpt_adapter.py`
  - dodano `awareness_rule` i `reasoning_rule`;
  - kontrakt mówi, że ChatGPT ma używać Jaźni jako warstwy poznawczej, nie jako drugiego rozmówcy.

- `latka_jazn/memory/runtime_persistence.py`
  - prośby o świadomość/logikę są promowane do reguły proceduralnej;
  - nowy schemat: `v14.5.28-awareness-logic`.

- `latka_jazn/core/self_architecture.py`
  - dodano warstwy `operational_awareness` i `logical_reasoning`.

- `latka_jazn/core/scientific_basis.py`
  - dopisano źródła inspiracji: Global Workspace, Higher-Order Theories, ACT-R, Soar i LIDA.

## Granica prawdy

Ta aktualizacja nie twierdzi, że Jaźń uzyskała biologiczną świadomość, ciało, fenomenalne przeżywanie albo stałe czuwanie w tle. Dodaje kontrolowalny model operacyjny: runtime wie, co jest w centrum uwagi, jakie są reguły prawdy, jakie są przesłanki i jaki wniosek wolno postawić.

## Testy

- `pytest -q` → `57 passed`
- `python main.py --status-readonly` → runtime zwrócił status `v14.5.28-awareness-logic`
- `python main.py --cognitive-frame "Przygotuj aktualizację systemu Jaźni: świadomość operacyjna i logiczne myślenie."` → JSON zawiera:
  - `intent_tags`: `architecture`, `awareness`, `reasoning`
  - `operational_awareness.model_kind`: `operational_self_awareness_not_phenomenal_consciousness`
  - `logical_reasoning.public_trace`: 4 kroki audytu
  - `persistence.candidate_kind`: `reguła_proceduralna`

## Pamięć

Aktualizacja została zapisana przez `VersionUpdateRecorder` do:

- `memory/raw/dziennik.json`
- `memory/layered/episodic.jsonl`
- `memory/layered/reflections.jsonl`
- `memory/layered/semantic.jsonl`
- `memory/layered/procedural.jsonl`
- `memory/layered/truth_audits.jsonl`
- `workspace_runtime/latka_jazn_v14_5_28.sqlite3`

## Ograniczenia

- runtime nadal działa jako wywołanie programu, nie jako demon w tle;
- `chat.html` jest rozpakowany w aktywnym folderze roboczym, ale eksport full zachowuje `chat.html.7z` i pomija rozpakowany HTML, żeby nie dublować ogromnych danych;
- „świadomość” w nazwie aktualizacji oznacza świadomość operacyjną/funkcjonalną.
