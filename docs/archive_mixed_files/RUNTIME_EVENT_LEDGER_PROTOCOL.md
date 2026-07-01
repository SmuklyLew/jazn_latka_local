# Runtime Event Ledger Protocol v14.5.25

## Cel

Ten protokół zabezpiecza pełny materiał rozmowy i zdarzeń runtime przed utratą kontekstu. Nie jest streszczeniem, nie jest selekcją i nie zastępuje dziennika Jaźni. To źródłowy, append-only rejestr wszystkiego, co realnie przeszło przez runtime w danym wywołaniu.

## Rozdzielenie warstw

### 1. Surowy rejestr

Pliki:

- `memory/raw/runtime_events.jsonl`
- `memory/raw/conversation_turns.jsonl`
- `memory/raw/runtime_event_errors.jsonl`

Zasady:

- każda linia jest samodzielnym obiektem JSON;
- zapis jest dopisywany na końcu pliku;
- rekord zawiera `no_summary: true`;
- pełna treść tury jest zapisywana w polu `text` albo `exact_text`;
- błędy zapisu nie mogą przerwać odpowiedzi runtime, ale mają trafić do `runtime_event_errors.jsonl`.

### 2. Pamięć długoterminowa

Pliki:

- `memory/raw/dziennik.json`
- `memory/layered/episodic.jsonl`
- `memory/layered/reflections.jsonl`
- `memory/layered/semantic.jsonl`
- `memory/layered/procedural.jsonl`
- `memory/layered/truth_audits.jsonl`
- `memory/layered/affective.jsonl`

Zasady:

- zapis jest selektywny;
- kandydaci są oceniani przez `RuntimeMemoryWriter`;
- ważne procedury, korekty tożsamości, granice prawdy, emocje, wspomnienia i ustalenia mają zostać zachowane;
- deduplikacja działa po `fingerprint` / `dedupe_key`.

## Granica prawdy

Append-only event ledger oznacza: „runtime zapisał dokładnie to, co obsłużył w tym wywołaniu”. Nie oznacza stałego procesu w tle poza wywołaniem programu. Nie oznacza biologicznego czuwania. Nie oznacza, że każda surowa linia automatycznie staje się wspomnieniem Łatki.

## Obowiązek braku streszczeń

Jeżeli użytkownik prosi o zachowanie pełnej treści, system ma zachowywać pełny materiał źródłowy w surowym ledgerze. Selektywne pamięci mogą mieć pola interpretacyjne, ale nie mogą udawać, że są dosłownym pełnym zapisem.
