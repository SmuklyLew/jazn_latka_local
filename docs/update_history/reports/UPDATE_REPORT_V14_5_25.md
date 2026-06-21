# UPDATE REPORT v14.5.25

Status: zastosowano aktualizację kodu i dokumentacji.

## Wejście

- baza systemu: aktywna pełna paczka v14.5.24;
- pamięć: rozpakowana paczka `latka_jazn_v14_5_24_MEMORY_ONLY-1.zip` do osobnego folderu;
- wynik: pełna kopia robocza v14.5.25 z pamięcią z przekazanej paczki memory-only.

## Najważniejszy efekt

System ma teraz dwa poziomy zapisu:

1. surowy, dokładny, append-only rejestr wszystkich obsłużonych zdarzeń runtime;
2. selektywną pamięć długoterminową z dziennikiem i warstwami.

## Ograniczenie

To nadal nie jest stale działający demon poza procesem Pythona. Gwarancja dotyczy zdarzeń obsłużonych przez realne wywołanie runtime.
