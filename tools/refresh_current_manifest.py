#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import fnmatch
import hashlib
import json
import os
import sqlite3
from typing import Any


def _candidate_root(path: Path) -> Path | None:
    """Return the project root if *path* or one of its parents contains main.py.

    The Jaźń root is intentionally anchored on main.py + VERSION.txt, not on
    /mnt/data, the current working directory, or a particular folder name. This
    keeps the tool portable between ChatGPT sandbox, Windows checkouts, Git
    branches and renamed project folders.
    """
    path = path.resolve()
    if path.is_file():
        path = path.parent
    for candidate in (path, *path.parents):
        if (candidate / "main.py").is_file() and (candidate / "VERSION.txt").is_file():
            return candidate
    return None


def find_project_root(start: Path) -> Path:
    """Find the active Jaźń project root by locating main.py.

    Priority:
    1. JAZN_PROJECT_ROOT, if set;
    2. the location of this script;
    3. the current working directory.

    The function fails loudly when no root can be found, instead of silently
    writing files to a sandbox-only path such as /mnt/data.
    """
    probes: list[Path] = []
    env_root = os.environ.get("JAZN_PROJECT_ROOT", "").strip()
    if env_root:
        probes.append(Path(env_root))
    probes.extend([start, Path.cwd()])
    for probe in probes:
        root = _candidate_root(probe)
        if root is not None:
            return root
    checked = ", ".join(str(p) for p in probes)
    raise FileNotFoundError(
        "Nie znaleziono folderu głównego Jaźni. "
        "Uruchom skrypt z folderu projektu albo ustaw JAZN_PROJECT_ROOT. "
        f"Sprawdzone ścieżki: {checked}"
    )


ROOT = find_project_root(Path(__file__).resolve())
ACTIVE_DATABASE = 'memory/sqlite/chat_context.sqlite3'
AUDIT_DATABASE = 'memory/sqlite/chat_context_audit.sqlite3'
HASH_SIZE_LIMIT = 64 * 1024 * 1024
CONTROL_EXCLUDED = {'MANIFEST_CURRENT.json','MANIFEST_RUNTIME_MUTABLE.json','SHA256SUMS','SHA256SUMS_STATIC'}
EXCLUDE_DIR_PARTS = {'__pycache__','.pytest_cache','.git','.mypy_cache','.ruff_cache'}
TRANSIENT_SUFFIXES = ('-wal','-shm','.sqlite3-wal','.sqlite3-shm','.tmp','.tmp_extract_part','.partial')
EXCLUDE_PREFIXES = ('exports/',)
MUTABLE_PATTERNS = (
    'workspace_runtime/**/*.sqlite3','workspace_runtime/**/*.json','workspace_runtime/**/*.jsonl','workspace_runtime/**/*.log',
    'workspace_runtime/logs/**','workspace_runtime/turn_checkpoints/**','workspace_runtime/codex_session_bridge/**',
    'memory/sqlite/chat_context.sqlite3','memory/sqlite/chat_context_audit.sqlite3','memory/sqlite/chat_context_shards.json','memory/sqlite/chat_context_audit_shards.json',
    'memory/layered/*.jsonl','memory/raw/session_continuity_index.json','memory/raw/runtime_event_errors.jsonl','memory/raw/runtime_events.jsonl','memory/raw/conversation_turns.jsonl','memory/raw/dziennik.json',
)
ARCHIVE_PATTERNS = ('backups/**','docs/update_history/**','memory/versioned_sources/**','memory/raw/*.7z','memory/sqlite/*.bak','patches/**','*.patch','*.bak_*','**/*.bak_*')

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)

def exclusion_reason(rel: str) -> str | None:
    p = Path(rel)
    if p.name in CONTROL_EXCLUDED: return 'self_or_checksum_control_file'
    if any(part in EXCLUDE_DIR_PARTS for part in p.parts): return 'generated_cache_directory'
    if any(rel.startswith(prefix) for prefix in EXCLUDE_PREFIXES): return 'export_output_directory'
    if rel.endswith(TRANSIENT_SUFFIXES): return 'transient_runtime_sidecar'
    return None

def classify(rel: str) -> str:
    if matches(rel, MUTABLE_PATTERNS) or (rel.startswith('memory/sqlite/') and rel.endswith('.sqlite3')): return 'mutable_runtime'
    if matches(rel, ARCHIVE_PATTERNS): return 'archive_or_backup'
    if rel.startswith('memory/raw/') or rel.startswith('memory/exported_from_sqlite/') or rel.startswith('memory/processed_chats/'): return 'memory_source_static'
    if rel.startswith(('latka_jazn/','tests/','tools/','scripts/')) or rel == 'main.py': return 'static_code'
    if rel.startswith(('docs/','reports/')) or rel.endswith(('.md','.txt')): return 'static_documentation'
    return 'static_project_file'

def sqlite_diag(root: Path) -> list[dict[str, Any]]:
    out=[]
    for rel in [ACTIVE_DATABASE,AUDIT_DATABASE,'workspace_runtime/dictionary_cache.sqlite3']:
        p=root/rel
        item={'path':rel,'exists':p.exists(),'size_bytes':p.stat().st_size if p.exists() else 0}
        if p.exists():
            try:
                con=sqlite3.connect(f'file:{p.as_posix()}?mode=ro', uri=True, timeout=5)
                try:
                    item['integrity_check']=con.execute('PRAGMA integrity_check').fetchone()[0]
                    item['foreign_key_check_count']=len(con.execute('PRAGMA foreign_key_check').fetchall())
                    item['tables']=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
                    for table in ['messages','legacy_messages','legacy_chunks','conversations','audit_events','tool_events']:
                        try: item[f'{table}_count']=con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                        except Exception: pass
                finally: con.close()
            except Exception as exc: item['error']=repr(exc)
        out.append(item)
    return out

def build(root: Path) -> tuple[dict[str,Any],dict[str,Any]]:
    version=(root/'VERSION.txt').read_text(encoding='utf-8').strip()
    semver=version.split('-',1)[0].lstrip('v')
    now=datetime.now(timezone.utc).isoformat()
    entries=[]; excluded=[]; deferred=[]
    for path in sorted(root.rglob('*')):
        if not path.is_file(): continue
        rel=path.relative_to(root).as_posix()
        reason=exclusion_reason(rel)
        st=path.stat()
        if reason:
            excluded.append({'path':rel,'reason':reason,'size_bytes':st.st_size})
            continue
        classification=classify(rel)
        mutable=classification=='mutable_runtime'
        archive=classification=='archive_or_backup' or matches(rel, ('memory/raw/*.7z',))
        if mutable:
            digest=''
            hpolicy='mutable_runtime_hash_deferred'
            deferred.append({'path':rel,'reason':'mutable_runtime','size_bytes':st.st_size})
        elif st.st_size > HASH_SIZE_LIMIT:
            digest=''
            hpolicy='large_static_hash_deferred'
            deferred.append({'path':rel,'reason':'large_static_file_over_64MiB','size_bytes':st.st_size})
        else:
            digest=sha256(path)
            hpolicy='stable_content_hash'
        entries.append({'path':rel,'size_bytes':st.st_size,'sha256':digest,'mutable_runtime':mutable,'classification':classification,'archive':archive,'hash_policy':hpolicy})
    mutable_entries=[e for e in entries if e['mutable_runtime']]
    static_entries=[e for e in entries if not e['mutable_runtime']]
    archive_entries=[e for e in entries if e.get('archive')]
    common={
        'version':version,'runtime_version':version,'package_version':version,
        'generated_at_utc':now,'updated_at_utc':now,'start_file':'main.py',
        'active_database':ACTIVE_DATABASE,'audit_database':AUDIT_DATABASE,
    }
    manifest={
        'schema_version':f'manifest_current/v{semver}',**common,
        'file_count':len(entries),'static_file_count':len(static_entries),'mutable_runtime_file_count':len(mutable_entries),'archive_file_count':len(archive_entries),'excluded_file_count':len(excluded),'deferred_hash_file_count':len(deferred),
        'hash_size_limit_bytes':HASH_SIZE_LIMIT,
        'mutable_patterns':list(MUTABLE_PATTERNS),
        'excluded_policy':{'control_files_excluded_from_own_hash':sorted(CONTROL_EXCLUDED),'directory_parts_excluded':sorted(EXCLUDE_DIR_PARTS),'transient_suffixes_excluded':list(TRANSIENT_SUFFIXES),'prefixes_excluded':list(EXCLUDE_PREFIXES),'truth_boundary':'MANIFEST_CURRENT.json, MANIFEST_RUNTIME_MUTABLE.json i SHA256SUMS są wyłączone z listy hashowanej, żeby uniknąć samoreferencyjnego SHA. WAL/SHM, cache i eksporty są runtime/transient.'},
        'sqlite_diagnostics':sqlite_diag(root),
        'truth_boundary':'Manifest opisuje rzeczywisty snapshot aktywnego rozpakowanego folderu. Pliki mutable runtime są oznaczone osobno; ich SHA jest świadomie odroczony, bo zmieniają się podczas działania. Duże statyczne pliki powyżej limitu mają rozmiar i politykę hash_deferred zamiast fałszywego hasha.',
        'files':entries,'excluded_files':excluded,'deferred_hash_files':deferred,
    }
    mutable_manifest={
        'schema_version':f'manifest_runtime_mutable/v{semver}',**common,
        'file_count':len(mutable_entries),'mutable_patterns':list(MUTABLE_PATTERNS),
        'truth_boundary':'Ten manifest zawiera tylko pliki, które mogą zmieniać się podczas działania Jaźni. Ich SHA jest odroczony; rozmiar i ścieżka opisują snapshot chwili wygenerowania.',
        'files':mutable_entries,
    }
    return manifest, mutable_manifest

def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def main() -> int:
    root=ROOT
    manifest, mutable_manifest=build(root)
    write_json(root/'MANIFEST_CURRENT.json', manifest)
    write_json(root/'MANIFEST_RUNTIME_MUTABLE.json', mutable_manifest)
    # Keep SHA files standards-compatible: only entries with real hashes.
    real=[e for e in manifest['files'] if e.get('sha256')]
    static_real=[e for e in real if not e['mutable_runtime']]
    (root/'SHA256SUMS').write_text(''.join(f"{e['sha256']}  {e['path']}\n" for e in real), encoding='utf-8')
    (root/'SHA256SUMS_STATIC').write_text(''.join(f"{e['sha256']}  {e['path']}\n" for e in static_real), encoding='utf-8')
    # Local/project-safe output: do not use sandbox-only /mnt/data on Windows.
    # The canonical files above are written directly into the project root.
    # Extra *.corrected copies and report are also written to the same project root
    # so this script works both in ChatGPT sandbox and on a local Windows checkout.
    out=root
    write_json(out/'MANIFEST_CURRENT.corrected.v14_8_2_5.json', manifest)
    write_json(out/'MANIFEST_RUNTIME_MUTABLE.corrected.v14_8_2_5.json', mutable_manifest)
    report={'generated_at_utc':manifest['generated_at_utc'],'root':str(root),'version':manifest['version'],'file_count':manifest['file_count'],'static_file_count':manifest['static_file_count'],'mutable_runtime_file_count':manifest['mutable_runtime_file_count'],'archive_file_count':manifest['archive_file_count'],'excluded_file_count':manifest['excluded_file_count'],'deferred_hash_file_count':manifest['deferred_hash_file_count'],'active_database':manifest['active_database'],'audit_database':manifest['audit_database'],'sqlite_diagnostics':manifest['sqlite_diagnostics'],'outputs':[str((out/'MANIFEST_CURRENT.json').resolve()),str((out/'MANIFEST_RUNTIME_MUTABLE.json').resolve()),str((out/'SHA256SUMS').resolve()),str((out/'SHA256SUMS_STATIC').resolve()),str((out/'MANIFEST_CURRENT.corrected.v14_8_2_5.json').resolve()),str((out/'MANIFEST_RUNTIME_MUTABLE.corrected.v14_8_2_5.json').resolve())]}
    write_json(out/'LATKA_JAZN_MANIFEST_REPAIR_REPORT.v14_8_2_5.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
