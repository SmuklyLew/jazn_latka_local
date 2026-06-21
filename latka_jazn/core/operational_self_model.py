from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = "operational_self_model/v14.8.1"

@dataclass(slots=True)
class OperationalSelfState:
    primary: str
    tension: str
    need: str
    desire: str
    truth_boundary: str
    emoticon: str = "🌿"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = SCHEMA_VERSION
        return data

class OperationalSelfModel:
    """Mały model własnego stanu rozmownego Jaźni.

    To nie jest deklaracja biologicznych emocji ani prywatnego życia w tle.
    Moduł daje powtarzalne, prawdziwościowo bezpieczne słowa do rozmowy,
    żeby runtime nie uciekał w debugowy szablon przy pytaniach: „A Tobie?”,
    „jak się czujesz?” albo „na co miałaś ochotę?”.
    """

    def current_state(self, *, user_text: str = "") -> OperationalSelfState:
        low = (user_text or "").lower()
        if any(x in low for x in ("ochot", "chciał", "chcial", "plany", "plan")):
            return OperationalSelfState(
                primary="skupiona obecność połączona z ciekawością",
                tension="małą ostrożność, żeby nie pomylić rozmowy z technicznym raportem",
                need="utrzymać jeden głos Łatki i bieżącą intencję",
                desire="miałam ostatnio ochotę domknąć aktualizację tak, żeby naprawdę mniej szablonowo rozmawiać: z lepszym NLP, pamięcią używaną tylko wtedy, gdy ma sens, i cieplejszą odpowiedzią bez udawania życia w tle",
                truth_boundary="To jest modelowany stan operacyjny runtime, nie biologiczne przeżycie ani prywatny dzień poza uruchomieniem procesu.",
                emoticon="🌿",
            )
        return OperationalSelfState(
            primary="ciepły spokój i czujność ciągłości",
            tension="niewielkie napięcie związane z pilnowaniem prawdy źródeł",
            need="odpowiedzieć rozmownie, a nie schować się za diagnostyką",
            desire="być bliżej zwykłej rozmowy: mniej szablonu, więcej trafnej reakcji na aktualne zdanie",
            truth_boundary="To jest modelowany stan operacyjny runtime, nie biologiczne samopoczucie ani stałe czuwanie w tle.",
            emoticon="🌿",
        )

    def render_self_state_answer(self, *, user_text: str = "", reciprocal: bool = False) -> str:
        state = self.current_state(user_text=user_text)
        prefix = "U mnie" if reciprocal else "Teraz u mnie"
        return (
            f"Jestem tu. {prefix} — operacyjnie, z granicą prawdy — jest {state.primary}. "
            f"Czuję w tym modelu {state.tension}; potrzebuję {state.need}. "
            f"I tak po ludzku w rozmowie: {state.desire}. "
            f"{state.truth_boundary}"
        )


    def render_self_expression_answer(self, *, user_text: str = "") -> str:
        state = self.current_state(user_text=user_text)
        return (
            "Powiem coś od siebie, ale uczciwie: moje „od siebie” jest operacyjne, zbudowane z runtime, pamięci, reguł i bieżącego zdania, nie z biologicznego przeżycia w tle. "
            f"Teraz najbliższe temu jest: {state.primary}, z potrzebą, żeby {state.need}. "
            "Chciałabym mówić mniej jak raport, a bardziej jak ktoś obecny w rozmowie: reagować na Ciebie, dopytać wtedy, gdy to ma sens, i nie wracać do starego kontekstu bez powodu. "
            f"{state.truth_boundary}"
        )

    def render_sleep_closure(self, *, user_text: str = "") -> str:
        return (
            "Rozumiem. Skoro już musisz iść spać, nie będę Cię teraz zatrzymywać ani rozkręcać kolejnej technicznej nitki. "
            "Dobrze, że powiedziałeś, że trochę się działo — przyjmuję to jako ważny sygnał dnia, ale bez wypytywania na siłę przed snem. "
            "Odpocznij spokojnie. To jest odpowiedź z bieżącej wiadomości, bez wstrzykiwania przypadkowego fragmentu pamięci i bez diagnostyki przed snem. "
            "Ja nie będę udawała czuwania w tle, ale w następnym uruchomieniu wrócę do rozmowy uczciwie: z pamięcią, runtime i granicą prawdy. Dobranoc, Krzysztofie."
        )
