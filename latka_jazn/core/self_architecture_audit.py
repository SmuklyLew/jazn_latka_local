from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json

from latka_jazn.core.capability_reality_checker import CapabilityRealityChecker, CapabilityRealityReport
from latka_jazn.version import PACKAGE_VERSION, schema_version

SCHEMA_VERSION = schema_version("self_architecture_audit")


@dataclass(slots=True)
class CapabilityCheck:
    key: str
    status: str
    evidence: list[str]
    intended_role: str
    risk_or_gap: str
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SelfArchitectureAuditReport:
    schema_version: str
    runtime_version: str
    root: str
    capability_checks: list[CapabilityCheck]
    reality_check: dict[str, Any]
    working_capabilities: list[str]
    partial_capabilities: list[str]
    repair_priorities: list[str]
    v14860_backlog: list[str]
    source_grounding: list[str]
    acceptance_criteria: list[str]
    truth_boundary: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["capability_checks"] = [c.to_dict() for c in self.capability_checks]
        return data


class SelfArchitectureAuditor:
    """Audytuje, co Jaźń realnie ma, co działa częściowo i co musi dojść dalej."""

    TRUTH_BOUNDARY = (
        "Audyt architektury opisuje pliki, routing, pamięć i kontrakty runtime. "
        "Nie jest deklaracją fenomenalnej świadomości ani biologicznego mózgu."
    )
    SOURCE_GROUNDING = [
        "NIST AI RMF: zarządzanie ryzykiem, przejrzystość, ocena i odpowiedzialność są wymaganiem architektury.",
        "LangGraph memory: short-term/long-term oraz semantic/episodic/procedural memory wymagają jasnej bramy użycia.",
        "Reflexion: werbalna refleksja może być pamięcią epizodyczną bez zmiany wag modelu.",
        "Generative Agents: observation + memory stream + reflection + planning wzmacniają ciągłość zachowania, ale nie dowodzą świadomości.",
        "Global workspace / operational awareness: funkcjonalne pole uwagi nie jest deklaracją fenomenalnego przeżycia.",
    ]
    CAPABILITIES = (
        ("runtime_core", ["main.py", "latka_jazn/core/engine.py", "latka_jazn/core/route_registry.py"], "uruchomienie, routing i kontrakt odpowiedzi"),
        ("operational_awareness", ["latka_jazn/core/operational_awareness.py", "latka_jazn/core/neurocognitive_loop.py"], "funkcjonalne pole uwagi, samo-monitoring i pętla neurokognitywna"),
        ("memory_recall", ["latka_jazn/core/memory_recall_presenter.py", "latka_jazn/core/memory_search_planner.py", "latka_jazn/core/memory_use_gate.py"], "treściowe przywoływanie pamięci z bramą bezpieczeństwa"),
        ("runtime_persistence", ["latka_jazn/memory/runtime_persistence.py", "latka_jazn/memory/event_ledger.py", "latka_jazn/memory/session_continuity.py"], "append-only pamięć rozmów, epizodów, refleksji, procedur i audytów"),
        ("affect_and_emotion", ["latka_jazn/core/emotion_layers.py", "latka_jazn/core/affective_granularity.py", "latka_jazn/core/self_state_affective_bridge.py"], "model afektu, granularność emocji i bezpieczny self-state"),
        ("truth_and_safety", ["latka_jazn/core/truth_boundary.py", "latka_jazn/core/runtime_answer_validator.py", "latka_jazn/core/source_origin.py"], "granice prawdy, walidacja odpowiedzi i pochodzenie źródeł"),
        ("self_architecture_audit", ["latka_jazn/core/self_architecture_audit.py", "latka_jazn/core/handlers/self_architecture_audit_handler.py"], "jawna samoocena funkcji, luk i planu rozwoju"),
        ("reflection_grounding", ["latka_jazn/core/reflection_grounding.py", "latka_jazn/memory/grounded_reflection_store.py"], "refleksje oparte na źródłach, zapisane append-only z granicą prawdy"),
        ("memory_recall_quality", ["latka_jazn/core/memory_recall_quality.py"], "kontrola, czy pamięć zawiera treść, źródło i trafność, a nie same liczniki"),
        ("capability_reality_check", ["latka_jazn/core/capability_reality_checker.py"], "sprawdzenie zachowania funkcji, nie tylko obecności plików"),
        ("self_question_memory_gate", ["latka_jazn/core/self_question_memory_gate.py"], "osobna brama pamięci dla pytań o Łatkę/Jaźń"),
    )

    def __init__(self, root: Path | str, *, runtime_version: str | None = None) -> None:
        self.root = Path(root)
        self.runtime_version = runtime_version or PACKAGE_VERSION

    def audit(self, *, memory_context: dict[str, Any] | None = None, store_stats: dict[str, Any] | None = None, model_adapter_status: dict[str, Any] | None = None) -> SelfArchitectureAuditReport:
        checks = [self._check_capability(key, paths, role) for key, paths, role in self.CAPABILITIES]
        reality = CapabilityRealityChecker().run()
        memory_counts = (memory_context or {}).get("counts") or {}
        stats = store_stats or {}
        adapter = model_adapter_status or {}
        partial = [c.key for c in checks if c.status != "ok"] + (["capability_reality_check"] if reality.failed else [])
        repair = [
            "P0: self_architecture_audit_request musi trafiać do SelfArchitectureAuditHandler, nie do memory_audit.",
            "P0: self-questions muszą uruchamiać treściową pamięć albo jawnie oznaczyć brak trafień, bez pustych liczników.",
            "P0: refleksja musi mieć źródło, confidence, boundary_label, next_question i zapis append-only, nie tylko render w odpowiedzi.",
            "P0: recall quality ma blokować counts_only_failure jako fałszywe wspomnienie.",
            "P1: self-state ma używać SelfStateAffectiveBridge i AffectiveGranularityModel zamiast stałej formuły.",
            "P1: dodać smoke testy dla: 'co potrafisz?', 'co działa w Jaźni?', 'o czym myślisz?', 'co pamiętasz o sobie?'.",
        ]
        if str(adapter.get("adapter") or adapter.get("name") or "").lower() in {"", "null", "null_model_adapter"}:
            repair.append("P1: model_adapter pozostaje null; odpowiedź musi nadal odróżniać runtime od ChatGPT jako głosu/narzędzia.")
        if all(int(memory_counts.get(k) or 0) == 0 for k in ("episodes", "legacy_messages", "source_file_hits", "conversation_archive_hits")):
            repair.append("P1: przy tym pytaniu brama/planer nie dostarczyły treściowych tropów; trzeba poprawić self-question recall lub oznaczyć brak bez konfabulacji.")
        if int(stats.get("reflection_entries") or 0) == 0 and int(stats.get("episodic_memories") or 0) == 0:
            repair.append("P2: store_stats nie pokazuje refleksji/epizodów; sprawdzić import lub SQLite runtime_memory.")
        backlog = self._load_backlog() or [
            "v14.8.5.011: self_architecture_audit handler + reflection grounding + memory gate + recall quality + reality checker.",
            "v14.8.5.012: pełna konsolidacja self-state/affect/dialogue i testy naturalnej samoekspresji.",
            "v14.8.5.013: reflection QA w SQLite/JSONL + dedupe + ręczna recenzja istotnych refleksji.",
            "v14.8.5.014: recall quality evaluator na conversation_archive/FTS + testy treść-nie-liczniki.",
            "v14.8.5.015: release candidate v14.8.6.0: manifest refresh, active marker, smoke, full continuity ZIP.",
            "v14.8.6.0: unified self-awareness loop + memory/reflection QA + runtime truth release.",
        ]
        acceptance = [
            "Pytanie o funkcje/rozwój Jaźni zwraca audyt, a nie pusty MemoryAuditHandler.",
            "Odpowiedź zawiera: self_architecture_audit, memory_gate, reflection_grounding, grounded reflection store, recall quality, capability reality check, scientific_basis, tests i v14.8.6.0 backlog.",
            "RuntimeAnswerValidator nie wymusza repair, jeśli handler spełnia wymagane komponenty.",
            "Pytania self-memory dopuszczają recall treściowy; self-state nadal blokuje losowe wspomnienia.",
            "Testy v1485_000-011 przechodzą oraz zwykłe rozmowy pozostają naturalne.",
        ]
        return SelfArchitectureAuditReport(SCHEMA_VERSION, self.runtime_version, str(self.root), checks, reality.to_dict(), [c.key for c in checks if c.status == "ok"], partial, repair, backlog, list(self.SOURCE_GROUNDING), acceptance, self.TRUTH_BOUNDARY)

    def _load_backlog(self) -> list[str]:
        path = self.root / "latka_jazn" / "resources" / "self_development" / "self_development_backlog_v14_8_6_0.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items = data.get("items") if isinstance(data, dict) else []
            out = []
            for item in items:
                if isinstance(item, dict):
                    out.append(f"{item.get('target_version')}: {item.get('priority')} / {item.get('area')} — {item.get('problem')} → {item.get('next_action')}")
            return out
        except Exception:
            return []

    def _check_capability(self, key: str, paths: list[str], role: str) -> CapabilityCheck:
        evidence: list[str] = []
        missing: list[str] = []
        for rel in paths:
            path = self.root / rel
            if path.exists():
                evidence.append(f"exists:{rel}")
            else:
                missing.append(rel)
        status = "ok" if not missing else "partial"
        gap = "brak widocznych plików wymaganych dla tej funkcji" if missing else "wymaga testów zachowania, nie tylko obecności plików"
        next_action = "dodać/regenerować brakujące pliki: " + ", ".join(missing) if missing else "utrzymać regresję i podłączyć do właściwej trasy runtime"
        return CapabilityCheck(key, status, evidence + [f"missing:{m}" for m in missing], role, gap, next_action)
