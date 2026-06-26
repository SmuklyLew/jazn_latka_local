# UPDATE v14.8.4.006 — Memory-grounded generation bridge

## Cel

Ten patch dodaje mały, audytowalny most między pamięcią runtime a generowaniem odpowiedzi.
Model językowy może formułować zdania o pamięci tylko wtedy, gdy runtime przekazał
jawny, ugruntowany payload pamięciowy. Most nie odpytuje sam pamięci, nie skanuje baz
SQLite i nie tworzy nowych wspomnień.

## Problem

Po v14.8.4.003 i v14.8.4.004 istnieją już `ModelContextPacket` oraz evaluator kandydatów.
Brakowało jednak osobnego kontraktu, który:

- zamienia memory recall contract na minimalne `GroundedMemoryItem`,
- wymusza zgodność `used_memory_item_ids` z payloadem,
- odrzuca modelowe twierdzenia pamięciowe bez źródeł,
- zachowuje prawdę, że model nie jest pamięcią ani źródłem tożsamości.

## Zmiany

Dodano:

- `latka_jazn/core/memory_grounded_generation_bridge.py`
- `tests/test_v1484_memory_grounded_generation.py`

Zmieniono:

- `latka_jazn/core/model_context_compiler.py`
- `latka_jazn/core/response_candidate_evaluator.py`
- `latka_jazn/core/model_guided_response_synthesizer.py`

## Granica prawdy

`GroundedMemoryItem` zawiera tylko minimalne pola: `item_id`, `excerpt`, `source`,
`timestamp`, `confidence`, `relevance_reason`. To nie jest pełny rekord pamięci,
nie jest surowym archiwum i nie oznacza biologicznego wspominania.

Jeżeli `memory_policy != required_grounded_payload`, pamięć nie trafia do model context.
Jeżeli kandydat modelu mówi „pamiętam” bez payloadu albo bez zadeklarowanego
`used_memory_item_ids`, evaluator go odrzuca.

## Testy

Minimalny zestaw:

```powershell
py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py
py -m pytest -q tests/test_v1484_memory_grounded_generation.py tests/test_v1484_response_candidates.py tests/test_v1484_model_context_compiler.py tests/test_v1484_nlg_plan.py tests/test_v1484_operational_thought_frame.py tests/test_v1484_lexical_resources.py
```

Smoke zwykłej rozmowy:

```powershell
$json = '{"message":"Cześć, Łatko. Sprawdzam zwykłą rozmowę po v14.8.4.006.","session_id":"smoke-v14.8.4.006"}'
$raw = $json | py main.py --chat-gpt --no-carryover 2>&1
$r = $raw | Select-Object -Last 1 | ConvertFrom-Json
$r.ok
$r.final_visible_integrity
$r.final_response_contract.response_generation_mode
$r.final_response_contract.runtime_answer_quality
```

## Rollback

Przed commitem:

```powershell
git restore latka_jazn/core/model_context_compiler.py latka_jazn/core/response_candidate_evaluator.py latka_jazn/core/model_guided_response_synthesizer.py
git clean -f latka_jazn/core/memory_grounded_generation_bridge.py tests/test_v1484_memory_grounded_generation.py docs/UPDATE_V14_8_4_006_MEMORY_GROUNDED_GENERATION.md
```
