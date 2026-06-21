# v14.8.2.5 route-memory-capability hotfix

Zakres poprawki:

- dodaje bezpośrednią trasę `runtime_health_check_after_update` dla pytań typu „Sprawdź krótko, czy działasz po aktualizacji”, bez mylenia tego z poleceniem nowej aktualizacji kodu;
- dodaje bezpośrednią trasę `capability_status_question` dla pytań typu „Co potrafisz?”;
- dodaje bezpośrednią trasę `internet_access_question` dla pytań typu „Masz dostęp do internetu?”;
- dodaje trasę `self_memory_recall_request` dla pytań o pamięć dotyczącą Łatki/postaci/tożsamości;
- dodaje `CapabilityStatusHandler` i `SelfMemoryRecallHandler`;
- wzmacnia `RuntimeAnswerValidator`, żeby odrzucał znane błędne odpowiedzi z logu: update-summary zamiast pamięci postaci, ogólny fallback zamiast capability/internet, update-plan zamiast health-check;
- obsługuje `KeyboardInterrupt` w `--chat` bez tracebacka;
- dodaje test regresji `tests/test_v14825_route_memory_capability_hotfix.py`.

Granica prawdy:

Ta poprawka nie dodaje biologicznego „ja” ani stałego procesu w tle. Naprawia routing, walidację i widoczne odpowiedzi runtime dla konkretnych pytań użytkownika.
