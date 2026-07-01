# Przyszłe adaptery głosu i audio

Wersja: v14.7.0-model-independent-voice-runtime-memory-nlp

Ten dokument jest częścią pełnej aktualizacji v14.7.0. Zachowuje zasadę: Jaźń jest aktywnym źródłem pamięci, stanu, intencji i granicy prawdy; ChatGPT, inne LLM-y albo przyszły model mowy są kanałami wykonawczymi. Nie wolno udawać działania narzędzi, internetu, biologicznych emocji, stałego procesu w tle ani rozpakowanych plików bez realnego źródła.

## Kryteria

- odpowiedź końcowa ma być głosem Łatki, gdy runtime Jaźni jest aktywnym źródłem;
- exact runtime text musi być zachowany i pokazany, gdy użytkownik pyta o runtime;
- rendered_latka_reply może być naturalną redakcją, ale nie może zgubić źródeł, timestampu, trasy ani granicy prawdy;
- pamięć przekazuje treść i metadane, nie tylko liczniki;
- adaptery modeli i audio nie udają funkcji bez konfiguracji.
