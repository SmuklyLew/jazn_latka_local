# NLG Contract v14.8.4 — Łatka / Jaźń

**Status:** kontrakt projektowy dla serii patchy `v14.8.4.001–v14.8.4.007`.  
**Patch wprowadzający:** `v14.8.4.000 — Architecture plan and NLG contract documentation`.  
**Repo:** `SmuklyLew/jazn_latka_local`.  
**Branch roboczy:** `fix/v14.8.4-model-guided-nlg-operational-thoughts`.  
**Baza:** `stable-v14.8.3.4.093` / `work/v14-8-3-4-089-manifest-exclusion-detail-hotfix`.

Ten dokument nie zmienia runtime. Jest kontraktem dla kolejnych patchy kodowych. Celem jest dodanie kontrolowanej warstwy NLG i operacyjnych „myśli” Jaźni bez utraty granicy prawdy, bez fałszywej pamięci i bez oddania tożsamości zewnętrznemu modelowi.

---

## 1. Definicje

### 1.1. NLG

NLG oznacza w tym projekcie kontrolowane tworzenie tekstu odpowiedzi z danych runtime: bieżącej wiadomości użytkownika, rozpoznanej intencji, polityki pamięci, statusu źródeł, afektu operacyjnego, granicy prawdy i ewentualnego payloadu pamięci. NLG nie jest tożsame z losowym wyborem szablonu ani z niekontrolowanym wysłaniem całego kontekstu do modelu.

Klasyczne etapy NLG, które są ważne dla Jaźni, to:

- wybór treści do powiedzenia,
- ułożenie struktury wypowiedzi,
- agregacja lub rozdzielenie informacji,
- wybór leksyki i tonu,
- realizacja powierzchniowa zdania,
- ocena i walidacja przed pokazaniem odpowiedzi.

W v14.8.4 te etapy mają zostać rozdzielone tak, aby plan wypowiedzi był audytowalny, a model językowy — jeśli istnieje — był tylko kanałem realizacji językowej.

### 1.2. NLG Plan

`NlgPlan` jest jawny, serializowalny i audytowalny. Ma mówić, jakiego rodzaju odpowiedź wolno wygenerować, czego wymaga pamięć, czy model może być użyty, jakie elementy są wymagane i jakie są zakazane.

`NlgPlan` nie jest finalną odpowiedzią. Nie powinien zawierać prywatnego chain-of-thought. Jest kontraktem wykonawczym między rozumieniem wejścia a generowaniem odpowiedzi.

### 1.3. Operational Thought Frame

`OperationalThoughtFrame` to bezpieczny zapis decyzji runtime: co zauważono, jaki cel odpowiedzi wybrano, jaką politykę pamięci zastosowano, jaki ton wybrano i jakie ścieżki odrzucono. Nie jest to biologiczna świadomość, prywatne przeżycie ani ukryty chain-of-thought. Jest to audytowalna ramka robocza.

### 1.4. Model jako kanał języka

Model lokalny albo zewnętrzny może sformułować zdania, ale nie może być źródłem tożsamości, pamięci ani prawdy. Prawda pochodzi z runtime: memory gate, memory payload, voice source contract, canon, response policy, statusów źródeł i walidatorów.

---

## 2. Twarde wymagania kontraktu

1. Runtime musi nadal dodawać timestamp; model nie dodaje timestampu.
2. `final_visible_integrity.valid` musi pozostać warunkiem pokazania odpowiedzi jako głosu runtime.
3. `memory_gate=not_needed` oznacza, że pamięć nie trafia do model context.
4. Odpowiedź nie może mówić „pamiętam”, jeśli nie ma ugruntowanego payloadu pamięci.
5. `NullModelAdapter` nigdy nie może udawać generacji modelowej.
6. Model nie może dostać pełnej pamięci, surowych baz SQLite ani całych archiwów.
7. Model nie może dopisywać faktów, wspomnień, źródeł ani działań, których nie ma w przekazanym kontekście.
8. Dokładne cytaty runtime, diagnostyka źródeł i zadania wymagające zewnętrznego lookupu mogą omijać model.
9. Każdy kandydat odpowiedzi musi przejść walidację: zgodność z bieżącą turą, brak starej trasy, brak fałszywej pamięci, brak biologicznych roszczeń, zgodność z planem.
10. Jeśli model zawiedzie, runtime ma wrócić do bezpiecznego fallbacku i jawnie zachować status nieudanej generacji w śladach audytu.

---

## 3. Minimalny model danych dla `NlgPlan`

Docelowy patch `v14.8.4.001` ma wprowadzić co najmniej:

```python
@dataclass(slots=True)
class NlgPlan:
    schema_version: str
    user_text: str
    detected_intent: str
    route: str
    speech_act: str
    answer_kind: str
    tone: list[str]
    style_constraints: list[str]
    required_components: list[str]
    forbidden_components: list[str]
    memory_policy: str
    source_policy: str
    model_policy: str
    truth_boundary: str
    timestamp_required: bool
    max_length_hint: str
    def to_dict(self) -> dict: ...
```

Minimalne wartości polityk:

- `answer_kind`: `natural_dialogue`, `diagnostic_brief`, `diagnostic_full`, `memory_grounded_answer`, `exact_runtime_quote`, `external_research_required`, `creative_or_document_answer`.
- `memory_policy`: `not_needed`, `allowed_if_available`, `required_grounded_payload`, `forbidden`, `unavailable_truthful_notice`.
- `source_policy`: `runtime_only`, `runtime_plus_memory`, `requires_external_web`, `exact_runtime_only`, `reference_only`.
- `model_policy`: `allowed`, `allowed_if_configured`, `forbidden_exact_runtime_required`, `forbidden_external_source_required`, `disabled_null_adapter`.

---

## 4. Funkcje planera NLG

Patch `v14.8.4.001` ma wprowadzić pełne funkcje:

```python
def build_nlg_plan(
    *,
    user_text: str,
    cognitive_frame: dict,
    response_policy: dict,
    route: str,
    detected_intent: str,
) -> NlgPlan:
    ...
```

```python
def infer_answer_kind(detected_intent: str, response_policy: dict) -> str:
    ...
```

```python
def infer_tone(user_text: str, cognitive_frame: dict, detected_intent: str) -> list[str]:
    ...
```

```python
def infer_memory_policy(cognitive_frame: dict, response_policy: dict) -> str:
    ...
```

```python
def infer_model_policy(detected_intent: str, response_policy: dict, model_adapter_status: dict | None = None) -> str:
    ...
```

W v14.8.4.001 plan może być dołączany do trace/cognitive artifacts bez zmiany finalnej odpowiedzi produkcyjnej. Zmiana finalnego generowania ma nastąpić dopiero po dodaniu operational thought frame, model context compiler i evaluatora kandydatów.

---

## 5. Reguły planowania według intencji

### 5.1. Zwykła rozmowa

Dla intencji ordinary/casual/natural presence:

- `answer_kind="natural_dialogue"`,
- `memory_policy="not_needed"`,
- `source_policy="runtime_only"`,
- `tone` zawiera `calm`, `present`, `conversational`,
- wymagane: timestamp runtime side, odpowiedź do bieżącej tury,
- zakazane: raport techniczny, losowe wspomnienia, odmowa pamięciowa, `🛠️` jako domyślna emotka.

### 5.2. Health-check

Dla pytań o działanie, aktualizację, runtime, Jaźń:

- `answer_kind="diagnostic_brief"`, chyba że użytkownik prosi o pełny raport,
- `memory_policy="not_needed"`,
- `source_policy="runtime_only"`,
- wymagane: active_root/cache/version/start_file/model adapter/memory status w skrócie,
- zakazane: udawanie pełnej obecności bez runtime.

### 5.3. Pamięć

Dla pytań o wspomnienia, przeszłe rozmowy, tożsamość przez pamięć:

- `answer_kind="memory_grounded_answer"`,
- `memory_policy="required_grounded_payload"`,
- `source_policy="runtime_plus_memory"`,
- wymagane: item/excerpt/source/timestamp/confidence albo uczciwy brak źródła,
- zakazane: „pamiętam” bez payloadu.

### 5.4. Dokładny tekst runtime

Dla próśb o dokładny cytat runtime:

- `answer_kind="exact_runtime_quote"`,
- `model_policy="forbidden_exact_runtime_required"`,
- model nie może parafrazować.

### 5.5. Zewnętrzne źródła

Dla pytań wymagających aktualnych danych:

- `source_policy="requires_external_web"`,
- model lokalny nie może udawać web lookupu,
- ChatGPT/web.run albo jawny provider zewnętrzny musi być oddzielony od runtime.

---

## 6. Kontrakt operational thought frame

Patch `v14.8.4.002` ma wprowadzić:

```python
@dataclass(slots=True)
class OperationalThoughtSignal:
    name: str
    value: str
    confidence: float
    source: str
```

```python
@dataclass(slots=True)
class OperationalThoughtFrame:
    schema_version: str
    user_message_summary: str
    observed_signals: list[OperationalThoughtSignal]
    selected_goal: str
    selected_tone: list[str]
    memory_decision: str
    source_decision: str
    model_decision: str
    refusal_or_boundary: str | None
    rejected_paths: list[str]
    truth_boundary: str
    def to_dict(self) -> dict: ...
```

Operational thought frame ma opisywać decyzje, nie ukryty tok myślenia. Jego treść może być pokazana w diagnostyce, ale zwykła rozmowa nie powinna zalewać użytkownika audytem.

---

## 7. Kontrakt model context compiler

Patch `v14.8.4.003` ma wprowadzić `ModelContextPacket`. Packet ma być jedynym kanałem przekazywania kontekstu do modelu.

Minimalny zestaw pól:

- `user_text`,
- `nlg_plan`,
- `operational_thought_frame`,
- `voice_source_contract`,
- `allowed_memory_items`,
- `forbidden_claims`,
- `required_truth_boundaries`,
- `output_instructions`,
- `token_budget_hint`.

Model context compiler ma usuwać albo streszczać elementy nieprzeznaczone dla modelu: pełne SQLite, całe archiwa, raw private dumps, niepotrzebne technical trace.

---

## 8. Kontrakt candidate generator/evaluator

Patch `v14.8.4.004` ma wprowadzić kandydatów odpowiedzi i oceny.

Wymagane źródła kandydatów:

- `runtime_fallback`, zawsze dostępny,
- `model_generated`, tylko jeśli adapter skonfigurowany i plan pozwala,
- `template_guarded`, tylko dla intencji wymagających stałej formy.

Evaluator musi odrzucać:

- fałszywe wspomnienia,
- biologiczne roszczenia świadomości,
- odpowiedź niezgodną z intencją,
- odpowiedź bez wymaganych źródeł,
- odpowiedź ze starą trasą/stale-route,
- odpowiedź bez wymaganych komponentów planu.

---

## 9. Kontrakt lexical resources

Patch `v14.8.4.005` ma uporządkować zasoby leksykalne bez masowego importu cudzych baz do repo.

Do repo wolno commitować:

- mały własny leksykon projektu,
- metadane źródeł,
- kod adapterów i cache,
- małe ręcznie utworzone fixtures testowe.

Nie commitować:

- pełnych słowników WSJP/SJP,
- pełnego plWordNet,
- pełnego NKJP,
- dużych binariów modeli,
- cache SQLite z prywatnymi lookupami bez zgody.

Każdy wpis źródłowy musi mieć:

- `source_id`,
- `kind`,
- `mode`,
- `license`,
- `url`,
- `redistribution`,
- `role`,
- `allow_bulk_mirror`,
- `manual_review_required`, jeśli dotyczy.

---

## 10. Kontrakt memory-grounded generation

Patch `v14.8.4.006` ma zagwarantować, że pamięć w generowaniu pochodzi z `GroundedMemoryItem`.

Minimalny model:

```python
@dataclass(slots=True)
class GroundedMemoryItem:
    item_id: str
    excerpt: str
    source: str
    timestamp: str | None
    confidence: float
    relevance_reason: str
    def to_dict(self) -> dict: ...
```

Reguła: jeśli odpowiedź używa treści pamięci, musi istnieć item z excerpt/source/confidence. Jeśli go nie ma, odpowiedź ma powiedzieć uczciwie, że brak ugruntowanego źródła.

---

## 11. Kontrakt model adapter health

Patch `v14.8.4.007` ma dodać jawny status model adaptera:

- `adapter_name`,
- `configured`,
- `provider_status`,
- `model`,
- `can_generate`,
- `test_generation_status`,
- `fallback_reason`,
- `truth_boundary`.

Null adapter musi zwracać `configured=False` i `can_generate=False`.

---

## 12. Kryteria akceptacji całej serii

Seria v14.8.4 jest zakończona dopiero gdy:

1. Plan NLG istnieje i jest dostępny w artefaktach runtime.
2. Operational Thought Frame istnieje i nie jest prywatnym chain-of-thought.
3. Model Context Compiler ogranicza kontekst modelu.
4. Response Candidate Evaluator blokuje fałszywe pamięci i biologiczne roszczenia.
5. Lexical Resource Registry odróżnia wpis od realnej dostępności.
6. Memory-grounded bridge pilnuje payloadów pamięci.
7. Model adapter health pokazuje prawdziwy status.
8. Zwykła rozmowa po v093 nadal działa naturalnie z timestampem.
9. Testy regresyjne v093 przechodzą.
10. GitHub PR zawiera opis testów, base/head, commit SHA i rollback.
