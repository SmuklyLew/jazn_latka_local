# v14.8.5.001 — current-turn grounding i carryover guard

Cel: zablokować przenoszenie starego kontekstu i starych szablonów do bieżącej tury. Patch dodaje `TurnContextResolver` oraz `CurrentTurnGrounding`, a walidator odpowiedzi używa nowej kontroli przed pokazaniem tekstu użytkownikowi.

## Zakres

- `TurnContextResolver` rozróżnia krótką kontynuację od nowego tematu.
- Poprzednia trasa aktualizacji nie może przejść do zwykłego powitania, pytania „co tam?” ani health-checka.
- `CurrentTurnGrounding` wykrywa stale-version output, stale-update template, zwykły meta-leak i nieproszoną pamięć.
- `RuntimeAnswerValidator` dołącza raport current-turn grounding do walidacji.

## Testy

```powershell
py -m compileall -q latka_jazn main.py
py -m pytest -q tests/test_v1485_001_current_turn_grounding.py
py -m pytest -q tests/test_v1485_000_version_template_reconciliation.py
```
