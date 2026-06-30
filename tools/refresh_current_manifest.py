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
ACTIVE_DATABASE = 'memory/sqlite/conversation_archive_v1/conversation_archive_manifest.sqlite3'
AUDIT_DATABASE = 'memory/sqlite/runtime_write_v1/runtime_audit.sqlite3'
RUNTIME_WRITE_DATABASE = 'memory/sqlite/runtime_write_v1/runtime_memory.sqlite3'
CONVERSATION_FTS_DATABASE = 'memory/sqlite/conversation_fts_v1/conversation_fts_0001.sqlite3'
STAGING_DATABASE = 'memory/sqlite/staging_v1/staging_memory_0001.sqlite3'
STORAGE_LAYOUT = 'conversation_archive_v1+fts_v1+staging_v1+runtime_write_v1'
HASH_SIZE_LIMIT = 64 * 1024 * 1024
CONTROL_EXCLUDED = {'MANIFEST_CURRENT.json','RUNTIME_STATE.json','SHA256SUMS','SHA256SUMS_STATIC'}
EXCLUDE_DIR_PARTS = {'__pycache__','.pytest_cache','.pytest-tmp','.git','.mypy_cache','.ruff_cache'}
TRANSIENT_SUFFIXES = ('-wal','-shm','.sqlite3-wal','.sqlite3-shm','.tmp','.tmp_extract_part','.partial')
EXCLUDE_PREFIXES = ('exports/',)
EXCLUDED_DETAIL_SUPPRESSED_REASONS = {'generated_cache_directory'}
MUTABLE_PATTERNS = (
    # Everything under workspace_runtime is local runtime/cache/session state.
    'workspace_runtime/**',
    # All memory exports/imports/SQLite-adjacent files are runtime/private memory, not static package files.
    'memory/**',
    # Private/raw memory and imported conversation graphs are memory state, not static code.
    'memory/raw/**',
    'memory/raw_chats/**',
    'memory/processed_chats/**',
    'memory/layered/*.jsonl',
    # SQLite stores and shard/audit sidecars are runtime/private memory stores.
    'memory/sqlite/**/*.sqlite3',
    'memory/sqlite/**/*_shards.json',
    'memory/sqlite/sqlite_audit_report.json',
)
ARCHIVE_PATTERNS = ('backups/**','docs/archive/**','memory/versioned_sources/**','memory/raw/*.7z','memory/sqlite/*.bak','patches/**','patchs/**','reports/**','*.patch','*.bak_*','**/*.bak_*')

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)

def _manifest_entry(rel: str, size: int, digest: str, mutable: bool, classification: str, archive: bool, hpolicy: str) -> dict[str, Any]:
    return {
        'path': rel,
        'size_bytes': size,
        'sha256': digest,
        'mutable_runtime': mutable,
        'classification': classification,
        'archive': archive,
        'hash_policy': hpolicy,
    }

def exclusion_reason(rel: str) -> str | None:
    p = Path(rel)
    if p.name in CONTROL_EXCLUDED: return 'self_or_checksum_control_file'
    if any(part in EXCLUDE_DIR_PARTS for part in p.parts): return 'generated_cache_directory'
    if any(rel.startswith(prefix) for prefix in EXCLUDE_PREFIXES): return 'export_output_directory'
    if rel.lower().endswith('.zip'): return 'zip_archive_not_static_manifest'
    if rel.endswith(TRANSIENT_SUFFIXES): return 'transient_runtime_sidecar'
    return None

def classify(rel: str) -> str:
    # Runtime/private memory is intentionally classified before static code/docs.
    # MANIFEST_CURRENT must not list local runtime state, raw private memory,
    # imported chat graphs, SQLite stores or workspace cache files as static package files.
    if matches(rel, MUTABLE_PATTERNS):
        return 'mutable_runtime'
    if rel.startswith('memory/sqlite/') and rel.endswith(('.sqlite3', '.sqlite3-wal', '.sqlite3-shm')):
        return 'mutable_runtime'
    if matches(rel, ARCHIVE_PATTERNS):
        return 'archive_or_backup'
    if rel.startswith(('latka_jazn/','tests/','tools/','scripts/')) or rel == 'main.py':
        return 'static_code'
    if rel.startswith(('docs/','reports/')) or rel.endswith(('.md','.txt')):
        return 'static_documentation'
    return 'static_project_file'

def sqlite_diag(root: Path) -> list[dict[str, Any]]:
    out=[]
    for rel in [ACTIVE_DATABASE,AUDIT_DATABASE,RUNTIME_WRITE_DATABASE,CONVERSATION_FTS_DATABASE,STAGING_DATABASE,'workspace_runtime/dictionary_cache.sqlite3']:
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
    entries=[]; mutable_entries=[]; excluded=[]; deferred=[]; mutable_deferred=[]
    excluded_file_count=0
    excluded_detail_suppressed: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob('*')):
        if not path.is_file(): continue
        rel=path.relative_to(root).as_posix()
        reason=exclusion_reason(rel)
        st=path.stat()
        if reason:
            excluded_file_count += 1
            if reason in EXCLUDED_DETAIL_SUPPRESSED_REASONS:
                summary = excluded_detail_suppressed.setdefault(reason, {'reason':reason,'count':0,'size_bytes':0})
                summary['count'] += 1
                summary['size_bytes'] += st.st_size
            else:
                excluded.append({'path':rel,'reason':reason,'size_bytes':st.st_size})
            continue
        classification=classify(rel)
        mutable=classification=='mutable_runtime'
        archive=classification=='archive_or_backup'
        if mutable:
            # Keep runtime/private-memory paths out of MANIFEST_CURRENT.
            # They live only in RUNTIME_STATE so active-cache hashes
            # are stable and static package manifests do not swallow memory state.
            entry = _manifest_entry(rel, st.st_size, '', True, classification, False, 'runtime_or_private_memory_hash_deferred')
            mutable_entries.append(entry)
            mutable_deferred.append({'path':rel,'reason':'runtime_or_private_memory','size_bytes':st.st_size})
            continue
        if st.st_size > HASH_SIZE_LIMIT:
            digest=''
            hpolicy='large_static_hash_deferred'
            deferred.append({'path':rel,'reason':'large_static_file_over_64MiB','size_bytes':st.st_size})
        else:
            digest=sha256(path)
            hpolicy='stable_content_hash'
        entries.append(_manifest_entry(rel, st.st_size, digest, False, classification, archive, hpolicy))
    static_entries=list(entries)
    archive_entries=[e for e in entries if e.get('archive')]
    common={
        'version':version,'runtime_version':version,'package_version':version,
        'generated_at_utc':now,'updated_at_utc':now,'start_file':'main.py',
        'active_database':ACTIVE_DATABASE,'audit_database':AUDIT_DATABASE,
        'active_runtime_write_database':RUNTIME_WRITE_DATABASE,
        'active_conversation_archive':ACTIVE_DATABASE,
        'active_conversation_fts':CONVERSATION_FTS_DATABASE,
        'active_staging_database':STAGING_DATABASE,
        'storage_layout':STORAGE_LAYOUT,
    }
    manifest={
        'schema_version':f'manifest_current/v{semver}',**common,
        'file_count':len(entries),'static_file_count':len(static_entries),'mutable_runtime_file_count':0,'runtime_mutable_file_count':len(mutable_entries),'archive_file_count':len(archive_entries),'excluded_file_count':excluded_file_count,'deferred_hash_file_count':len(deferred),
        'hash_size_limit_bytes':HASH_SIZE_LIMIT,
        'runtime_state_file':'RUNTIME_STATE.json',
        'runtime_memory_split_policy':{
            'static_manifest':'MANIFEST_CURRENT.json contains static code/documentation/project files only.',
            'runtime_state':'RUNTIME_STATE.json contains workspace_runtime, raw/private memory, processed chat graphs and SQLite stores.',
            'why':'Memory/runtime files change during operation and must not invalidate the static package manifest or be mistaken for source code.'
        },
        'excluded_file_detail_count':len(excluded),
        'excluded_file_detail_suppressed_count':sum(item['count'] for item in excluded_detail_suppressed.values()),
        'excluded_file_detail_suppressed_summary':list(excluded_detail_suppressed.values()),
        'mutable_patterns':list(MUTABLE_PATTERNS),
        'excluded_policy':{'control_files_excluded_from_own_hash':sorted(CONTROL_EXCLUDED),'directory_parts_excluded':sorted(EXCLUDE_DIR_PARTS),'transient_suffixes_excluded':list(TRANSIENT_SUFFIXES),'prefixes_excluded':list(EXCLUDE_PREFIXES),'truth_boundary':'MANIFEST_CURRENT.json, RUNTIME_STATE.json i SHA256SUMS są wyłączone z listy hashowanej, żeby uniknąć samoreferencyjnego SHA. WAL/SHM, cache i eksporty są runtime/transient.'},
        'sqlite_diagnostics':sqlite_diag(root),
        'truth_boundary':'Manifest opisuje rzeczywisty snapshot aktywnego rozpakowanego folderu. Pliki mutable runtime są oznaczone osobno; ich SHA jest świadomie odroczony, bo zmieniają się podczas działania. Duże statyczne pliki powyżej limitu mają rozmiar i politykę hash_deferred zamiast fałszywego hasha.',
        'files':entries,'excluded_files':excluded,'deferred_hash_files':deferred,
    }
    mutable_manifest={
        'schema_version':f'runtime_state/v{semver}',**common,
        'file_count':len(mutable_entries),'mutable_patterns':list(MUTABLE_PATTERNS),
        'deferred_hash_file_count':len(mutable_deferred),
        'deferred_hash_files':mutable_deferred,
        'truth_boundary':'RUNTIME_STATE.json zawiera pliki runtime/prywatnej pamięci: workspace_runtime, raw/private memory, processed chat graphs i SQLite. To nie jest manifest paczki; SHA jest odroczony, a rozmiar i ścieżka opisują snapshot chwili wygenerowania.',
        'files':mutable_entries,
    }
    return manifest, mutable_manifest

def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def main() -> int:
    root=ROOT
    manifest, mutable_manifest=build(root)
    write_json(root/'MANIFEST_CURRENT.json', manifest)
    write_json(root/'RUNTIME_STATE.json', mutable_manifest)
    # Keep SHA files standards-compatible: only entries with real hashes.
    real=[e for e in manifest['files'] if e.get('sha256')]
    static_real=[e for e in real if not e['mutable_runtime']]
    (root/'SHA256SUMS').write_text(''.join(f"{e['sha256']}  {e['path']}\n" for e in real), encoding='utf-8')
    (root/'SHA256SUMS_STATIC').write_text(''.join(f"{e['sha256']}  {e['path']}\n" for e in static_real), encoding='utf-8')
    # Local/project-safe output: do not use sandbox-only /mnt/data on Windows.
    # Only canonical active files are written at the root; reports go to archive.
    out=root
    report={'generated_at_utc':manifest['generated_at_utc'],'root':str(root),'version':manifest['version'],'file_count':manifest['file_count'],'static_file_count':manifest['static_file_count'],'mutable_runtime_file_count':manifest['mutable_runtime_file_count'],'runtime_mutable_file_count':manifest.get('runtime_mutable_file_count', 0),'archive_file_count':manifest['archive_file_count'],'excluded_file_count':manifest['excluded_file_count'],'excluded_file_detail_count':manifest.get('excluded_file_detail_count', len(manifest.get('excluded_files', []))),'excluded_file_detail_suppressed_count':manifest.get('excluded_file_detail_suppressed_count', 0),'deferred_hash_file_count':manifest['deferred_hash_file_count'],'active_database':manifest['active_database'],'audit_database':manifest['audit_database'],'sqlite_diagnostics':manifest['sqlite_diagnostics'],'outputs':[str((out/'MANIFEST_CURRENT.json').resolve()),str((out/'RUNTIME_STATE.json').resolve()),str((out/'SHA256SUMS').resolve()),str((out/'SHA256SUMS_STATIC').resolve()),str((out/'docs/archive/manifest_history/last_refresh_report.json').resolve())]}
    report_path=out/'docs/archive/manifest_history/last_refresh_report.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
