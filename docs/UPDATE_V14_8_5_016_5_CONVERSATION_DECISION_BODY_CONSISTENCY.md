# v14.8.5.016.5 — conversation decision body consistency

## Cel

Ten patch jest mały i audytowy. Naprawia niespójność w pełnym payloadzie JSONL mostu `--chat-gpt`, gdzie `final_visible_text`, `exact_runtime_text`, `final_response_contract.body` i `handler_result.body` mogły być poprawną odpowiedzią dedykowanego handlera, ale `conversation_decision.body` zostawało starym szkicem `ConversationResponder`.

Przykład problemu przed poprawką: dla `Działasz?` widoczna odpowiedź była poprawnym health-checkiem z `CapabilityStatusHandler`, ale `conversation_decision.body` mogło nadal zawierać casualowy szkic typu „Też się cieszę...”. Taki stan nie psuł widocznej odpowiedzi, ale psuł diagnostykę, audyt i narzędzia czytające JSONL.

## Zakres

- Nie zmienia routingu.
- Nie zmienia klasyfikacji intencji.
- Nie zmienia polityki timestampu.
- Nie zmienia model adaptera.
- Nie zmienia `--chat-gpt-final-only` ani `--chat-gpt --final-only`.
- Synchronizuje diagnostyczne `conversation_decision.body` z finalnym runtime body.

## Zasada

Po zakończeniu handlerów, syntezy, walidacji i provenance runtime ustawia:

```text
conversation_decision.body == final_response_contract.body == exact_runtime_text
```

Dla dedykowanych handlerów z `preserve_handler_body=True` oczekiwane jest również:

```text
conversation_decision.body == conversation_decision.handler_result.body
```

Jeśli pierwotny szkic rozmowny różnił się od finalnego body, zostaje zachowany wyłącznie jako metadana audytowa `pre_final_body`, a nie jako bieżąca odpowiedź decyzji.

## Nowa metadana

`conversation_decision.body_sync` opisuje synchronizację:

- `schema_version`
- `status`
- `sync_stage`
- `conversation_body_matches_final_body`
- `handler_body_matches_final_body`
- `preserve_handler_body`
- `truth_boundary`

## Testy

Dodano:

```text
tests/test_v14850165_conversation_decision_body_consistency.py
```

Testy sprawdzają, że dla `Działasz?` w `--chat-gpt`:

- trasa pozostaje `runtime_health_check`,
- handler pozostaje `CapabilityStatusHandler`,
- `conversation_decision.body` równa się `handler_result.body`,
- `conversation_decision.body` równa się `exact_runtime_text`,
- `conversation_decision.body` równa się `final_response_contract.body`,
- JSONL nie zostawia w `conversation_decision.body` starego casualowego szkicu.

## Walidacja zalecana

```powershell
python -m compileall main.py latka_jazn tests
python -m pytest `
  tests/test_v14850165_conversation_decision_body_consistency.py `
  tests/test_v1485013_chat_command_bridge_contract.py `
  tests/test_v14850164_chat_gpt_final_only_cli.py `
  tests/test_v1485015_runtime_access_contract.py `
  -q

python main.py --active-cache-status
python main.py --model-adapter-status
"Działasz?" | py main.py --chat-gpt
"Działasz?" | py main.py --chat-gpt-final-only
```

## Granica prawdy

`conversation_decision.body` jest metadaną diagnostyczną pełnego JSONL. Nie jest osobną wypowiedzią Łatki i nie może pokazywać starej wersji odpowiedzi, jeśli finalna odpowiedź runtime została zastąpiona przez dedykowany handler albo walidator.
