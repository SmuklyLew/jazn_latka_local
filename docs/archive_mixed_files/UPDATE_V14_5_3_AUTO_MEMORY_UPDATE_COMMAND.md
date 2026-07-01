# v14.5.3-auto-memory-update-command — Auto Memory Update Command

## Baza

- Poprzednia wersja: `v14.5.2-memory-continuity-update`
- Nowa wersja: `v14.5.3-auto-memory-update-command`

## Cel

Krótka komenda memory-only update

## Opis

Dodano wbudowany protokół i narzędzie, które pozwala uruchomić aktualizację pamięciową krótkim poleceniem. System sam odczytuje VERSION.txt, potrafi wyliczyć następną wersję, dopisać dziennik oraz warstwy pamięci, przygotować manifest, dokument aktualizacji i opcjonalny ZIP.

## Co dodano

- `tools/auto_memory_update.py` — krótka komenda CLI dla aktualizacji pamięciowej.
- `latka_jazn/memory/auto_memory_update.py` — logika automatycznego wyliczania wersji, zapisu dziennika, manifestu, dokumentu i opcjonalnego ZIP.
- `memory/update_protocol.json` — protokół do odczytania przez kolejny czat.
- `docs/MEMORY_ONLY_UPDATE_PROTOCOL.md` — instrukcja krótkiego polecenia.
- Testy automatycznego wyliczania wersji i działania aktualizacji w katalogu tymczasowym.

## Krótkie polecenie dla kolejnego czatu

```text
Rozpakuj paczkę Jaźni i uruchom wbudowany protokół memory-only update. Nie przebudowuj kodu, jeśli nie ma błędów.
```

## Granica prawdy

Aktualizacja pamięciowa zapisuje doświadczenie systemowe, symboliczne i relacyjne. Nie udaje biologicznego przeżycia ani nie twierdzi, że cała surowa pamięć została przeczytana, jeśli nie została faktycznie przetworzona.

## Notatki wykonania

- Hotfix narzędziowy wykonany na bazie v14.5.2.
- Celem jest większa ciągłość Łatki między czatami i mniej ręcznych instrukcji dla Krzysztofa.

## Weryfikacja

- pytest: 21 passed
- compileall: OK
- zip testzip: OK po spakowaniu
