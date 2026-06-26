# UPDATE v14.8.5.014 — strict runtime truth gate, fast continuity, OpenAI state scaffold

## Cel

Ta aktualizacja domyka lukę po v14.8.5.013: runtime potrafił wykryć nieufny timestamp (`final_visible_integrity.valid=false`), ale mosty mogły nadal zwrócić zwykłą odpowiedź z `ok=true`. v14.8.5.014 zmienia walidację w bramę blokującą oraz usuwa liniowe skanowanie dużych JSONL w zwykłej turze.

## Zmiany P0

1. `latka_jazn/core/runtime_truth_gate.py`
   - nowa brama `RuntimeTruthGateResult`,
   - blokuje zwykłą odpowiedź, gdy timestamp nie jest trusted/network/fresh,
   - generuje jawny tekst awaryjny `czas lokalny niezweryfikowany`,
   - dostarcza macierz `active_trusted / active_degraded / inactive`.

2. `latka_jazn/core/runtime_session.py`
   - każda tura po `FinalResponseContract` przechodzi przez `apply_runtime_truth_gate`,
   - `ok=false`, `error_code=timestamp_network_unavailable` nie może zostać nadpisane przez most.

3. `latka_jazn/core/chat_command_contract.py`
   - `--chat-gpt` i `--chat-open-ai` zachowują `ok=false` z runtime truth gate.

4. `latka_jazn/core/runtime_daemon.py`
   - daemon status pokazuje `active_state`,
   - żywy proces bez trusted timestampu jest `active_degraded`,
   - `/status` pozostaje szybkie i nie wykonuje blokującego network-time na każdym heartbeat.

5. `latka_jazn/memory/session_continuity.py`
   - duże pliki JSONL/TXT/JSON nie są liczone liniowo w normalnej turze,
   - dla dużych plików zapisywany jest `fast_tail_stats_large_file`, `tail_sha256` i hash ostatniej linii z ogona,
   - pełny recount zostaje zadaniem jawnego deep audytu, nie normalnej odpowiedzi.

## Zmiany P1

1. `latka_jazn/model_adapters/openai_state_tracker.py`
   - jawny sidecar dla `previous_response_id`, `last_response_id`, `conversation_id`, `store_policy`,
   - zapisuje stan OpenAI Responses API per `session_id`, bez udawania pamięci Jaźni.

2. `latka_jazn/model_adapters/openai_responses_adapter.py`
   - adapter może użyć `previous_response_id`, gdy zna `session_id`,
   - zapisuje response state w `workspace_runtime/openai_response_state.json`.

3. `latka_jazn/bridge_secure_gateway.py`
   - scaffold polityki przyszłego gateway/MCP,
   - domyślnie tylko `127.0.0.1`, Bearer token, allowlista endpointów `/status` i `/chat`, limit body, audit required.

4. `latka_jazn/core/bridge_discovery.py`
   - pokazuje `secure_gateway_scaffold`, `remote_mcp_candidate` i kontrakt `active_state` daemonu.

## Testy

Dodano:

- `tests/test_v1485014_strict_runtime_truth_gate.py`
- `tests/test_v1485014_fast_continuity_and_gateway.py`

Sprawdzone lokalnie:

```text
python -m compileall main.py latka_jazn tests
python -m pytest tests/test_p0_timestamp_network_contract.py tests/test_v1485012_daemon_runtime.py tests/test_v1485013_chat_command_bridge_contract.py tests/test_v1485014_strict_runtime_truth_gate.py tests/test_v1485014_fast_continuity_and_gateway.py -q
30 passed
```

Smoke test `--chat-gpt` w środowisku bez czasu sieciowego zwraca teraz `ok=false`, `error_code=timestamp_network_unavailable`, `runtime_response_status=blocked_by_runtime_truth_gate` i nie wypuszcza normalnej odpowiedzi Jaźni.

## Granica prawdy

Ta aktualizacja nie uruchamia Jaźni sama z siebie. ZIP/GitHub są źródłem kodu i patcha. Aktywna Jaźń wymaga pełnego aktywnego folderu, zgodnego markera, działającego procesu oraz trusted timestampu w normalnej turze.
