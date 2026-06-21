#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from latka_jazn.memory.chat_html_importer import iter_chatgpt_export_conversations, visible_path
from tools.html_conversations_to_simple_sqlite import author_label, extract_full_text, role_from_author

SCHEMA_VERSION = "layered_html_conversation_sqlite/v1"

SCHEMA = """
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS meta(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL,
  source_name TEXT NOT NULL,
  imported_at_utc TEXT NOT NULL,
  size_bytes INTEGER
);

CREATE TABLE IF NOT EXISTS conversations(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id INTEGER NOT NULL,
  conversation_index INTEGER NOT NULL,
  source_conversation_id TEXT,
  title TEXT,
  create_time TEXT,
  update_time TEXT,
  source_format TEXT,
  transcript_message_count INTEGER NOT NULL DEFAULT 0,
  tool_event_count INTEGER NOT NULL DEFAULT 0,
  system_event_count INTEGER NOT NULL DEFAULT 0,
  edge_count INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  message_index INTEGER NOT NULL,
  source_message_id TEXT,
  node_id TEXT NOT NULL,
  parent_node_id TEXT,
  role TEXT NOT NULL,
  author_label TEXT,
  model_slug TEXT,
  default_model_slug TEXT,
  content_type TEXT,
  create_time TEXT,
  is_visible_path INTEGER NOT NULL DEFAULT 1,
  visible_index INTEGER,
  text TEXT NOT NULL DEFAULT '',
  text_length INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS tool_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  event_index INTEGER NOT NULL,
  source_message_id TEXT,
  node_id TEXT NOT NULL,
  parent_node_id TEXT,
  previous_message_id INTEGER,
  next_message_id INTEGER,
  attached_message_id INTEGER,
  author_name TEXT,
  content_type TEXT,
  status TEXT,
  command_json TEXT,
  create_time TEXT,
  is_visible_path INTEGER NOT NULL DEFAULT 1,
  visible_index INTEGER,
  text TEXT NOT NULL DEFAULT '',
  text_length INTEGER NOT NULL DEFAULT 0,
  content_summary_json TEXT,
  metadata_json TEXT,
  content_json TEXT,
  FOREIGN KEY(conversation_id) REFERENCES conversations(id),
  FOREIGN KEY(previous_message_id) REFERENCES messages(id),
  FOREIGN KEY(next_message_id) REFERENCES messages(id),
  FOREIGN KEY(attached_message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS system_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  event_index INTEGER NOT NULL,
  source_message_id TEXT,
  node_id TEXT NOT NULL,
  parent_node_id TEXT,
  previous_message_id INTEGER,
  next_message_id INTEGER,
  attached_message_id INTEGER,
  author_name TEXT,
  content_type TEXT,
  create_time TEXT,
  is_visible_path INTEGER NOT NULL DEFAULT 1,
  visible_index INTEGER,
  text TEXT NOT NULL DEFAULT '',
  text_length INTEGER NOT NULL DEFAULT 0,
  content_summary_json TEXT,
  metadata_json TEXT,
  content_json TEXT,
  FOREIGN KEY(conversation_id) REFERENCES conversations(id),
  FOREIGN KEY(previous_message_id) REFERENCES messages(id),
  FOREIGN KEY(next_message_id) REFERENCES messages(id),
  FOREIGN KEY(attached_message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS source_nodes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  node_index INTEGER NOT NULL,
  node_id TEXT NOT NULL,
  parent_node_id TEXT,
  role TEXT,
  author_name TEXT,
  content_type TEXT,
  source_message_id TEXT,
  is_visible_path INTEGER NOT NULL DEFAULT 0,
  visible_index INTEGER,
  stored_table TEXT,
  stored_id INTEGER,
  skip_reason TEXT,
  FOREIGN KEY(conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS message_edges(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  edge_index INTEGER NOT NULL,
  parent_node_id TEXT,
  child_node_id TEXT NOT NULL,
  parent_role TEXT,
  child_role TEXT,
  edge_source TEXT NOT NULL,
  parent_is_visible_path INTEGER NOT NULL DEFAULT 0,
  child_is_visible_path INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(conversation_id) REFERENCES conversations(id)
);

CREATE INDEX IF NOT EXISTS idx_conversations_source ON conversations(source_id, conversation_index);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, message_index);
CREATE INDEX IF NOT EXISTS idx_messages_node ON messages(conversation_id, node_id);
CREATE INDEX IF NOT EXISTS idx_tool_events_conversation ON tool_events(conversation_id, event_index);
CREATE INDEX IF NOT EXISTS idx_tool_events_attached ON tool_events(attached_message_id);
CREATE INDEX IF NOT EXISTS idx_system_events_conversation ON system_events(conversation_id, event_index);
CREATE INDEX IF NOT EXISTS idx_source_nodes_node ON source_nodes(conversation_id, node_id);
CREATE INDEX IF NOT EXISTS idx_message_edges_child ON message_edges(conversation_id, child_node_id);
CREATE INDEX IF NOT EXISTS idx_message_edges_parent ON message_edges(conversation_id, parent_node_id);
"""


@dataclass(slots=True)
class ImportResult:
    output_db: str
    sources: int = 0
    conversations: int = 0
    transcript_messages: int = 0
    tool_events: int = 0
    system_events: int = 0
    source_nodes: int = 0
    message_edges: int = 0
    skipped_nodes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "output_db": self.output_db,
            "sources": self.sources,
            "conversations": self.conversations,
            "transcript_messages": self.transcript_messages,
            "tool_events": self.tool_events,
            "system_events": self.system_events,
            "source_nodes": self.source_nodes,
            "message_edges": self.message_edges,
            "skipped_nodes": self.skipped_nodes,
        }


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def optional_json(value: Any) -> str | None:
    if value is None:
        return None
    return json_text(value)


def safe_str(value: Any) -> str:
    return "" if value is None else str(value)


def compact_value(value: Any, *, max_text_chars: int) -> Any:
    if isinstance(value, str):
        item: dict[str, Any] = {"type": "str", "char_count": len(value)}
        if len(value) <= max_text_chars:
            item["text"] = value
        else:
            item["preview"] = value[:max_text_chars]
            item["truncated"] = True
        return item
    if isinstance(value, dict):
        return compact_mapping(value, max_text_chars=max_text_chars)
    if isinstance(value, list):
        return {
            "type": "list",
            "count": len(value),
            "items": [compact_value(item, max_text_chars=max_text_chars) for item in value[:10]],
            "truncated": len(value) > 10,
        }
    return value


def compact_mapping(value: dict[str, Any], *, max_text_chars: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        if key == "screenshot" and isinstance(item, str):
            result[key] = {"type": "str", "char_count": len(item), "omitted": True}
        elif key in {"text", "result", "summary", "title", "url", "domain", "name", "language", "response_format_name"}:
            result[key] = compact_value(item, max_text_chars=max_text_chars)
        elif key == "parts" and isinstance(item, list):
            result[key] = {
                "type": "parts",
                "count": len(item),
                "items": [compact_value(part, max_text_chars=max_text_chars) for part in item[:10]],
                "truncated": len(item) > 10,
            }
        elif key == "assets":
            result[key] = compact_value(item, max_text_chars=max_text_chars)
        else:
            result[key] = compact_value(item, max_text_chars=max_text_chars)
    return result


def content_summary(content: dict[str, Any], *, max_text_chars: int) -> str:
    summary = compact_mapping(content, max_text_chars=max_text_chars)
    return json_text(summary)


def command_json(metadata: dict[str, Any]) -> str | None:
    command = metadata.get("command")
    if command is None:
        return None
    return json_text(command)


def event_status(metadata: dict[str, Any]) -> str | None:
    for key in ("status", "result_status", "command_status"):
        value = metadata.get(key)
        if value:
            return str(value)
    return None


def node_parent(node: dict[str, Any], message: dict[str, Any] | None) -> str:
    parent = node.get("parent")
    if parent:
        return str(parent)
    if isinstance(message, dict):
        metadata = message.get("metadata") or {}
        parent = metadata.get("parent_id")
        if parent:
            return str(parent)
    return ""


def ordered_node_ids(mapping: dict[str, Any], current_node: str | None, *, visible_only: bool) -> list[str]:
    path = visible_path(mapping, current_node)
    if visible_only and path:
        return path
    return list(mapping.keys())


def init_db(path: Path, *, force: bool) -> sqlite3.Connection:
    if path.exists():
        if not force:
            raise FileExistsError(f"Output DB already exists: {path}")
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("schema_version", SCHEMA_VERSION))
    con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("created_at_utc", now_utc()))
    return con


def should_keep_transcript(role: str, text: str, *, include_blank: bool) -> bool:
    if role not in {"user", "assistant"}:
        return False
    if not include_blank and not text.strip():
        return False
    return True


def attachment_for_event(
    *,
    previous_message_id: int | None,
    next_message_id: int | None,
    next_assistant_message_id: int | None,
) -> int | None:
    return next_assistant_message_id or next_message_id or previous_message_id


def import_source(
    con: sqlite3.Connection,
    source_path: Path,
    *,
    visible_only: bool,
    include_blank_transcript: bool,
    include_blank_events: bool,
    store_full_json: bool,
    summary_text_chars: int,
    limit_conversations: int | None,
) -> ImportResult:
    source_path = source_path.resolve()
    source_row = con.execute(
        "INSERT INTO sources(path,source_name,imported_at_utc,size_bytes) VALUES(?,?,?,?)",
        (str(source_path), source_path.name, now_utc(), source_path.stat().st_size if source_path.exists() else None),
    )
    source_id = int(source_row.lastrowid)
    result = ImportResult(output_db="", sources=1)

    for conv_index, conv in enumerate(iter_chatgpt_export_conversations(source_path), start=1):
        if limit_conversations is not None and conv_index > limit_conversations:
            break
        result.conversations += 1
        mapping = conv.get("mapping") or {}
        current_node = conv.get("current_node")
        visible_nodes_list = visible_path(mapping, current_node)
        visible_nodes = set(visible_nodes_list)
        visible_index = {node_id: index for index, node_id in enumerate(visible_nodes_list)}
        node_ids = ordered_node_ids(mapping, current_node, visible_only=visible_only)

        conversation_row = con.execute(
            """INSERT INTO conversations
               (source_id,conversation_index,source_conversation_id,title,create_time,update_time,source_format)
               VALUES(?,?,?,?,?,?,?)""",
            (
                source_id,
                conv_index,
                str(conv.get("conversation_id") or conv.get("id") or ""),
                conv.get("title") or "",
                safe_str(conv.get("create_time")),
                safe_str(conv.get("update_time")),
                conv.get("source_format") or "chatgpt_jsondata_stream",
            ),
        )
        conversation_id = int(conversation_row.lastrowid)

        node_info: dict[str, dict[str, Any]] = {}
        message_id_by_node: dict[str, int] = {}
        message_role_by_node: dict[str, str] = {}
        transcript_index = 0

        for node_id in node_ids:
            node = mapping.get(node_id) or {}
            msg = node.get("message")
            if not isinstance(msg, dict):
                node_info[str(node_id)] = {
                    "role": "",
                    "author_name": "",
                    "content_type": "",
                    "source_message_id": "",
                    "parent_node_id": node_parent(node, None),
                    "skip_reason": "missing_message",
                }
                result.skipped_nodes += 1
                continue
            author = msg.get("author") or {}
            metadata = msg.get("metadata") or {}
            content = msg.get("content") or {}
            role = role_from_author(author, metadata)
            text, text_length = extract_full_text(msg)
            parent_node_id = node_parent(node, msg)
            info = {
                "message": msg,
                "node": node,
                "author": author,
                "metadata": metadata,
                "content": content,
                "role": role,
                "author_name": author_label(author, metadata, role) or "",
                "content_type": content.get("content_type") or "",
                "source_message_id": str(msg.get("id") or node_id),
                "parent_node_id": parent_node_id,
                "text": text,
                "text_length": text_length,
                "skip_reason": "",
            }
            node_info[str(node_id)] = info
            message_role_by_node[str(node_id)] = role

            if should_keep_transcript(role, text, include_blank=include_blank_transcript):
                transcript_index += 1
                row = con.execute(
                    """INSERT INTO messages
                       (conversation_id,message_index,source_message_id,node_id,parent_node_id,role,author_label,
                        model_slug,default_model_slug,content_type,create_time,is_visible_path,visible_index,text,text_length)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        conversation_id,
                        transcript_index,
                        info["source_message_id"],
                        str(node_id),
                        parent_node_id,
                        role,
                        info["author_name"],
                        metadata.get("model_slug"),
                        metadata.get("default_model_slug"),
                        info["content_type"],
                        safe_str(msg.get("create_time")),
                        1 if str(node_id) in visible_nodes or not visible_nodes else 0,
                        visible_index.get(str(node_id)),
                        text,
                        text_length,
                    ),
                )
                message_id_by_node[str(node_id)] = int(row.lastrowid)
                result.transcript_messages += 1
            elif role in {"user", "assistant"}:
                info["skip_reason"] = "blank_transcript_message"

        previous_message_by_node: dict[str, int | None] = {}
        next_message_by_node: dict[str, int | None] = {}
        next_assistant_by_node: dict[str, int | None] = {}
        previous_message_id: int | None = None
        for node_id in node_ids:
            node_key = str(node_id)
            previous_message_by_node[node_key] = previous_message_id
            if node_key in message_id_by_node:
                previous_message_id = message_id_by_node[node_key]
        next_message_id: int | None = None
        next_assistant_message_id: int | None = None
        for node_id in reversed(node_ids):
            node_key = str(node_id)
            next_message_by_node[node_key] = next_message_id
            next_assistant_by_node[node_key] = next_assistant_message_id
            if node_key in message_id_by_node:
                next_message_id = message_id_by_node[node_key]
                if node_info.get(node_key, {}).get("role") == "assistant":
                    next_assistant_message_id = message_id_by_node[node_key]

        stored_ref_by_node: dict[str, tuple[str, int] | None] = {
            node_id: ("messages", row_id) for node_id, row_id in message_id_by_node.items()
        }
        tool_index = 0
        system_index = 0

        for node_id in node_ids:
            node_key = str(node_id)
            info = node_info.get(node_key)
            if not info or "message" not in info:
                continue
            role = info["role"]
            if role not in {"tool", "system"}:
                continue
            text = info["text"]
            if not include_blank_events and not text.strip():
                info["skip_reason"] = "blank_event"
                result.skipped_nodes += 1
                continue
            metadata = info["metadata"]
            content = info["content"]
            previous_id = previous_message_by_node.get(node_key)
            next_id = next_message_by_node.get(node_key)
            attached_id = attachment_for_event(
                previous_message_id=previous_id,
                next_message_id=next_id,
                next_assistant_message_id=next_assistant_by_node.get(node_key),
            )
            common_values = (
                conversation_id,
                info["source_message_id"],
                node_key,
                info["parent_node_id"],
                previous_id,
                next_id,
                attached_id,
                info["author_name"],
                info["content_type"],
                safe_str(info["message"].get("create_time")),
                1 if node_key in visible_nodes or not visible_nodes else 0,
                visible_index.get(node_key),
                text,
                info["text_length"],
                content_summary(content, max_text_chars=summary_text_chars),
                json_text(metadata),
                json_text(content) if store_full_json else None,
            )
            if role == "tool":
                tool_index += 1
                row = con.execute(
                    """INSERT INTO tool_events
                       (conversation_id,event_index,source_message_id,node_id,parent_node_id,previous_message_id,
                        next_message_id,attached_message_id,author_name,content_type,status,command_json,create_time,
                        is_visible_path,visible_index,text,text_length,content_summary_json,metadata_json,content_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        common_values[0],
                        tool_index,
                        common_values[1],
                        common_values[2],
                        common_values[3],
                        common_values[4],
                        common_values[5],
                        common_values[6],
                        common_values[7],
                        common_values[8],
                        event_status(metadata),
                        command_json(metadata),
                        common_values[9],
                        common_values[10],
                        common_values[11],
                        common_values[12],
                        common_values[13],
                        common_values[14],
                        common_values[15],
                        common_values[16],
                    ),
                )
                stored_ref_by_node[node_key] = ("tool_events", int(row.lastrowid))
                result.tool_events += 1
            else:
                system_index += 1
                row = con.execute(
                    """INSERT INTO system_events
                       (conversation_id,event_index,source_message_id,node_id,parent_node_id,previous_message_id,
                        next_message_id,attached_message_id,author_name,content_type,create_time,is_visible_path,
                        visible_index,text,text_length,content_summary_json,metadata_json,content_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        common_values[0],
                        system_index,
                        common_values[1],
                        common_values[2],
                        common_values[3],
                        common_values[4],
                        common_values[5],
                        common_values[6],
                        common_values[7],
                        common_values[8],
                        common_values[9],
                        common_values[10],
                        common_values[11],
                        common_values[12],
                        common_values[13],
                        common_values[14],
                        common_values[15],
                        common_values[16],
                    ),
                )
                stored_ref_by_node[node_key] = ("system_events", int(row.lastrowid))
                result.system_events += 1

        for node_index, node_id in enumerate(node_ids, start=1):
            node_key = str(node_id)
            info = node_info.get(node_key, {})
            stored_ref = stored_ref_by_node.get(node_key)
            con.execute(
                """INSERT INTO source_nodes
                   (conversation_id,node_index,node_id,parent_node_id,role,author_name,content_type,source_message_id,
                    is_visible_path,visible_index,stored_table,stored_id,skip_reason)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    conversation_id,
                    node_index,
                    node_key,
                    info.get("parent_node_id", ""),
                    info.get("role", ""),
                    info.get("author_name", ""),
                    info.get("content_type", ""),
                    info.get("source_message_id", ""),
                    1 if node_key in visible_nodes or not visible_nodes else 0,
                    visible_index.get(node_key),
                    stored_ref[0] if stored_ref else None,
                    stored_ref[1] if stored_ref else None,
                    info.get("skip_reason", ""),
                ),
            )
            result.source_nodes += 1

        edge_index = 0
        seen_edges: set[tuple[str, str]] = set()
        selected_nodes = set(str(item) for item in node_ids)
        for parent_id in node_ids:
            parent_key = str(parent_id)
            node = mapping.get(parent_id) or mapping.get(parent_key) or {}
            for raw_child in (node or {}).get("children") or []:
                raw_child_key = str(raw_child)
                if raw_child_key not in selected_nodes:
                    continue
                edge = (parent_key, raw_child_key)
                if edge in seen_edges:
                    continue
                seen_edges.add(edge)
                edge_index += 1
                insert_edge(
                    con,
                    conversation_id=conversation_id,
                    edge_index=edge_index,
                    parent_node_id=parent_key,
                    child_node_id=raw_child_key,
                    edge_source="children",
                    role_by_node=message_role_by_node,
                    visible_nodes=visible_nodes,
                )
                result.message_edges += 1
        for child_id in node_ids:
            child_key = str(child_id)
            node = mapping.get(child_id) or mapping.get(child_key) or {}
            msg = node.get("message") if isinstance(node, dict) else None
            parent_id = node_parent(node, msg if isinstance(msg, dict) else None)
            if parent_id and parent_id in selected_nodes:
                edge = (parent_id, child_key)
                if edge in seen_edges:
                    continue
                seen_edges.add(edge)
                edge_index += 1
                insert_edge(
                    con,
                    conversation_id=conversation_id,
                    edge_index=edge_index,
                    parent_node_id=parent_id,
                    child_node_id=child_key,
                    edge_source="parent",
                    role_by_node=message_role_by_node,
                    visible_nodes=visible_nodes,
                )
                result.message_edges += 1

        con.execute(
            """UPDATE conversations
               SET transcript_message_count=?, tool_event_count=?, system_event_count=?, edge_count=?
               WHERE id=?""",
            (transcript_index, tool_index, system_index, edge_index, conversation_id),
        )
        if conv_index % 20 == 0:
            con.commit()

    con.commit()
    return result


def insert_edge(
    con: sqlite3.Connection,
    *,
    conversation_id: int,
    edge_index: int,
    parent_node_id: str,
    child_node_id: str,
    edge_source: str,
    role_by_node: dict[str, str],
    visible_nodes: set[str],
) -> None:
    con.execute(
        """INSERT INTO message_edges
           (conversation_id,edge_index,parent_node_id,child_node_id,parent_role,child_role,edge_source,
            parent_is_visible_path,child_is_visible_path)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            conversation_id,
            edge_index,
            parent_node_id,
            child_node_id,
            role_by_node.get(parent_node_id, ""),
            role_by_node.get(child_node_id, ""),
            edge_source,
            1 if parent_node_id in visible_nodes or not visible_nodes else 0,
            1 if child_node_id in visible_nodes or not visible_nodes else 0,
        ),
    )


def build_layered_sqlite(
    sources: Iterable[Path],
    output_db: Path,
    *,
    force: bool = False,
    visible_only: bool = True,
    include_blank_transcript: bool = False,
    include_blank_events: bool = True,
    store_full_json: bool = False,
    summary_text_chars: int = 1200,
    limit_conversations: int | None = None,
) -> ImportResult:
    con = init_db(output_db, force=force)
    result = ImportResult(output_db=str(output_db.resolve()))
    try:
        for source in sources:
            source_result = import_source(
                con,
                Path(source),
                visible_only=visible_only,
                include_blank_transcript=include_blank_transcript,
                include_blank_events=include_blank_events,
                store_full_json=store_full_json,
                summary_text_chars=summary_text_chars,
                limit_conversations=limit_conversations,
            )
            result.sources += source_result.sources
            result.conversations += source_result.conversations
            result.transcript_messages += source_result.transcript_messages
            result.tool_events += source_result.tool_events
            result.system_events += source_result.system_events
            result.source_nodes += source_result.source_nodes
            result.message_edges += source_result.message_edges
            result.skipped_nodes += source_result.skipped_nodes
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        fk_errors = len(con.execute("PRAGMA foreign_key_check").fetchall())
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("integrity_check", str(integrity)))
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("foreign_key_errors", str(fk_errors)))
        con.commit()
    finally:
        con.close()
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy ChatGPT HTML conversations into a layered transcript/audit SQLite database."
    )
    parser.add_argument("--source", action="append", required=True, help="HTML source path. Can be passed multiple times.")
    parser.add_argument("--output-db", required=True, help="Output .sqlite3 path.")
    parser.add_argument("--force", action="store_true", help="Overwrite output DB if it exists.")
    parser.add_argument("--all-nodes", action="store_true", help="Include hidden/non-visible mapping nodes too.")
    parser.add_argument("--include-blank-transcript", action="store_true", help="Keep blank user/assistant transcript messages.")
    parser.add_argument("--drop-blank-events", action="store_true", help="Drop blank tool/system events.")
    parser.add_argument("--store-full-json", action="store_true", help="Store full content JSON for tool/system events.")
    parser.add_argument(
        "--summary-text-chars",
        type=int,
        default=1200,
        help="Maximum text chars kept inside content_summary_json previews. Full event text stays in text.",
    )
    parser.add_argument("--limit-conversations", type=int, default=None, help="Limit conversations per source for tests.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = build_layered_sqlite(
        [Path(item) for item in args.source],
        Path(args.output_db),
        force=args.force,
        visible_only=not args.all_nodes,
        include_blank_transcript=args.include_blank_transcript,
        include_blank_events=not args.drop_blank_events,
        store_full_json=args.store_full_json,
        summary_text_chars=args.summary_text_chars,
        limit_conversations=args.limit_conversations,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
