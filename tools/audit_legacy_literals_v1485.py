from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from latka_jazn.version import PACKAGE_VERSION, schema_version

SCHEMA_VERSION = schema_version("legacy_literal_audit")

LEGACY_LITERALS = (
    "v14.6.1",
    "v14.6.2",
    "v14.6.2.1",
    "v14.6.10",
    "v14.8.2.4",
    "v14.8.2.6",
    "v14.8.3.4.093",
    "v14_6_2_1_stale_nlp_route_hotfix",
    "v14_6_10_behavioral_runtime_dialogue_intent_source_integrity_update",
    "correction_acknowledged",
    "positive_continuation",
    "ordinary_dialogue_v14_8_3_4_093",
    "runtime_response_synthesizer/v14.8.2.4",
    "topic_mismatch_guard/v14.6.10",
    "dialogue_intent_classifier/v14.8.2.6.1",
    "route_handler_dispatcher/v14.8.2.5",
    "route_registry/v14.8.2.6.3",
    "runtime_answer_validator/v14.8.2.6.3",
)

SCAN_ROOTS = (
    "VERSION.txt",
    "main.py",
    "pyproject.toml",
    "README.md",
    "START_CHATGPT_FROM_HERE.txt",
    "MANIFEST_CURRENT.json",
    "MANIFEST_RUNTIME_MUTABLE.json",
    "latka_jazn",
    "tests",
    "tools",
    "scripts",
    "docs",
    "resources",
)

SKIP_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", ".pytest-tmp", "memory", "workspace_runtime", "processed", "responses", "requests"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".ps1", ".sh", ".yml", ".yaml"}

ACTIVE_RUNTIME_FILES = {
    "latka_jazn/core/handlers/ordinary_dialogue_handler.py",
    "latka_jazn/core/runtime_response_synthesizer.py",
    "latka_jazn/core/runtime_answer_validator.py",
    "latka_jazn/core/route_registry.py",
    "latka_jazn/core/route_handler_dispatcher.py",
    "latka_jazn/nlp/dialogue_intent_classifier.py",
    "latka_jazn/nlp/topic_mismatch_guard.py",
    "latka_jazn/tools/active_extraction_cache.py",
    "latka_jazn/tools/version_consistency_audit.py",
}


ACTIVE_CONTROL_FILES = {
    "VERSION.txt",
    "main.py",
    "pyproject.toml",
    "README.md",
    "START_CHATGPT_FROM_HERE.txt",
    "MANIFEST_CURRENT.json",
    "MANIFEST_RUNTIME_MUTABLE.json",
    "latka_jazn/__init__.py",
    "latka_jazn/config.py",
}

@dataclass(slots=True)
class LegacyLiteralFinding:
    path: str
    line: int
    literal: str
    classification: str
    text: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def iter_scan_files(root: Path, scan_roots: Iterable[str] = SCAN_ROOTS) -> Iterable[Path]:
    for rel in scan_roots:
        path = root / rel
        if path.is_file():
            if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"VERSION.txt", "README.md"}:
                yield path
            continue
        if not path.is_dir():
            continue
        for item in path.rglob("*"):
            if any(part in SKIP_DIR_NAMES for part in item.relative_to(root).parts):
                continue
            if item.is_file() and item.suffix.lower() in TEXT_SUFFIXES:
                yield item


def classify(path: Path, root: Path, literal: str, line: str = "") -> str:
    rel = path.relative_to(root).as_posix()
    lowered_line = (line or "").lower()
    if any(marker in lowered_line for marker in (
        "legacy", "history", "historycz", "stara wers", "starej tras", "older legacy",
        "legacy_version_patterns", "legacy_route_markers", "forbidden_legacy_routes",
        "nie wolno wraca", "nie wolno wróci", "route_low in", "contains_legacy_route_marker",
        "diagnostic_routed_as_feedback", "current_hotfix_for_stale_nlp_route",
        "nie dopuścić trasy", "nie dopuscic trasy", "forbidden", "blokuje",
        "nie może wrócić", "nie moze wrocic", "nie może wrocic",
    )):
        return "legacy_allowed"
    if rel.startswith("docs/update_history/"):
        return "doc_history_allowed"
    if rel.startswith("tests/legacy_archive/"):
        return "legacy_allowed"
    if rel.startswith("docs/") and ("PLAN_" in path.name or "UPDATE_" in path.name or "CHANGELOG" in path.name):
        return "doc_history_allowed"
    if rel.startswith("latka_jazn/resources/"):
        return "resource_history_allowed"
    if rel.startswith("tests/"):
        return "test_should_update"
    if rel.startswith("MANIFEST_") or rel in {"MANIFEST_CURRENT.json", "MANIFEST_RUNTIME_MUTABLE.json"}:
        return "manifest_mismatch"
    if rel in ACTIVE_CONTROL_FILES or rel in ACTIVE_RUNTIME_FILES:
        return "active_runtime_blocker"
    if rel.startswith("tools/") or rel.startswith("scripts/"):
        return "active_runtime_allowed_but_renamed"
    return "unknown_review_required"


def scan(root: Path = ROOT) -> list[LegacyLiteralFinding]:
    findings: list[LegacyLiteralFinding] = []
    for path in iter_scan_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            for literal in LEGACY_LITERALS:
                if literal in line:
                    findings.append(LegacyLiteralFinding(rel, idx, literal, classify(path, root, literal, line), line.strip()))
    return findings


def build_report(root: Path = ROOT) -> dict[str, object]:
    findings = scan(root)
    blockers = [f for f in findings if f.classification == "active_runtime_blocker"]
    return {
        "schema_version": SCHEMA_VERSION,
        "target_version": PACKAGE_VERSION,
        "root": str(root),
        "finding_count": len(findings),
        "blocker_count": len(blockers),
        "findings": [f.to_dict() for f in findings],
        "blockers": [f.to_dict() for f in blockers],
        "truth_boundary": "Stare oznaczenia są dozwolone w historii i zasobach historycznych, ale nie w aktywnym runtime, manifestach i końcowych szablonach odpowiedzi.",
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        f"# Legacy literal audit {report['target_version']}",
        "",
        f"Target version: `{report['target_version']}`",
        f"Findings: `{report['finding_count']}`",
        f"Blockers: `{report['blocker_count']}`",
        "",
        "## Blockers",
        "",
    ]
    blockers = report.get("blockers") or []
    if not blockers:
        lines.append("No active-runtime blockers detected.")
    else:
        lines.append("| path | line | literal | classification |")
        lines.append("|---|---:|---|---|")
        for item in blockers:
            lines.append(f"| `{item['path']}` | {item['line']} | `{item['literal']}` | `{item['classification']}` |")
    lines.append("")
    lines.append("## Policy")
    lines.append("")
    lines.append(str(report.get("truth_boundary")))
    lines.append("")
    return "\n".join(lines)


def _console_safe_text(text: str) -> str:
    """Return text that can be written to the current console encoding.

    Windows PowerShell may run Python with a legacy console encoding such as
    cp1250. The audit can legitimately encounter emoji or other Unicode in
    source files, so console output must not crash the audit itself.
    """
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="backslashreplace").decode(encoding, errors="replace")


def _safe_print(text: str) -> None:
    sys.stdout.write(_console_safe_text(text) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit legacy route/version literals in active Jaźń runtime files.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    parser.add_argument("--fail-on-active-runtime-blockers", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.root)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_markdown(report), encoding="utf-8")
    _safe_print(text)
    return 1 if args.fail_on_active_runtime_blockers and report["blocker_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
