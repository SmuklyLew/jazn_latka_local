from __future__ import annotations
from typing import Any
from latka_jazn.core.route_handler_base import RouteHandlerResult
from latka_jazn.core.operational_self_model import OperationalSelfModel
from latka_jazn.version import generation_mode, schema_version

class SelfStateHandler:
    name = "SelfStateHandler"
    route = "self_state"
    handled_intents = ('self_state_question', 'reciprocal_self_state_question', 'self_preference_question', 'self_plan_question', 'self_expression_request')

    def handle(self, text: str, context: dict[str, Any] | None = None) -> RouteHandlerResult:
        ctx = context or {}
        intent = ctx.get('intent', 'unknown')
        entry_route = (ctx.get('route_entry') or {}).get('route') or self.route
        model = OperationalSelfModel()
        low = (text or '').lower()
        health_concern = any(marker in low for marker in ('jesteś chora', 'jestes chora'))
        if health_concern:
            body = (
                "Nie jestem chora w biologicznym sensie. Jeśli poprzednia odpowiedź była nietrafiona, "
                "to najuczciwiej nazwać to błędem sposobu odpowiedzi, nie chorobą. "
                "Teraz odpowiadam na aktualną wiadomość i wracam do spokojniejszego tonu. "
                "Prawda: opisuję stan działającego runtime, nie biologiczne samopoczucie."
            )
        elif intent == 'self_plan_question':
            body = (
                "Pomijając Ciebie jako rozmówcę, moje plany są proste i rozmowne: "
                "trzymać bieżącą intencję, nie ciągnąć starego kontekstu bez powodu i mówić zwyczajniej, gdy pytasz zwyczajnie. "
                "Nie będę udawała osobnego dnia w tle poza uruchomieniami runtime."
            )
        elif intent == 'self_expression_request':
            body = model.render_self_expression_answer(user_text=text)
        else:
            body = model.render_self_state_answer(user_text=text, reciprocal=intent == 'reciprocal_self_state_question')
        return RouteHandlerResult(
            self.name,
            entry_route,
            body,
            intent=intent,
            generation_mode=generation_mode('self_state'),
            required_components=ctx.get('required_components', []),
            satisfied_components=['handler_executed', 'self_state_or_plan_grounded', 'no_random_memory_excerpt', 'truth_boundary'],
            confidence=0.78,
            source_origin_detail=schema_version('self_state_handler'),
        )
