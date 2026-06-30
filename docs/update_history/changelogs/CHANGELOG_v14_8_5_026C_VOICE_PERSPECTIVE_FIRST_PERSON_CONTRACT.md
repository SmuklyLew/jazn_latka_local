# v14.8.5.026C - voice-perspective-first-person-contract

## Zakres

- Normalizuje metadane wydania po hotfixie perspektywy głosu.
- Ustawia aktywną wersję runtime na `v14.8.5.026C`.
- Utrzymuje pełną nazwę pakietu jako `v14.8.5.026C-voice-perspective-first-person-contract`.
- Wzmacnia kontrakt pierwszoosobowego głosu Łatki dodany w poprzednim commicie.
- Poprawia `tools/refresh_current_manifest.py`, żeby `memory/**` nie trafiało do statycznego `MANIFEST_CURRENT.json`.

## Granica prawdy

To nie jest awans do `v14.8.6.0`. Etapy planu 14.8.6.0 pozostają osobnym zakresem. Ten hotfix porządkuje wersję po `026B` i po kontrakcie głosu `026C`.

## Testy minimalne

```powershell
python -X utf8 tools/refresh_current_manifest.py
pytest -q tests/test_v1485021a_release_metadata_manifest_hygiene.py
pytest -q tests/test_v1485018_daemon_time_presence_voice.py::test_voice_perspective_feedback_routes_to_diagnostic_not_memory tests/test_v1485018_daemon_time_presence_voice.py::test_self_memory_recall_visible_intro_uses_first_person_voice
```
