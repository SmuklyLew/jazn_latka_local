from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tools.html_conversations_to_simple_sqlite import build_simple_sqlite


def table_columns(con: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]


def test_simple_sqlite_imports_rendered_dom_without_hash_columns(tmp_path: Path):
    html = tmp_path / "rendered.html"
    html.write_text(
        """<body><div id="root">
        <div class="conversation"><h4>Lista plikow</h4>
        <pre class="message"><div class="author">user</div><div>Pokaz pliki</div></pre>
        <pre class="message"><div class="author">ChatGPT</div><div>Oto lista.</div></pre>
        </div></div></body>""",
        encoding="utf-8",
    )
    db = tmp_path / "simple.sqlite3"

    result = build_simple_sqlite([html], db)

    assert result.conversations == 1
    assert result.messages == 2
    con = sqlite3.connect(db)
    try:
        con.row_factory = sqlite3.Row
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        table_names = {
            row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert {"meta", "sources", "conversations", "messages"}.issubset(table_names)
        all_columns = table_columns(con, "sources") + table_columns(con, "conversations") + table_columns(con, "messages")
        assert not any("sha" in column.lower() for column in all_columns)
        assert tuple(con.execute("SELECT title,message_count FROM conversations").fetchone()) == ("Lista plikow", 2)
        rows = con.execute("SELECT role,author_label,model_slug,text FROM messages ORDER BY message_index").fetchall()
        assert [(row["role"], row["author_label"], row["model_slug"], row["text"]) for row in rows] == [
            ("user", "user", None, "Pokaz pliki"),
            ("assistant", "ChatGPT", None, "Oto lista."),
        ]
    finally:
        con.close()


def test_simple_sqlite_imports_jsondata_visible_user_assistant_with_model(tmp_path: Path):
    html = tmp_path / "chat.html"
    data = [
        {
            "conversation_id": "c1",
            "title": "Model test",
            "current_node": "m4",
            "mapping": {
                "m1": {
                    "children": ["m2"],
                    "message": {
                        "id": "m1",
                        "author": {"role": "system"},
                        "content": {"content_type": "text", "parts": ["hidden system"]},
                    },
                },
                "m2": {
                    "parent": "m1",
                    "children": ["m3"],
                    "message": {
                        "id": "m2",
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": ["Pytanie"]},
                    },
                },
                "m3": {
                    "parent": "m2",
                    "children": ["m4"],
                    "message": {
                        "id": "m3",
                        "author": {"role": "tool", "name": "browser"},
                        "content": {"content_type": "text", "parts": ["tool output"]},
                    },
                },
                "m4": {
                    "parent": "m3",
                    "children": [],
                    "message": {
                        "id": "m4",
                        "author": {"role": "assistant"},
                        "content": {"content_type": "text", "parts": ["Odpowiedz"]},
                        "metadata": {"model_slug": "gpt-test", "default_model_slug": "gpt-default"},
                    },
                },
                "hidden": {
                    "message": {
                        "id": "hidden",
                        "author": {"role": "assistant"},
                        "content": {"content_type": "text", "parts": ["hidden branch"]},
                    }
                },
            },
        }
    ]
    html.write_text("<script>var jsonData = " + json.dumps(data, ensure_ascii=False) + ";</script>", encoding="utf-8")
    db = tmp_path / "simple.sqlite3"

    result = build_simple_sqlite([html], db)

    assert result.conversations == 1
    assert result.messages == 2
    con = sqlite3.connect(db)
    try:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT role,model_slug,default_model_slug,text FROM messages ORDER BY message_index").fetchall()
        assert [(row["role"], row["model_slug"], row["default_model_slug"], row["text"]) for row in rows] == [
            ("user", None, None, "Pytanie"),
            ("assistant", "gpt-test", "gpt-default", "Odpowiedz"),
        ]
    finally:
        con.close()
