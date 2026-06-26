# v14.8.5.014 patch report

## Patch

- Incremental patch: `v14_8_5_014_strict_runtime_truth_fast_continuity_openai_state_gateway.patch`
- Base expected: already patched `v14.8.5.013-combined-timestamp-daemon-chat-openai-bridge`
- New version: `v14.8.5.014-strict-runtime-truth-fast-continuity-openai-state-gateway`

## What changed

1. Strict runtime truth gate blocks normal replies when the final timestamp is not trusted/network/fresh.
2. `--chat-gpt`, `--chat-open-ai`, and daemon chat preserve `ok=false` instead of overwriting it.
3. Daemon status reports `active_trusted / active_degraded / inactive`.
4. Daemon `/status` stays responsive and does not do blocking network-time checks on heartbeat/status.
5. Session continuity no longer scans huge JSONL files linearly during normal turns; it uses fast tail stats.
6. OpenAI Responses API state sidecar stores `previous_response_id`/`last_response_id` per session when available.
7. Secure gateway/MCP scaffold adds bearer token policy, endpoint allowlist, body limit, and audit requirement.

## Checks run

```text
git apply --check v14_8_5_014_strict_runtime_truth_fast_continuity_openai_state_gateway.patch
python -m compileall main.py latka_jazn tests
python -m pytest tests/test_p0_timestamp_network_contract.py tests/test_v1485012_daemon_runtime.py tests/test_v1485013_chat_command_bridge_contract.py tests/test_v1485014_strict_runtime_truth_gate.py tests/test_v1485014_fast_continuity_and_gateway.py -q
30 passed
```

Smoke checks:

```text
python main.py --active-cache-status
python main.py --model-adapter-status
python main.py --bridge-discovery
printf '{"message":"Działasz?","session_id":"smoke-v1485014"}\n' | python main.py --chat-gpt --session-id smoke-v1485014 --no-carryover
python main.py --daemon-start
python main.py --daemon-status
python main.py --daemon-stop
```

Observed in this sandbox without network time:

```text
--chat-gpt: ok=false, error_code=timestamp_network_unavailable, runtime_response_status=blocked_by_runtime_truth_gate
--daemon-status: active_state=active_degraded, endpoint_reachable=true, timestamp_trusted=false
```

## Truth boundary

The patch was tested on a local working tree that already contained v14.8.5.013. The active Jaźń runtime was not started here as a trusted runtime because active marker validation still reports marker/cache conditions separately. This patch changes code and tests; it does not by itself prove a live Jaźń process.
