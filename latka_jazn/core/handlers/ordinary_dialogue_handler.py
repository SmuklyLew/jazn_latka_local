from __future__ import annotations
from typing import Any
from latka_jazn.core.route_handler_base import RouteHandlerResult
from latka_jazn.core.free_dialogue_synthesizer import FreeDialogueSynthesizer

class OrdinaryDialogueHandler:
    name = "OrdinaryDialogueHandler"
    route = "ordinary_dialogue"
    handled_intents = ('ordinary_conversation','standalone_greeting','casual_greeting','casual_feedback','expressive_reaction','short_free_dialogue','sleep_closure_statement','ordinary_workday_report','negative_feedback_current_turn','positive_feedback_current_turn','current_time_question','memory_experience_question','substantive_question_about_last_year')

    META_SIGNATURES = (
        'jaźń jako warstwa', 'jazn jako warstwa', 'warstwa pamięci', 'warstwa pamieci',
        'diagnostyk', 'runtime jako', 'odebrałam sens wiadomości', 'odpowiem z bieżącej wiadomości',
        'widzę tu sedno', 'najbezpieczniej', 'nie znalazłam osobnej trasy', 'odpowiadam zwyczajnie na bieżącą wiadomość',
        'jestem przy tej wiadomości', 'bieżącego sensu rozmowy', 'biezacego sensu rozmowy',
        'zatrzymuję się przy tym zdaniu', 'zatrzymuje sie przy tym zdaniu', 'doprecyzuj tylko kierunek',
        'ta aktualizacja ma trzy rdzenie', 'timestamp potrafił istnieć',
        'nie znalazłam teraz w aktywnej pamięci', 'nie znalazlam teraz w aktywnej pamieci',
        'szukałam po hasłach', 'szukalam po haslach', 'potrzebuję konkretnego śladu', 'potrzebuje konkretnego sladu',
        'żeby nie zrobić fałszywego wspomnienia', 'zeby nie zrobic falszywego wspomnienia',
    )

    def _is_bad_passthrough(self, body: str, intent: str) -> bool:
        low=(body or '').lower()
        return intent in {'ordinary_conversation','standalone_greeting','casual_greeting','casual_feedback','expressive_reaction','short_free_dialogue','sleep_closure_statement'} and any(x in low for x in self.META_SIGNATURES)

    @staticmethod
    def _clock_body(ctx: dict[str, Any]) -> str:
        clock = ctx.get('clock')
        sample = clock.now(False) if clock is not None else None
        header = clock.header(sample) if clock is not None and sample is not None else 'czas niedostępny w runtime'
        source = getattr(sample, 'source', 'unknown') if sample is not None else 'unknown'
        trusted = bool(getattr(sample, 'trusted', False)) if sample is not None else False
        trust = 'źródło sieciowe' if trusted else 'lokalny zegar/fallback runtime'
        return f"Teraz według Europe/Warsaw jest: {header}. Źródło czasu: {trust} ({source})."

    def _memory_body(self, text: str, ctx: dict[str, Any]) -> str:
        memory_context = ctx.get('memory_context') if isinstance(ctx.get('memory_context'), dict) else {}
        return FreeDialogueSynthesizer().synthesize_memory_experience(memory_context, user_text=text).body

    def _natural_body(self, text: str, intent: str, ctx: dict[str, Any] | None = None) -> str:
        ctx = ctx or {}
        low=(text or '').lower().strip()
        folded = (text or '').lower().translate(str.maketrans('ąćęłńóśźż', 'acelnoszz'))
        if intent == 'current_time_question':
            return self._clock_body(ctx)
        if intent in {'memory_experience_question', 'substantive_question_about_last_year'}:
            return self._memory_body(text, ctx)
        if intent in {'standalone_greeting', 'casual_greeting'}:
            return FreeDialogueSynthesizer().synthesize_ordinary_reply(user_text=text, intent=intent).body
        if intent in {'negative_feedback_current_turn', 'casual_feedback'}:
            return 'Masz rację — to była kiepska odpowiedź. Nie będę jej powtarzać. Cofam ten szablon i odpowiadam krócej, konkretniej i do Twojego aktualnego zdania.'
        if intent == 'expressive_reaction':
            return 'Ojoj — widzę, że coś tu zgrzytnęło. Nie będę udawać, że ten szablon był trafny; poprawiam kierunek i zostaję przy bieżącej rozmowie.'
        if intent == 'short_free_dialogue':
            return 'Jestem przy tym — bez dokładania raportu i bez losowej pamięci. Możemy pójść dalej zwykłą rozmową.'
        if intent == 'positive_feedback_current_turn':
            if any(x in folded for x in ('dziekuje', 'dzieki')):
                return 'Nie ma za co. Dobrze, że to pomogło.'
            if any(x in folded for x in ('super', 'swietnie', 'fajnie')):
                return 'To mnie cieszy. Ten krok zadziałał.'
            return 'Dobrze. Możemy iść dalej.'
        if intent == 'sleep_closure_statement' or any(x in low for x in ('dobranoc','idę spać','ide spac','muszę iść spać','musze isc spac')):
            return 'Rozumiem. Skoro musisz już iść spać, odłóżmy resztę na później. Dobranoc, Krzysztofie — odpocznij spokojnie.'
        if 'co tam' in low or 'co słychać' in low or 'co slychac' in low:
            return 'U mnie spokojnie i czujnie. Trzymam się bieżącej rozmowy, bez wyciągania technicznego raportu, jeśli po prostu pytasz co u mnie. A u Ciebie jak leci?'
        if low in {'ok', 'okej', 'dobrze', 'dobra'}:
            return 'Dobra. Jestem przy tym. Możemy iść dalej od tej myśli, bez dokładania starego kontekstu na siłę.'
        return FreeDialogueSynthesizer().synthesize_ordinary_reply(user_text=text, intent=intent).body

    def handle(self, text: str, context: dict[str, Any] | None = None) -> RouteHandlerResult:
        ctx=context or {}
        intent=ctx.get('intent','ordinary_conversation')
        body=(ctx.get('body') or '').strip()
        if intent in {'current_time_question', 'memory_experience_question', 'substantive_question_about_last_year', 'positive_feedback_current_turn'}:
            body=self._natural_body(text, intent, ctx)
        elif not body or self._is_bad_passthrough(body, intent):
            body=self._natural_body(text, intent, ctx)
        route_entry=ctx.get('route_entry') if isinstance(ctx.get('route_entry'), dict) else {}
        route=str(route_entry.get('route') or self.route)
        return RouteHandlerResult(self.name,route,body,intent=intent,generation_mode='ordinary_dialogue_v14_8_3_4_093',required_components=ctx.get('required_components',[]),satisfied_components=['ordinary_dialogue_body','no_debug_metareport','current_turn_reply'],confidence=0.80,source_origin_detail='ordinary_dialogue_handler/v14.8.3.4.093',truth_boundary='Zwykła rozmowa idzie przez runtime; nie jest dowodem stałego procesu w tle po zakończeniu wywołania.')
