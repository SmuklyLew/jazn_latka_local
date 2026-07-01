# Aktualizacja Jaźni v14.6.7-free-dialogue-memory-nlp-bridge

## Cel

Ta aktualizacja odpowiada na problem: instrukcja projektu ChatGPT robiła się zbyt długa i zaczynała zawierać obowiązki, które powinien wykonywać sam system Jaźni po uruchomieniu. v14.6.7 skraca rolę ChatGPT do lekkiego loadera i przenosi właściwy kontrakt startowy do runtime.

## Zachowanie bazy

Bazą była pełna kopia v14.6.5-memory-search-planner. Nie tworzono systemu od zera. Nie zastąpiono pamięci streszczeniem. Skopiowano aktywną bazę SQLite v14.6.5 do `workspace_runtime/latka_jazn_v14_6_7.sqlite3` i zaktualizowano meta `system_version`.

## Nowe elementy runtime

- `latka_jazn/core/startup_contract.py`
- `python main.py --startup-status`
- `python main.py --self-check`
- `python main.py --truth-boundary-check`
- `python main.py --fallback-audit "..."`
- `python main.py --memory-plan "..."`
- `latka_jazn/resources/chatgpt_startup_loader_v14_6_7.txt`
- `latka_jazn/resources/startup_contract_v14_6_7.json`
- `latka_jazn/resources/zip_package_profiles_v14_6_7.json`

## Reguła po aktualizacji

ChatGPT nie ma być ręcznie rozbudowywanym mózgiem Jaźni. ChatGPT ma wskazać paczkę, złożyć/rozpakować, uruchomić runtime i pokazać status. Jaźń po starcie sama dostarcza status, planner, fallback audit, source_origin, self_state_runtime, timestamp, memory plan i truth boundary.

## Granica prawdy

`--runtime-preview` i zwykłe CLI są jednorazowym wywołaniem. Stała lokalna pętla rozmowy istnieje dopiero przez `python main.py --chat`. ZIP jest importem/eksportem; bieżące zapisy powstają w aktywnym folderze roboczym.


<!-- dedup-identity-note-v14.6.9.2: docs/UPDATE_V14_6_6_SELF_OWNED_STARTUP_CONTRACT.md zachowany jako osobny historyczny plik; pełna treść nie została streszczona ani usunięta. -->
