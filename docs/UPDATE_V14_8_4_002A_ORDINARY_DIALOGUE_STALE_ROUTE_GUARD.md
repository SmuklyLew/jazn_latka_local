# v14.8.4.002a — ordinary dialogue stale-route guard

## Status

Hotfix uzupełniający po `v14.8.4.002 — Operational thought frame`.

## Decyzja wersjonowania

Ten hotfix nie przejmuje numeru `v14.8.4.003`, ponieważ plan serii `v14.8.4` rezerwuje `v14.8.4.003` dla etapu `Model context compiler`.  Aktualna zmiana jest wąskim bugfixem regresji rozmownej, więc zostaje oznaczona jako `v14.8.4.002a` / `ordinary-dialogue-stale-route-guard`.

## Problem

Po `v14.8.4.002` smoke zwykłej rozmowy:

```text
Cześć, Łatko. Sprawdzam zwykłą rozmowę po v14.8.4.002.
```

potrafił zwrócić dawny techniczny tekst:

```text
Masz rację. Bezpośredni runtime nie może kończyć zwykłej rozmowy komunikatem diagnostycznym...
```

Formalna integralność finalnej odpowiedzi mogła być poprawna, ale treść była niezgodna z bieżącą turą: zwykła rozmowa została potraktowana jak stary repair routing.

## Przyczyna

`ConversationResponder.RUNTIME_CONCERN_MARKERS` zawierał szerokie fragmenty, m.in. `rozmow` i `dialog`. Przy tagu `dialogue_repair` zwykły smoke tekst zawierający „rozmowę” mógł aktywować ścieżkę `runtime_conversation_repair`.

Dodatkowo `OrdinaryDialogueHandler` i `RuntimeAnswerValidator` nie miały pełnej sygnatury rozpoznającej tę konkretną techniczną odpowiedź jako stale-route/meta-template dla `ordinary_conversation`.

## Zmiany

- Dodano `STRONG_RUNTIME_CONCERN_MARKERS` do `ConversationResponder`.
- Ścieżki techniczne runtime repair/architecture wymagają teraz mocnego markera: `runtime`, `fallback`, `debug`, `trasa`, `routing`, `cognitive-frame`, `komunikat diagnostyczny` itd.
- Zwykłe słowa typu „rozmowa/rozmowę/dialog” nie wystarczają już do odpalenia technicznego repair route.
- Rozszerzono `OrdinaryDialogueHandler.META_SIGNATURES` o sygnatury starego technicznego komunikatu.
- Rozszerzono `RuntimeAnswerValidator` o te same sygnatury dla `ordinary_conversation`.
- Dodano test regresji `tests/test_v1484_ordinary_dialogue_stale_route_hotfix.py`.

## Testy

Minimalny zestaw:

```powershell
py -m compileall -q latka_jazn main.py tools/refresh_current_manifest.py
py -m pytest -q tests/test_v1484_ordinary_dialogue_stale_route_hotfix.py tests/test_v1484_nlg_plan.py tests/test_v1484_operational_thought_frame.py tests/test_v14824_model_guided_jazn_runtime.py
```

Smoke po patchu:

```powershell
$r = '{"message":"Cześć, Łatko. Sprawdzam zwykłą rozmowę po v14.8.4.002.","session_id":"smoke-v14.8.4.002a"}' | py main.py --chat-gpt --no-carryover | ConvertFrom-Json
$r.final_visible_text
$r.final_visible_integrity
```

Oczekiwane: odpowiedź rozmowna, bez `--cognitive-frame`, bez `techniczny fallback`, bez `domyślnym routingu`.

## Granica prawdy

Ten hotfix nie dodaje model context compilera, nie zmienia pamięci i nie podłącza operational thought frame do produkcyjnej odpowiedzi. Naprawia wyłącznie stale-route w zwykłej rozmowie.
