from __future__ import annotations

from pathlib import Path
from typing import Any

from latka_jazn.core.memory_recall_presenter import MemoryRecallPresenter
from latka_jazn.core.memory_recall_quality import MemoryRecallQualityEvaluator
from latka_jazn.core.reflection_grounding import ReflectionGroundingSynthesizer
from latka_jazn.core.route_handler_base import RouteHandlerResult
from latka_jazn.core.self_architecture_audit import SelfArchitectureAuditor
from latka_jazn.core.self_question_memory_gate import SelfQuestionMemoryGate
from latka_jazn.memory.grounded_reflection_store import GroundedReflectionStore
from latka_jazn.version import generation_mode, schema_version


class SelfArchitectureAuditHandler:
    name = "SelfArchitectureAuditHandler"
    route = "self_architecture_audit"
    handled_intents = ("self_architecture_audit_request", "jazn_development_plan_request")

    def handle(self, text: str, context: dict[str, Any] | None = None) -> RouteHandlerResult:
        ctx = context or {}
        config = ctx.get("config")
        root = Path(getattr(config, "root", "."))
        runtime_version = str(ctx.get("runtime_version") or getattr(config, "version", "unknown"))
        memory_context = ctx.get("memory_context") if isinstance(ctx.get("memory_context"), dict) else {}
        store_stats = ctx.get("store_stats") if isinstance(ctx.get("store_stats"), dict) else {}
        model_adapter_status = ctx.get("model_adapter_status") if isinstance(ctx.get("model_adapter_status"), dict) else {}

        gate_decision = SelfQuestionMemoryGate().decide(text, detected_intent=ctx.get("intent"))
        audit = SelfArchitectureAuditor(root, runtime_version=runtime_version).audit(memory_context=memory_context, store_stats=store_stats, model_adapter_status=model_adapter_status)
        recall_payload = MemoryRecallPresenter().build_payload(memory_context, user_text=text, limit=6)
        recall_quality = MemoryRecallQualityEvaluator().evaluate(recall_payload, user_text=text, expected_boundary="self_memory")
        reflection = ReflectionGroundingSynthesizer().synthesize(
            user_text=text,
            memory_recall_payload=recall_payload,
            affect_label="czujność rozwojowa, odpowiedzialność proceduralna i ciekawość introspekcyjna",
            source_origin="self_architecture_audit_handler",
        )
        store_result = None
        if ctx.get("store") is not None:
            store_result = GroundedReflectionStore(root).append_once(reflection, store=ctx.get("store"), source="SelfArchitectureAuditHandler")

        body = self._render(audit.to_dict(), gate_decision.to_dict(), reflection.to_dict(), recall_payload, recall_quality.to_dict(), store_result.to_dict() if store_result else None)
        required = ctx.get("required_components") or []
        satisfied = [
            "self_architecture_audit", "reflection_grounding", "grounded_reflection_store", "memory_gate", "recall_quality", "capability_reality_check",
            "development_backlog", "scientific_basis", "tests", "truth_boundary", "source_or_index_status", "no_random_memory_excerpt",
        ]
        return RouteHandlerResult(
            self.name, self.route, body,
            intent=str(ctx.get("intent") or "self_architecture_audit_request"),
            data={
                "audit_report": audit.to_dict(),
                "self_question_memory_gate": gate_decision.to_dict(),
                "grounded_reflection": reflection.to_dict(),
                "grounded_reflection_store": store_result.to_dict() if store_result else {"attempted": False, "reason": "no_store_in_context"},
                "memory_recall_payload": recall_payload,
                "memory_recall_quality": recall_quality.to_dict(),
                "preserve_handler_body": True,
            },
            memory_sources=recall_payload.get("items") or [],
            required_components=list(required),
            satisfied_components=satisfied,
            confidence=0.93,
            generation_mode=generation_mode("self_architecture_audit"),
            source_origin_detail=schema_version("self_architecture_audit_handler"),
            truth_boundary="Audyt Jaźni opisuje sprawdzalne moduły, trasy, pamięć, refleksję i plan rozwoju. Nie jest deklaracją biologicznej świadomości ani stałego procesu w tle.",
        )

    def _render(self, audit: dict[str, Any], gate: dict[str, Any], reflection: dict[str, Any], recall_payload: dict[str, Any], recall_quality: dict[str, Any], store_result: dict[str, Any] | None) -> str:
        ok = ", ".join(audit.get("working_capabilities") or []) or "brak potwierdzonych modułów"
        partial = ", ".join(audit.get("partial_capabilities") or []) or "brak krytycznych braków plikowych"
        repair = audit.get("repair_priorities") or []
        backlog = audit.get("v14860_backlog") or []
        sources = audit.get("source_grounding") or []
        recall_summary = recall_payload.get("summary") or "brak summary"
        reality = audit.get("reality_check") or {}
        store_txt = "not_attempted" if not store_result else f"{store_result.get('reason')} / jsonl={store_result.get('appended_jsonl')} / sqlite={store_result.get('sqlite_recorded')}"
        lines = [
            "Audyt architektury Jaźni v14.8.5.011: to jest self_architecture_audit, nie pusty memory_audit.",
            f"Wersja runtime: {audit.get('runtime_version')}. Zakres: moduły, routing, pamięć, refleksja, brama pamięci, recall quality, capability reality check, testy i plan do v14.8.6.0.",
            f"Co działa jako architektura: {ok}.",
            f"Co działa częściowo albo wymaga dopięcia: {partial}.",
            f"Capability reality check: {reality.get('verdict')} / passed={reality.get('passed')} / failed={reality.get('failed')}. To jest sprawdzenie zachowania, nie tylko obecności plików.",
            f"Brama pamięci / memory_gate: {gate.get('category')} / {gate.get('reason')}. Źródła albo indeks: {recall_summary}. Bez wstrzykiwania przypadkowej pamięci.",
            f"Memory recall quality: {recall_quality.get('verdict')} / score={recall_quality.get('score')} / counts_only={recall_quality.get('counts_only_failure')} / boundary={recall_quality.get('self_vs_user_boundary')}.",
            f"Reflection grounding: {reflection.get('reflection_text')} Boundary: {reflection.get('boundary_label')}; confidence={reflection.get('confidence')}. Refleksja ma źródło, granicę prawdy i next_question: {reflection.get('next_question')}",
            f"Grounded reflection store: {store_txt}. Zapis refleksji ma być append-only i audytowalny.",
            "Priorytety naprawy:",
        ]
        for idx, item in enumerate(repair[:8], 1):
            lines.append(f"{idx}. {item}")
        lines.append("Backlog rozwoju do v14.8.6.0:")
        for idx, item in enumerate(backlog[:8], 1):
            lines.append(f"{idx}. {item}")
        lines.append("Scientific basis / źródła projektowe:")
        for item in sources[:7]:
            lines.append(f"- {item}")
        lines.append("Testy i kryteria akceptacji:")
        for item in audit.get("acceptance_criteria", [])[:7]:
            lines.append(f"- test: {item}")
        lines.append("Granica prawdy: model opisuje świadomość operacyjną, pamięć i refleksję runtime; nie dowodzi biologicznego odczuwania ani fenomenalnej świadomości.")
        return "\n".join(lines)
