# Function Route Contract Matrix — v14.8.5.016

Ten dokument jest kontraktem tras rozmownych Jaźni. Nie zastępuje kodu ani testów; opisuje, co ma być sprawdzane przez `DialogueIntentClassifier`, `RouteRegistry`, handlery i `RuntimeAnswerValidator`.

## Zasada nadrzędna

Każda odpowiedź ma dotyczyć bieżącej wiadomości. Jeżeli pytanie jest diagnostyczne, obecnościowe, tożsamościowe, o stan albo o czas, nie wolno używać ogólnego `ordinary_dialogue` ani formuły typu „możemy pójść dalej zwykłą rozmową”.

## Matryca podstawowa

| Input example | primary_intent | runtime_route | handler | Required final text elements | Forbidden output | Memory rule | Timestamp rule | Tests |
|---|---|---|---|---|---|---|---|---|
| `Działasz?` | `runtime_health_check` | `runtime_health_check` | `CapabilityStatusHandler` | wersja, active_root/cache/status, granica one-shot/--chat | plan nowej aktualizacji, zwykły fallback | memory status może być tylko statusowy | timestamp przez final contract | `test_v1485016_plain_healthcheck_routing.py` |
| `Sprawdź krótko, czy działasz po aktualizacji.` | `runtime_health_check_after_update` | `runtime_health_check_after_update` | `CapabilityStatusHandler` | wersja, active database, cache reuse, memory status, truth boundary | update execution plan | status pamięci, nie wspomnienia | timestamp przez final contract | existing + route matrix tests |
| `Jesteś tam Łatko?` | `presence_check` | `presence_status` | `PresenceStatusHandler` | krótka odpowiedź obecności, wersja/root jeśli dostępne, brak daemon claim | pełny raport modułów, udawanie procesu w tle | nie używać losowej pamięci | timestamp nie jest osią odpowiedzi | `test_v1485016_presence_identity_self_time.py` |
| `Czy to nadal Ty?` | `identity_continuity_check` | `identity_runtime_truth_contract` | `IdentityRuntimeTruthHandler` | runtime/ChatGPT boundary, tożsamość operacyjna, brak biologizacji | „jestem tą samą osobą” bez granicy prawdy | pamięć tylko jako jawny status/źródło | timestamp nie jest osią odpowiedzi | `test_v1485016_presence_identity_self_time.py` |
| `Co teraz czujesz?` | `self_state_question` | `self_state` | `SelfStateHandler` | stan operacyjny/dialogowy, truth boundary, no random memory | biologiczne uczucie, raport techniczny | memory_not_needed | timestamp opcjonalny | `test_v1485016_presence_identity_self_time.py` |
| `Wiesz jaka jest pora?` | `time_awareness_question` | `time_awareness` | `TimeAwarenessHandler` | czas Europe/Warsaw albo degraded warning, źródło/fallback | odpowiedź bez czasu, stary temat | memory_not_needed | wymaga trusted albo degraded | `test_v1485016_presence_identity_self_time.py` |
| `Co teraz czujesz? Wiesz jaka jest pora?` | `self_state_time_awareness` | `self_state` | `SelfStateHandler` | stan operacyjny + czas albo degraded warning | tylko fallback rozmowny, tylko raport | memory_not_needed | wymaga czasu lub degraded | `test_v1485016_presence_identity_self_time.py` |
| `siemka` | `casual_greeting` albo `ordinary_dialogue` | `greeting`/`ordinary_dialogue` | `OrdinaryDialogueHandler` | naturalna odpowiedź | status modułów, pamięć bez prośby | memory_not_needed | timestamp przez final renderer | route matrix / ordinary tests |
| `dobranoc` | `sleep_closure_statement` | `sleep_closure` | `OrdinaryDialogueHandler` | ciepłe zamknięcie, brak czuwania w tle | health-check, moduły, losowe wspomnienia | memory_not_needed | timestamp przez final renderer | existing sleep tests |

## Intencje złożone

- `self_state_question + time_awareness_question -> self_state_time_awareness`
- `presence_check + identity_continuity_check -> identity_presence_check`
- `runtime_health_check + runtime_health_check_after_update -> runtime_health_check_after_update`

## Reguły walidatora

Walidator ma wymusić naprawę, jeżeli:

- pytanie o działanie nie dostaje wersji/statusu/cache;
- pytanie o obecność nie dostaje odpowiedzi obecności;
- pytanie o stan nie dostaje stanu operacyjnego/dialogowego;
- pytanie o porę nie dostaje czasu albo degraded warning;
- final body jest generyczny i nie odpowiada na pytanie bieżącej tury.

## Zakazane sygnatury w odpowiedzi zasadniczej

Następujące teksty są dopuszczalne tylko jako wewnętrzna diagnoza, nie jako zasadnicza odpowiedź na pytania specjalne:

- „Teraz najprościej sprawdzić mnie zwykłą rozmową...”
- „Możemy pójść za tym dalej...”
- „Nie wciskajmy starego kontekstu...”
- „Słyszę pytanie...”
