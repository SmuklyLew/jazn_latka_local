from pathlib import Path
from latka_jazn.core.module_responsibility_map import ModuleResponsibilityMap
from latka_jazn.memory.requirements_ledger import RequirementsLedger


def test_module_responsibility_map_builds(tmp_path: Path):
    pkg = tmp_path / "latka_jazn" / "core"
    pkg.mkdir(parents=True)
    (pkg / "conversation.py").write_text("class ConversationResponder: pass\n", encoding="utf-8")
    payload = ModuleResponsibilityMap(tmp_path).build(write=True)
    assert payload["module_count"] == 1
    assert payload["modules"][0]["handles_intents"]


def test_requirements_ledger_seed(tmp_path: Path):
    path = RequirementsLedger(tmp_path).seed_manifest_requirements()
    assert path.exists()
    assert "Runtime oznaczał" in path.read_text(encoding="utf-8")
