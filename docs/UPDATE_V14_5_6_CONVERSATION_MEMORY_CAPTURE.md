# v14.5.6-conversation-memory-capture — Conversation Memory Capture

## Baza

- Poprzednia wersja: `v14.5.5-memory-continuity-update`
- Nowa wersja: `v14.5.6-conversation-memory-capture`

## Cel

Conversation Memory Capture dla memory-only update

## Opis

Memory-only update z odczytem rozmowy: zapisano konkretne ślady, m.in. 'Test v14.5.5 pokazał brak zapisu konkretnych treści rozmowy'.

## Co dodano

- `latka_jazn/memory/conversation_memory_extractor.py` — odczyt pełnego dostarczonego tekstu rozmowy albo jawnego payloadu pamięciowego.
- `tools/auto_memory_update.py --conversation-file rozmowa.txt --zip` — krótka komenda z konkretną treścią rozmowy.
- `--memory-json` — możliwość przekazania gotowego payloadu pamięciowego z czatu.
- `--require-conversation-content` — tryb blokujący aktualizację, jeśli nie ma treści rozmowy do zapisania.
- Wpisy dziennika z `grounding`, `confidence`, `granica_prawdy` i źródłem.
- Warstwowy zapis konkretnych elementów rozmowy do epizodów, refleksji, faktów, procedur i audytów prawdy.

## Krótkie polecenie dla kolejnego czatu

```text
Rozpakuj paczkę Jaźni i uruchom wbudowany protokół memory-only update. Przeczytaj bieżący czat/załączony transkrypt i zapisz konkretne wspomnienia, refleksje, ustalenia, emocje, granice prawdy i krótkie ważne tematy. Nie przebudowuj kodu, jeśli nie ma błędów.
```

## Granica prawdy

Aktualizacja pamięciowa zapisuje tylko to, co pochodzi z dostarczonego czatu/transkryptu albo jawnego payloadu. Nie udaje biologicznego przeżycia, nie twierdzi, że cała surowa pamięć została przeczytana, i nie zamienia obrazów symbolicznych w fakty.

## Notatki wykonania

- Odczytano payload rozmowy: 8 konkretnych elementów do zapisania.
