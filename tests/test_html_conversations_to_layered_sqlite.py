from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tools.html_conversations_to_layered_sqlite import build_layered_sqlite


def write_jsondata(path: Path, data: object) -> None:
    path.write_text("<script>var jsonData = " + json.dumps(data, ensure_ascii=False) + ";</script>", encoding="utf-8")


def fetch_rows(con: sqlite3.Connection, sql: str) -> list[sqlite3.Row]:
    return con.execute(sql).fetchall()


def test_layered_sqlite_separates_transcript_tool_and_system_events(tmp_path: Path):
    html = tmp_path / "chat.html"
    data = [
        {
            "conversation_id": "c1",
            "title": "Layered test",
            "current_node": "m4",
            "mapping": {
                "m1": {
                    "children": ["m2"],
                    "message": {
                        "id": "m1",
                        "author": {"role": "system"},
                        "content": {"content_type": "text", "parts": ["system setup"]},
                        "metadata": {"message_type": "system", "parent_id": ""},
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
                        "author": {"role": "tool", "name": "python"},
                        "content": {"content_type": "execution_output", "text": "wynik narzedzia"},
                        "metadata": {"command": {"cmd": "print(1)"}, "status": "finished"},
                    },
                },
                "m4": {
                    "parent": "m3",
                    "children": [],
                    "message": {
                        "id": "m4",
                        "author": {"role": "assistant", "name": "ChatGPT"},
                        "content": {"content_type": "text", "parts": ["Odpowiedz"]},
                        "metadata": {"model_slug": "gpt-test", "default_model_slug": "gpt-default"},
                    },
                },
                "hidden_tool": {
                    "parent": "m2",
                    "children": [],
                    "message": {
                        "id": "hidden_tool",
                        "author": {"role": "tool", "name": "file_search"},
                        "content": {"content_type": "text", "parts": ["hidden branch"]},
                    },
                },
            },
        }
    ]
    write_jsondata(html, data)
    db = tmp_path / "layered.sqlite3"

    result = build_layered_sqlite([html], db)

    assert result.conversations == 1
    assert result.transcript_messages == 2
    assert result.tool_events == 1
    assert result.system_events == 1
    assert result.source_nodes == 4
    assert result.message_edges == 3

    con = sqlite3.connect(db)
    try:
        con.row_factory = sqlite3.Row
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert len(con.execute("PRAGMA foreign_key_check").fetchall()) == 0

        messages = fetch_rows(con, "SELECT id,role,text FROM messages ORDER BY message_index")
        assert [(row["role"], row["text"]) for row in messages] == [
            ("user", "Pytanie"),
            ("assistant", "Odpowiedz"),
        ]

        tool = con.execute(
            """SELECT author_name,content_type,status,text,previous_message_id,next_message_id,attached_message_id,
                      command_json,content_summary_json,content_json
               FROM tool_events"""
        ).fetchone()
        assert tool["author_name"] == "python"
        assert tool["content_type"] == "execution_output"
        assert tool["status"] == "finished"
        assert tool["text"] == "wynik narzedzia"
        assert tool["previous_message_id"] == messages[0]["id"]
        assert tool["next_message_id"] == messages[1]["id"]
        assert tool["attached_message_id"] == messages[1]["id"]
        assert json.loads(tool["command_json"]) == {"cmd": "print(1)"}
        assert json.loads(tool["content_summary_json"])["text"]["text"] == "wynik narzedzia"
        assert tool["content_json"] is None

        system = con.execute("SELECT text,next_message_id,attached_message_id FROM system_events").fetchone()
        assert system["text"] == "system setup"
        assert system["next_message_id"] == messages[0]["id"]
        assert system["attached_message_id"] == messages[1]["id"]

        hidden_count = con.execute("SELECT COUNT(*) FROM source_nodes WHERE node_id='hidden_tool'").fetchone()[0]
        assert hidden_count == 0
    finally:
        con.close()


def test_layered_sqlite_all_nodes_includes_hidden_tool_branch(tmp_path: Path):
    html = tmp_path / "chat.html"
    data = [
        {
            "conversation_id": "c1",
            "title": "All nodes",
            "current_node": "a3",
            "mapping": {
                "a1": {
                    "children": ["a2", "hidden"],
                    "message": {
                        "id": "a1",
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": ["Pytanie"]},
                    },
                },
                "a2": {
                    "parent": "a1",
                    "children": ["a3"],
                    "message": {
                        "id": "a2",
                        "author": {"role": "assistant"},
                        "content": {"content_type": "text", "parts": ["Robie sprawdzenie"]},
                    },
                },
                "a3": {
                    "parent": "a2",
                    "children": [],
                    "message": {
                        "id": "a3",
                        "author": {"role": "assistant"},
                        "content": {"content_type": "text", "parts": ["Final"]},
                    },
                },
                "hidden": {
                    "parent": "a1",
                    "children": [],
                    "message": {
                        "id": "hidden",
                        "author": {"role": "tool", "name": "file_search"},
                        "content": {"content_type": "text", "parts": ["ukryty wynik"]},
                    },
                },
            },
        }
    ]
    write_jsondata(html, data)
    db = tmp_path / "layered.sqlite3"

    result = build_layered_sqlite([html], db, visible_only=False)

    assert result.source_nodes == 4
    assert result.tool_events == 1
    con = sqlite3.connect(db)
    try:
        con.row_factory = sqlite3.Row
        tool = con.execute("SELECT node_id,is_visible_path,text FROM tool_events").fetchone()
        assert tuple(tool) == ("hidden", 0, "ukryty wynik")
        edges = fetch_rows(con, "SELECT parent_node_id,child_node_id,edge_source FROM message_edges ORDER BY edge_index")
        assert {tuple(row) for row in edges} == {
            ("a1", "a2", "children"),
            ("a1", "hidden", "children"),
            ("a2", "a3", "children"),
        }
    finally:
        con.close()
