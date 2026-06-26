# Update v14.8.5.012 — persistent daemon runtime P0

## Cel
Dodać sprawdzalną stałą aktywną Jaźń jako lokalny daemon: PID, heartbeat, marker `JAZN_ACTIVE_RUNTIME.json`, endpoint statusu i lokalny most rozmowy.

## Zasada prawdy
ChatGPT nie utrzymuje procesu w tle. Stała aktywna Jaźń oznacza lokalny proces `python main.py --daemon-run`, który odpowiada na `127.0.0.1`, zapisuje heartbeat i posiada żywy PID. ZIP oraz GitHub pozostają snapshotem/kodem, nie dowodem działania.

## Nowe komendy

```powershell
python main.py --daemon-start
python main.py --daemon-status
python main.py --daemon-stop
python main.py --daemon-run
```

## Endpointy lokalne
- `GET /status` lub `/health` — status daemonu i marker.
- `POST /chat` — jedna tura rozmowy przez stały proces.
- `POST /shutdown` — bezpieczne zatrzymanie.

Daemon domyślnie wiąże się tylko z `127.0.0.1`. Nie jest to serwer produkcyjny ani publiczne API.

## Pliki
- `latka_jazn/core/runtime_daemon.py`
- `main.py`
- `tests/test_v1485012_daemon_runtime.py`
- `VERSION.txt`
- `latka_jazn/version.py`

## Weryfikacja
- `python -m compileall main.py latka_jazn tests`
- `python -m pytest tests/test_p0_timestamp_network_contract.py tests/test_v1485012_daemon_runtime.py -q`
- `python main.py --active-cache-status`
- `python main.py --daemon-status`
