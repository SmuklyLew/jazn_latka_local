#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, zipfile
from pathlib import Path

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024), b''): h.update(c)
    return h.hexdigest()

def main() -> int:
    p=argparse.ArgumentParser(description='Verify Jaźń export package ZIP/SHA.')
    p.add_argument('zip_path', nargs='?', default=None)
    p.add_argument('--strict', action='store_true')
    ns=p.parse_args()
    z=Path(ns.zip_path) if ns.zip_path else None
    if not z or not z.exists():
        print(json.dumps({'ok':False,'error':'zip_path_missing'}, ensure_ascii=False)); return 2
    with zipfile.ZipFile(z) as archive:
        bad=archive.testzip(); members=len(archive.namelist())
    payload={'ok': bad is None, 'zip': str(z), 'sha256': sha(z), 'bad_member': bad, 'members': members}
    print(json.dumps(payload, ensure_ascii=False, indent=2)); return 0 if bad is None else 1
if __name__ == '__main__': raise SystemExit(main())
