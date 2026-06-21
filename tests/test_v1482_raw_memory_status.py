import sqlite3
from pathlib import Path
from latka_jazn.memory.raw_memory_status import RawMemoryInspector


def test_v1482_empty_sqlite_not_index_available(tmp_path: Path):
    root = tmp_path
    (root/'memory'/'raw').mkdir(parents=True)
    (root/'workspace_runtime').mkdir(parents=True)
    (root/'memory'/'raw'/'chat.html.7z').write_bytes(b'fake')
    db = root/'workspace_runtime'/'empty.sqlite3'
    con = sqlite3.connect(db)
    con.execute('create table legacy_messages(id integer)')
    con.commit(); con.close()
    status = RawMemoryInspector(root, db).inspect()
    assert status.status == 'indeks_pusty'
    assert not status.sqlite_index_available
    assert status.legacy_messages_count == 0


def test_v1482_imported_sqlite_requires_messages_and_source_sha(tmp_path: Path):
    root = tmp_path
    (root/'memory'/'raw').mkdir(parents=True)
    (root/'workspace_runtime').mkdir(parents=True)
    (root/'memory'/'raw'/'chat.html.7z').write_bytes(b'fake')
    db = root/'workspace_runtime'/'memory.sqlite3'
    con = sqlite3.connect(db)
    con.execute('create table legacy_messages(id integer)')
    con.execute('create table meta(key text primary key, value text not null)')
    con.execute('insert into legacy_messages(id) values(1)')
    con.execute("insert into meta(key,value) values('raw_chat_source_sha256','abc')")
    con.commit(); con.close()
    status = RawMemoryInspector(root, db).inspect()
    assert status.sqlite_index_available
    assert status.legacy_messages_count == 1
