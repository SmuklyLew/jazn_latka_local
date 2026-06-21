from __future__ import annotations

from .base import ProviderLemmaCandidate

class OptionalStanzaPolishProvider:
    """Opcjonalny adapter Stanza.

    Nie pobiera modeli i nie instaluje zależności samodzielnie. Aktywuje się dopiero,
    gdy użytkownik lokalnie zainstaluje `stanza` oraz modele języka polskiego.
    """
    name = "optional_stanza_pl"

    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = enabled
        self._pipeline = None
        self.available = False
        if enabled:
            self._try_init()

    def _try_init(self) -> None:
        try:
            import stanza  # type: ignore
            self._pipeline = stanza.Pipeline(lang="pl", processors="tokenize,pos,lemma", tokenize_no_ssplit=True, verbose=False)
            self.available = True
        except Exception:
            self._pipeline = None
            self.available = False

    def analyse_token(self, token: str, *, folded: str, context: str = "") -> list[ProviderLemmaCandidate]:
        if not self.available or self._pipeline is None or not token.strip():
            return []
        try:
            doc = self._pipeline(token)
            for sent in doc.sentences:
                if sent.words:
                    word = sent.words[0]
                    lemma = (word.lemma or folded).lower()
                    return [ProviderLemmaCandidate(
                        lemma=lemma,
                        confidence=0.86,
                        provider=self.name,
                        pos=getattr(word, "upos", None),
                        morph={},
                        explanation="wynik opcjonalnego pipeline Stanza dla PL"
                    )]
        except Exception:
            return []
        return []
