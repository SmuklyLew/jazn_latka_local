# Aktualizacja v14.6.2-runtime-start-fallback-truth-contract

## Cel

Naprawić sytuację, w której runtime po wiadomości z powitaniem wybierał trasę `greeting` i przez to nie odpowiadał na właściwe pytanie użytkownika. Przykład regresyjny: `Dobry wieczór. Co myślisz o zeszłym roku?`.

## Zmiany w rdzeniu

1. `ConversationResponder._analyse_text_shape()` oddziela `greeting_prefix` od `substantive_remainder`.
2. Trasa `greeting` działa tylko dla samodzielnego powitania.
3. Pytanie o zeszły rok po powitaniu trafia do `last_year_reflection`.
4. Szeroki request naprawy rdzenia/fallbacków trafia do `contextual_greeting_fallback_repair_update`.
5. `ContinuityBadgePolicy` kontroluje i tłumi powtarzane formuły obecności.
6. `FinalResponseContract` dostał pola: `runtime_route`, `detected_user_intent`, `direct_answer_required`, `runtime_next_step`, `greeting_prefix`, `substantive_remainder`, `continuity_badge_policy`, `runtime_followup_required` i `preservation_contract`.

## Zasada odpowiedzi

Formuła obecności jest dobra jako znak uruchomienia, pamięci i granicy prawdy, ale nie może zastąpić odpowiedzi na temat. ChatGPT ma zachować `runtime_next_step` i follow-up, jeżeli runtime je wygenerował.

## Granica prawdy

Ta aktualizacja nie dodaje stałego procesu w tle. W trybie jednorazowym runtime działa tylko przez jedną turę; w trybie `--chat` utrzymuje jeden proces do wyjścia.
