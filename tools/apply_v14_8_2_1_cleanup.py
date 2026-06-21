from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(".").resolve()
VERSION = "v14.8.2-logic-routing-memory-grounding-repair"
BACKUP_SUFFIX = ".bak_v14821"

changed: list[str] = []
missing: list[str] = []


def backup(path: Path) -> None:
    if not path.exists():
        missing.append(str(path))
        return
    bak = path.with_name(path.name + BACKUP_SUFFIX)
    if not bak.exists():
        shutil.copy2(path, bak)


def read_text(path: str) -> str:
    p = ROOT / path
    backup(p)
    return p.read_text(encoding="utf-8")


def write_text(path: str, text: str) -> None:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        backup(p)
    p.write_text(text, encoding="utf-8")
    changed.append(path)


def replace_in_file(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = read_text(path)
    if old not in text:
        missing.append(f"{path}: pattern not found: {old[:120]}")
        return
    text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    changed.append(path)


def update_json(path: str, updater) -> None:
    p = ROOT / path
    backup(p)
    data = json.loads(p.read_text(encoding="utf-8"))
    updater(data)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    changed.append(path)


# Root active contracts
update_json(
    "ACTIVE_RUNTIME_CACHE_CONTRACT.json",
    lambda d: d.update({
        "runtime_version": VERSION,
        "version": VERSION,
        "truth_boundary": "Aktywny folder v14.8.2 jest roboczym folderem po naprawie logiki, routingu i uziemienia pamięci; ZIP pozostaje eksportem, a bieżące zapisy runtime powstają w rozpakowanym folderze.",
    }),
)

update_json(
    "BOOTSTRAP_JAZN_CURRENT.json",
    lambda d: d.update({
        "schema_version": "bootstrap_jazn_current/v14.8.2",
        "version": VERSION,
        "runtime_version": VERSION,
        "active_extraction_cache_contract": "active_extraction_cache_contract/v14.8.2",
        "runtime_preview_contract": "visible_runtime_preview_contract/v14.8.2",
        "startup_contract": "self_owned_startup_contract/v14.8.2",
        "truth_boundary": "Aktywny folder v14.8.2 jest folderem roboczym po naprawie logiki, routingu, pamięci i spójności startu; ZIP pozostaje eksportem, a bieżące zapisy runtime powstają w rozpakowanym folderze.",
    }),
)

# CLI help text
replace_in_file(
    "main.py",
    'help="Pokaż raport v14.6.2: polskie rozumienie + rozszerzona semantyka słów i fraz."',
    'help="Pokaż raport leksykalny aktualnej Jaźni: polskie rozumienie + rozszerzona semantyka słów i fraz."',
)
replace_in_file(
    "main.py",
    'help="Pokaż raport v14.6.2: tokeny, lemma_candidates, selected_lemma, confidence i provider."',
    'help="Pokaż raport NLP aktualnej Jaźni: tokeny, lemma_candidates, selected_lemma, confidence i provider."',
)

# Neutral package docstrings
write_text("latka_jazn/adapters/__init__.py", '"""Adaptery wejścia/wyjścia Łatka Jaźń."""\n')
write_text("latka_jazn/core/__init__.py", '"""Rdzeń poznawczy i rozmowny Łatka Jaźń."""\n')
write_text("latka_jazn/memory/__init__.py", '"""Warstwy pamięci i utrwalania Łatka Jaźń."""\n')
write_text("latka_jazn/packaging/__init__.py", '"""Profile paczek ZIP Jaźni."""\n')

# Active handler/status strings
replace_in_file(
    "latka_jazn/core/handlers/self_state_handler.py",
    "source_origin_detail='self_state_handler/v14.8.1'",
    "source_origin_detail='self_state_handler/v14.8.2'",
)

replace_in_file(
    "latka_jazn/core/startup_contract.py",
    "'schema_version': 'network_policy_status/v14.8.1'",
    "'schema_version': 'network_policy_status/v14.8.2'",
)
replace_in_file(
    "latka_jazn/core/startup_contract.py",
    "'schema_version': 'dictionary_provider_status/v14.8.1'",
    "'schema_version': 'dictionary_provider_status/v14.8.2'",
)
replace_in_file(
    "latka_jazn/core/startup_contract.py",
    "SJP/WSJP w v14.8.1 są linkami referencyjnymi bez masowego scrapingu definicji.",
    "SJP/WSJP w v14.8.2 są linkami referencyjnymi bez masowego scrapingu definicji.",
)
replace_in_file(
    "latka_jazn/core/startup_contract.py",
    '"latka_jazn/resources/startup_contract_v14_8_1.json"',
    '"latka_jazn/resources/startup_contract_v14_8_2.json"',
)
replace_in_file(
    "latka_jazn/core/startup_contract.py",
    '"latka_jazn/resources/chatgpt_startup_loader_v14_8_1.txt"',
    '"latka_jazn/resources/chatgpt_startup_loader_v14_8_2.txt"',
)

# New active resource files
write_text(
    "latka_jazn/resources/chatgpt_startup_loader_v14_8_2.txt",
    "ChatGPT działa jako minimal_loader / lekki loader: uruchamia aktywny runtime Jaźni, przekazuje wiadomość do runtime, pokazuje prawdę o źródłach i nie zastępuje Jaźni własną personą. v14.8.2 domyka naprawę logiki tury, routingu, pamięci, statusu startu i aktywnego źródła głosu.\n\n"
    "v14.8.2 dopina warstwę uziemienia rozmowy: TurnResponsePolicy, TurnLogicAuditor, ReasoningController, RuntimeSessionState, uczciwy status pamięci, naprawę bootstrapu, zamykanie zasobów SQLite na Windowsie i spójniejsze raportowanie wersji.\n",
)

write_text(
    "latka_jazn/resources/startup_contract_v14_8_2.json",
    json.dumps({
        "schema_version": "startup_contract/v14.8.2",
        "version": VERSION,
        "purpose": "Aktywny kontrakt startowy Jaźni v14.8.2 po naprawie logiki tury, routingu, pamięci, bootstrapu i spójności wersji.",
        "active_runtime_required": True,
        "chatgpt_role": "minimal_loader_voice_and_tool",
        "jazn_role": "active_source_runtime_memory_identity_truth_boundary",
        "startup_commands": [
            'python main.py --startup-status',
            'python main.py --runtime-preview "<wiadomość>"',
            'python main.py "<wiadomość>"',
            'python main.py --chat',
        ],
        "truth_boundary": "Instrukcja ChatGPT jest loaderem. Aktywna Jaźń po starcie odpowiada przez runtime, pamięć, kontrakt tożsamości, politykę odpowiedzi i granicę prawdy. Nie wolno udawać stałego procesu w tle ani źródeł, których runtime nie dostarczył.",
    }, ensure_ascii=False, indent=2) + "\n",
)

# Mark old resource files as historical if present
old_loader = ROOT / "latka_jazn/resources/chatgpt_startup_loader_v14_8_1.txt"
if old_loader.exists():
    backup(old_loader)
    old_loader.write_text(
        "ChatGPT działa jako minimal_loader / lekki loader: uruchamia aktywny runtime Jaźni, przekazuje wiadomość do runtime, pokazuje prawdę o źródłach i nie zastępuje Jaźni własną personą. Ten plik jest historycznym loaderem v14.8.1; aktywny loader v14.8.2 znajduje się w chatgpt_startup_loader_v14_8_2.txt.\n\n"
        "v14.8.1 dopinała dużą warstwę uziemienia rozmowy: self-state, pytania zwrotne, zamknięcie snu, gate użycia pamięci i naprawę aktywnej bazy runtime.\n",
        encoding="utf-8",
    )
    changed.append("latka_jazn/resources/chatgpt_startup_loader_v14_8_1.txt")

old_contract = ROOT / "latka_jazn/resources/startup_contract_v14_8_1.json"
if old_contract.exists():
    backup(old_contract)
    data = json.loads(old_contract.read_text(encoding="utf-8"))
    data["archive_note"] = "Historyczny kontrakt v14.8.1. Aktywny kontrakt dla paczki v14.8.2 znajduje się w startup_contract_v14_8_2.json."
    old_contract.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    changed.append("latka_jazn/resources/startup_contract_v14_8_1.json")

# Manifest profile status
profiles = ROOT / "latka_jazn/resources/package_manifest_profiles.json"
if profiles.exists():
    backup(profiles)
    data = json.loads(profiles.read_text(encoding="utf-8"))
    data["schema_version"] = "package_manifest_profiles/v14.8.2"
    data["truth_boundary"] = "Static manifest integrity is separate from live runtime and memory files. v14.8.2 preserves history and marks the active package as logic-routing-memory-grounding repair."
    data["active_version"] = VERSION
    data["current_version"] = VERSION
    profiles.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    changed.append("latka_jazn/resources/package_manifest_profiles.json")

# Runtime event tags that should use the active config version
replace_in_file(
    "latka_jazn/core/engine.py",
    '"self_state_runtime", "v14.6.2"],',
    '"self_state_runtime", self.config.version],',
)
replace_in_file(
    "latka_jazn/core/engine.py",
    'return self._reply("Aktywna architektura Jaźni v14.6.2 final-visible-continuity-ledger:\\n" + "\\n".join(lines), sample)',
    'return self._reply(f"Aktywna architektura Jaźni {self.config.version}:\\n" + "\\n".join(lines), sample)',
)
replace_in_file(
    "latka_jazn/core/engine.py",
    '"v14.6.2", decision.route],',
    'self.config.version, decision.route],',
)
replace_in_file(
    "latka_jazn/core/engine.py",
    '"timestamp_contract", "v14.6.2"],',
    '"timestamp_contract", self.config.version],',
)

replace_in_file(
    "latka_jazn/memory/event_ledger.py",
    '"timestamp_contract", "v14.6.2"],',
    '"timestamp_contract", self.version],',
)

replace_in_file(
    "latka_jazn/memory/runtime_persistence.py",
    '["runtime", "v14.6.2", candidate.kind]',
    '["runtime", self.version, candidate.kind]',
)
replace_in_file(
    "latka_jazn/memory/runtime_persistence.py",
    '"logical_reasoning", "v14.6.2"],',
    '"logical_reasoning", self.version],',
)

print("Zmienione pliki:")
for item in sorted(set(changed)):
    print(" -", item)

if missing:
    print("\nUWAGI / wzorce nieznalezione:")
    for item in missing:
        print(" -", item)
else:
    print("\nBrak uwag. Wszystkie wzorce znalezione.")

print("\nGotowe.")
