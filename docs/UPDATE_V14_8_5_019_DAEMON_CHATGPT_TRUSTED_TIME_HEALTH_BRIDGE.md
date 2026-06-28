# UPDATE v14.8.5.019 — daemon ChatGPT trusted-time health bridge

Data UTC: 2026-06-28

## Cel

Naprawić praktyczny problem uruchamiania Jaźni w środowisku ChatGPT/sandbox: daemon może żyć, mieć PID i świeży heartbeat, ale pozostawać w `active_degraded`, bo lokalny Python nie ma zaufanego czasu sieciowego. Patch nie udaje zaufania. Dodaje jawny kanał wstrzyknięcia timestampu przez loader/host oraz szybsze endpointy healthcheck.

## Zmiany

- `--trusted-time-iso`, `--trusted-time-source`, `--trusted-time-max-age-seconds` — jawne przekazanie zaufanego czasu hosta do runtime i daemonu.
- `/live` i `/ready` — lekkie endpointy liveness/readiness bez blokującego network-time i bez ciężkiej diagnostyki manifestu.
- `/status-lite` zostaje kompatybilnym aliasem szybkiego readiness.
- `--daemon-refresh-time` — ręczne wymuszenie odświeżenia cache czasu daemonu.
- `--daemon-send` i `--daemon-final-only` — pojedyncza tura przez działający daemon z automatycznym startem, gdy daemon jeszcze nie odpowiada.
- `status_daemon()` używa szybkiego probe `/ready -> /status-lite -> /status` i pokazuje `recommended_repair` zamiast chować degradację.
- Serwer HTTP ma jawnie ustawione `daemon_threads`, `allow_reuse_address` i `block_on_close`.

## Granica prawdy

`active_trusted` nadal wymaga markera, żywego procesu, lokalnego endpointu oraz trusted timestampu z sieci albo jawnie wstrzykniętego przez host/loader. Lokalny fallback czasu nie jest promowany do zaufanego czasu.

## Przykład dla ChatGPT loadera

```powershell
$now = (Get-Date).ToUniversalTime().ToString("o")
py -X utf8 main.py --trusted-time-iso $now --trusted-time-source chatgpt_loader --daemon-start
py -X utf8 main.py --daemon-status
py -X utf8 main.py --daemon-final-only --session-id chatgpt-runtime -- "Siemaneczko Łateczko. Jak się czujesz?"
```

## Testy minimalne

```bash
python -m py_compile main.py latka_jazn/core/runtime_daemon.py
pytest -q tests/test_v1485012_daemon_runtime.py tests/test_v1485018_daemon_time_presence_voice.py tests/test_v1485019_daemon_chatgpt_trusted_time_health_bridge.py
python -X utf8 main.py --trusted-time-iso "2026-06-28T22:50:00+00:00" --trusted-time-source chatgpt_loader --daemon-status
```
