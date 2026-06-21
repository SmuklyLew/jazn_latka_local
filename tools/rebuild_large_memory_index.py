#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, sqlite3, subprocess, tempfile
from pathlib import Path
from latka_jazn.memory.raw_memory_status import RawMemoryInspector


def main() -> int:
    parser=argparse.ArgumentParser(description='Rebuild large memory index from chat.html.7z or chat.html without pretending extraction succeeded.')
    parser.add_argument('--from', dest='source', required=True)
    parser.add_argument('--db', required=True)
    ns=parser.parse_args()
    source=Path(ns.source)
    db=Path(ns.db)
    report={'source':str(source),'db':str(db),'extracted':False,'imported':False,'warnings':[]}
    if source.suffix == '.7z' and not shutil.which('7z'):
        try:
            import py7zr # type: ignore
        except Exception:
            report['warnings'].append('archive_present_but_no_py7zr_or_7z_extractor')
            print(json.dumps(report, ensure_ascii=False, indent=2)); return 2
    # This version is a guard/tool contract. Existing indexed DB is not overwritten blindly.
    db.parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(db)
    con.execute('create table if not exists meta(key text primary key, value text not null)')
    con.execute('insert or replace into meta(key,value) values(?,?)',('raw_memory_rebuild_tool_version','v14.8.2'))
    con.commit(); con.close()
    report.update(RawMemoryInspector(Path('.'), db).inspect().to_dict())
    print(json.dumps(report, ensure_ascii=False, indent=2)); return 0
if __name__ == '__main__': raise SystemExit(main())
