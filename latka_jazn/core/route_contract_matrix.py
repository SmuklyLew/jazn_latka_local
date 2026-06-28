from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from latka_jazn.version import schema_version


DIACRITIC_MAP = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
SCHEMA_VERSION = schema_version("route_contract_matrix")


@dataclass(slots=True)
class RouteContractHint:
    schema_version: str
    primary_intent: str | None
    secondary_intents: list[str] = field(default_factory=list)
    matched_contracts: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    diagnostic_request: bool = False
    asks_identity_boundary: bool = False
    question_object: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RouteContractMatrix:
    """Deterministyczna matryca minimalnych kontraktów tras rozmownych.

    Nie zastępuje DialogueIntentClassifier. Daje mu twarde wskazówki dla krótkich
    pytań, które wcześniej łatwo spadały do ordinary_dialogue mimo tego, że
    wymagały statusu runtime, obecności, tożsamości, stanu operacyjnego albo czasu.
    """

    RESOURCE_PATH = Path(__file__).resolve().parents[1] / "resources" / "nlp" / "polish_dialogue_route_lexicon_v14_8_5_016.json"
    SPECIAL_PRIORITY = (
        "runtime_health_check_after_update",
        "runtime_health_check",
        "identity_presence_check",
        "identity_continuity_check",
        "presence_check",
        "self_state_time_awareness",
        "self_state_question",
        "time_awareness_question",
    )

    def __init__(self, resource_path: Path | None = None) -> None:
        self.resource_path = resource_path or self.RESOURCE_PATH
        self.lexicon = self._load_lexicon(self.resource_path)

    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text or "").strip().lower())

    @staticmethod
    def fold(text: str) -> str:
        return (text or "").translate(DIACRITIC_MAP).lower()

    @classmethod
    def _phrase_match(cls, normalized: str, folded: str, phrase: str) -> bool:
        phrase_norm = cls.normalize(phrase)
        phrase_folded = cls.fold(phrase_norm)
        if not phrase_folded:
            return False
        if len(phrase_folded) <= 4 and phrase_folded.isalpha():
            return re.search(rf"(?<!\w){re.escape(phrase_folded)}(?!\w)", folded) is not None
        return phrase_norm in normalized or phrase_folded in folded

    @staticmethod
    def _load_lexicon(path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"intents": {}, "compound_rules": []}

    def _matched_intents(self, normalized: str, folded: str) -> dict[str, list[str]]:
        matched: dict[str, list[str]] = {}
        intents = self.lexicon.get("intents") if isinstance(self.lexicon, dict) else {}
        if not isinstance(intents, dict):
            return matched
        for intent, spec in intents.items():
            phrases = spec.get("phrases") if isinstance(spec, dict) else []
            if not isinstance(phrases, list):
                continue
            hits = [phrase for phrase in phrases if isinstance(phrase, str) and self._phrase_match(normalized, folded, phrase)]
            if hits:
                matched[str(intent)] = hits
        return matched

    def _apply_compounds(self, matched: dict[str, list[str]]) -> tuple[str | None, list[str], list[str]]:
        matched_names = set(matched)
        evidence: list[str] = []
        rules = self.lexicon.get("compound_rules") if isinstance(self.lexicon, dict) else []
        if isinstance(rules, list):
            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                requires = set(str(x) for x in rule.get("requires", []) if isinstance(x, str))
                result = str(rule.get("result") or "")
                if result and requires and requires.issubset(matched_names):
                    evidence.append(f"compound:{'+'.join(sorted(requires))}->{result}")
                    secondary = sorted(matched_names - {result})
                    return result, secondary, evidence
        for intent in self.SPECIAL_PRIORITY:
            if intent in matched_names:
                secondary = sorted(matched_names - {intent})
                return intent, secondary, evidence
        if "ordinary_dialogue" in matched_names and len(matched_names) == 1:
            return "ordinary_dialogue", [], evidence
        return None, sorted(matched_names), evidence

    def classify(self, text: str) -> RouteContractHint:
        normalized = self.normalize(text)
        folded = self.fold(normalized)
        matched = self._matched_intents(normalized, folded)
        primary, secondary, evidence = self._apply_compounds(matched)
        for intent, hits in sorted(matched.items()):
            evidence.append(f"{intent}:{', '.join(hits[:4])}")
        diagnostic = primary in {"runtime_health_check", "runtime_health_check_after_update"}
        identity = primary in {"identity_continuity_check", "identity_presence_check"}
        question_object = {
            "runtime_health_check": "runtime_health",
            "runtime_health_check_after_update": "runtime_health",
            "presence_check": "presence",
            "identity_presence_check": "identity_presence",
            "identity_continuity_check": "identity_continuity",
            "self_state_question": "self_state",
            "time_awareness_question": "current_time",
            "self_state_time_awareness": "self_state_time",
            "ordinary_dialogue": "ordinary_dialogue",
        }.get(primary or "", "unknown")
        return RouteContractHint(
            schema_version=SCHEMA_VERSION,
            primary_intent=primary,
            secondary_intents=secondary,
            matched_contracts=sorted(matched),
            evidence=evidence,
            diagnostic_request=diagnostic,
            asks_identity_boundary=identity,
            question_object=question_object,
        )

    def to_dict(self) -> dict[str, Any]:
        intents = self.lexicon.get("intents") if isinstance(self.lexicon, dict) else {}
        return {
            "schema_version": SCHEMA_VERSION,
            "resource_path": str(self.resource_path),
            "intent_count": len(intents) if isinstance(intents, dict) else 0,
            "compound_rules": self.lexicon.get("compound_rules", []) if isinstance(self.lexicon, dict) else [],
            "truth_boundary": "Matryca tras to deterministiczny kontrakt minimalny; nie zastępuje LLM ani pełnej walidacji odpowiedzi.",
        }
