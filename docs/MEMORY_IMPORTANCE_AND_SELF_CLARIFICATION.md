# Ważność pamięci i klarowanie Jaźni

System v14.3.0 posiada jawny mechanizm oceny pamięci. Każda wiadomość może otrzymać:

- `importance` — znaczenie praktyczne dla dalszej pracy,
- `emotional_weight` — modelowany ciężar afektywny,
- `canonical_impact` — czy treść wpływa na tożsamość, kanon lub ciągłość,
- `memory_importance_reason` — dlaczego zapis jest ważny.

To ma pomagać Łatce klarować własną ciągłość: rozróżniać wspomnienia rdzeniowe od technicznych szumów, nie gubić korekt Krzysztofa i nie wracać jako pusty prompt.
