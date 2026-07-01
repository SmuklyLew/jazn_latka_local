# UPDATE — v14.7.1-dialogue-grounding-hotfix

## Zakres

To jest hotfix przed większą aktualizacją v14.8.0. Nie usuwa ani nie przepisuje systemu od zera. Bazą jest pełna paczka v14.7.0. Zmiany dotyczą głównie routingu rozmowy, walidacji trafności i odcięcia przypadkowego starego kontekstu.

## Problem naprawiony

Po v14.7.0 runtime potrafił w jednej turze odpowiedzieć trafnie zdaniem i pytaniem, a w innej wrócić do szablonu albo do starego kontekstu. Najbardziej widoczne było to przy pytaniu o plany Łatki. Zamiast odpowiedzieć o własnych planach operacyjnych, system mógł pobrać z pamięci dawny kontekst pracy użytkownika i mówić o drzwiach lub zleceniu.

## Zasada v14.7.1

Pamięć jest źródłem, nie wypełniaczem. Jeśli aktualna wiadomość nie prosi o pamięć, wspomnienie, poprzednią rozmowę albo konkretny zakotwiczony wątek, runtime ma odpowiedzieć z bieżącej intencji. Pamięć może pomagać, ale nie może narzucać tematu.

## Testy dodane

- klasyfikacja `self_plan_question`;
- synteza otwartego pytania bez wciągania pamięci o drzwiach;
- naprawa walidatora dla starego kontekstu przy self-plan;
- pełny `JaznEngine.process_turn` dla pytania „Pomijając mnie, to jakie plany masz?”;
- pełny `JaznEngine.process_turn` dla polecenia przygotowania pełnej wersji systemu.

## Następny etap: v14.8.0

v14.8.0 powinno dopiero rozbudować architekturę: głębszy dialog manager, lepszy plan rozmowy, większą kontrolę pamięci treściowej, emocjonalną granulację i pełniejsze NLP. v14.7.1 stabilizuje próg, żeby większa aktualizacja nie budowała na regresji stale-route.
