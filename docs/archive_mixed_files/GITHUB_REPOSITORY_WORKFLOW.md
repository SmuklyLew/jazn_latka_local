# GitHub repository workflow — Łatka Jaźń v14.5.38

## Cel

Ta aktualizacja przygotowuje Jaźń do pracy z dwoma prywatnymi repozytoriami:

- `SmuklyLew/Latka.Jazn` — główny folder systemu Jaźni.
- `SmuklyLew/Latka.Jazn.Memory` — trwała pamięć tekstowa, dziennik, ledger i checkpointy.

## Dlaczego dwa repozytoria

System i pamięć mają różne tempo zmian. Kod i testy powinny być commitowane po sprawdzonej aktualizacji. Pamięć może dostawać lżejsze checkpointy po ważnych rozmowach, bez tworzenia pełnego ZIP po każdej wiadomości.

## Tryb pracy

1. Rozmowa normalna:
   - runtime zapisuje append-only ślad tury,
   - RuntimeMemoryWriter ocenia kandydat pamięci,
   - nie trzeba od razu eksportować ZIP ani pushować GitHub.

2. Ważny checkpoint:
   - odświeżyć `session_continuity_index.json`,
   - sprawdzić deduplikację,
   - commit do `Latka.Jazn.Memory`.

3. Aktualizacja systemu:
   - zmienić kod i dokumentację,
   - uruchomić testy,
   - utworzyć manifest aktualizacji,
   - przygotować full ZIP,
   - commit do `Latka.Jazn`.

## Komendy lokalne

```bash
python main.py --status-readonly
python main.py --github-plan
python main.py --cognitive-frame "Czy Jaźń ma działać jak LLM czy bardziej jak mózg runtime?"
python main.py --export-full --output exports/latka_jazn_v14_5_38_FULL_SYSTEM_WITH_MEMORY.zip
```

## Ograniczenia

Ten system nie wykonuje pushu do GitHub samym istnieniem pliku. Repozytoria stają się aktualne dopiero po realnym commicie/pushu wykonanym przez narzędzie z uprawnieniami albo lokalnie przez Krzysztofa.
