# Aktualizacja v14.5.24 — Runtime Bridge Export Hotfix

## Cel

Ta aktualizacja naprawia problem pustych fallbacków oraz dodaje możliwość generowania paczek do pobrania bez ręcznego wybierania plików.

## Najważniejsze zmiany

1. `latka_jazn/core/engine.py`
   - dodano `_fallback_diagnostics()`;
   - `_contextual_fallback()` nie zwraca już samej ogólnej odpowiedzi, tylko wskazuje pliki i funkcje do sprawdzenia;
   - `build_cognitive_frame()` zwraca pole `fallback_diagnostics`;
   - dodano komendy runtime: `/export_system`, `/export_memory`, `/export_full` oraz polskie warianty fraz.

2. `main.py`
   - zastąpiono ręczne parsowanie argumentów przez `argparse`;
   - dodano CLI: `--export-system`, `--export-memory`, `--export-full`, `--output`;
   - zachowano `--cognitive-frame`, `--chatgpt-frame`, `--brain-frame` i diagnostykę read-only.

3. `latka_jazn/tools/package_export.py`
   - nowy moduł eksportu ZIP;
   - tryby: `system`, `memory`, `full`;
   - raport obok paczki: `*.report.json`;
   - SHA-256, liczba plików, rozmiar ZIP i notatki diagnostyczne;
   - obsługa ZIP64 dla dużej pamięci;
   - brak dublowania `chat.html`, jeśli dostępne jest `chat.html.7z`.

4. `latka_jazn/core/clock.py`
   - `header()` używa lokalnego fallbacku, jeśli nie przekazano próbki czasu;
   - jawne sprawdzanie sieci pozostaje w `now(network_first=True)` i komendzie `/czas`.

5. `workspace_runtime/latka_jazn_v14_5_24.sqlite3`
   - aktywna baza runtime została przeniesiona z v14.5.23 i ma zaktualizowane metadane wersji.

## Komendy

```bash
python main.py --status-readonly
python main.py --cognitive-frame "Treść wiadomości"
python main.py --export-system
python main.py --export-memory
python main.py --export-full
python main.py --export-full --output exports/latka_full.zip
```

## Granica prawdy

Eksport full może zawierać `memory/raw/chat.html` i `memory/raw/chat.html.7z`, jeśli są obecne w aktywnej paczce. Eksport memory-only obejmuje pamięć i `workspace_runtime`, ale nie oznacza, że runtime działa jako stały proces w tle.

## Testy

Wynik kontroli po aktualizacji:

```text
41 passed in 17.54s
```
