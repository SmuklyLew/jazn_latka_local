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

SCHEMA_VERSION = "simple_html_conversation_sqlite/v1"

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
  message_count INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  message_index INTEGER NOT NULL,
  source_message_id TEXT,
  node_id TEXT,
  parent_node_id TEXT,
  role TEXT,
  author_label TEXT,
  model_slug TEXT,
  default_model_slug TEXT,
  content_type TEXT,
  create_time TEXT,
  is_visible_path INTEGER NOT NULL DEFAULT 1,
  visible_index INTEGER,
  text TEXT NOT NULL DEFAULT '',
  FOREIGN KEY(conversation_id) REFERENCES conversations(id)
);

CREATE INDEX IF NOT EXISTS idx_conversations_source ON conversations(source_id, conversation_index);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, message_index);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
CREATE INDEX IF NOT EXISTS idx_messages_model_slug ON messages(model_slug);
"""


@dataclass(slots=True)
class ImportResult:
    output_db: str
    sources: int = 0
    conversations: int = 0
    messages: int = 0
    skipped_messages: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "output_db": self.output_db,
            "sources": self.sources,
            "conversations": self.conversations,
            "messages": self.messages,
            "skipped_messages": self.skipped_messages,
        }


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def role_from_author(author: dict[str, Any], metadata: dict[str, Any]) -> str:
    role = str(author.get("role") or "").strip().lower()
    if role:
        return role
    label = str(metadata.get("author_label") or author.get("name") or "").strip().lower()
    if label == "user":
        return "user"
    if label in {"chatgpt", "assistant", "latka", "latka/jazn", "latka jazn"}:
        return "assistant"
    return "unknown"


def author_label(author: dict[str, Any], metadata: dict[str, Any], role: str) -> str | None:
    value = metadata.get("author_label") or author.get("name")
    if value:
        return str(value)
    if role == "assistant":
        return "ChatGPT"
    if role == "user":
        return "user"
    return role or None


def extract_full_text(message: dict[str, Any]) -> tuple[str, int]:
    content = message.get("content") or {}
    parts = content.get("parts") or []
    text_parts: list[str] = []

    def add(value: Any) -> None:
        if isinstance(value, str) and value:
            text_parts.append(value)

    for part in parts:
        if isinstance(part, str):
            add(part)
        elif isinstance(part, dict):
            add(part.get("text"))
    if not text_parts:
        add(content.get("text"))
    text = "\n".join(text_parts).strip()
    return text, len(text)


def parse_roles(value: str) -> set[str] | None:
    value = value.strip().lower()
    if value == "all":
        return None
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def should_keep_message(
    *,
    role: str,
    text: str,
    node_id: str,
    visible_nodes: set[str],
    roles: set[str] | None,
    visible_only: bool,
    include_blank: bool,
) -> bool:
    if visible_only and visible_nodes and node_id not in visible_nodes:
        return False
    if roles is not None and role not in roles:
        return False
    if not include_blank and not text.strip():
        return False
    return True


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


def import_source(
    con: sqlite3.Connection,
    source_path: Path,
    *,
    roles: set[str] | None,
    visible_only: bool,
    include_blank: bool,
    limit_conversations: int | None,
) -> tuple[int, int, int]:
    source_path = source_path.resolve()
    source_row = con.execute(
        "INSERT INTO sources(path,source_name,imported_at_utc,size_bytes) VALUES(?,?,?,?)",
        (str(source_path), source_path.name, now_utc(), source_path.stat().st_size if source_path.exists() else None),
    )
    source_id = int(source_row.lastrowid)
    conversations = 0
    messages = 0
    skipped = 0

    for conv_index, conv in enumerate(iter_chatgpt_export_conversations(source_path), start=1):
        if limit_conversations is not None and conv_index > limit_conversations:
            break
        conversations += 1
        mapping = conv.get("mapping") or {}
        current_node = conv.get("current_node")
        visible_nodes_list = visible_path(mapping, current_node)
        visible_nodes = set(visible_nodes_list)
        visible_index = {node_id: index for index, node_id in enumerate(visible_nodes_list)}
        node_ids = ordered_node_ids(mapping, current_node, visible_only=visible_only)

        conversation_row = con.execute(
            """INSERT INTO conversations
               (source_id,conversation_index,source_conversation_id,title,create_time,update_time,source_format,message_count)
               VALUES(?,?,?,?,?,?,?,0)""",
            (
                source_id,
                conv_index,
                str(conv.get("conversation_id") or conv.get("id") or ""),
                conv.get("title") or "",
                "" if conv.get("create_time") is None else str(conv.get("create_time")),
                "" if conv.get("update_time") is None else str(conv.get("update_time")),
                conv.get("source_format") or "chatgpt_jsondata_stream",
            ),
        )
        conversation_id = int(conversation_row.lastrowid)
        message_index = 0

        for node_id in node_ids:
            node = mapping.get(node_id) or {}
            msg = node.get("message")
            if not isinstance(msg, dict):
                skipped += 1
                continue
            author = msg.get("author") or {}
            metadata = msg.get("metadata") or {}
            role = role_from_author(author, metadata)
            text, _ = extract_full_text(msg)
            if not should_keep_message(
                role=role,
                text=text,
                node_id=str(node_id),
                visible_nodes=visible_nodes,
                roles=roles,
                visible_only=visible_only,
                include_blank=include_blank,
            ):
                skipped += 1
                continue
            content = msg.get("content") or {}
            message_index += 1
            con.execute(
                """INSERT INTO messages
                   (conversation_id,message_index,source_message_id,node_id,parent_node_id,role,author_label,
                    model_slug,default_model_slug,content_type,create_time,is_visible_path,visible_index,text)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    conversation_id,
                    message_index,
                    str(msg.get("id") or node_id),
                    str(node_id),
                    "" if node.get("parent") is None else str(node.get("parent")),
                    role,
                    author_label(author, metadata, role),
                    metadata.get("model_slug"),
                    metadata.get("default_model_slug"),
                    content.get("content_type") or "",
                    "" if msg.get("create_time") is None else str(msg.get("create_time")),
                    1 if str(node_id) in visible_nodes or not visible_nodes else 0,
                    visible_index.get(str(node_id)),
                    text,
                ),
            )
            messages += 1

        con.execute("UPDATE conversations SET message_count=? WHERE id=?", (message_index, conversation_id))
        if conv_index % 20 == 0:
            con.commit()

    con.commit()
    return conversations, messages, skipped


def build_simple_sqlite(
    sources: Iterable[Path],
    output_db: Path,
    *,
    force: bool = False,
    roles_value: str = "user,assistant",
    visible_only: bool = True,
    include_blank: bool = False,
    limit_conversations: int | None = None,
) -> ImportResult:
    roles = parse_roles(roles_value)
    con = init_db(output_db, force=force)
    result = ImportResult(output_db=str(output_db.resolve()))
    try:
        for source in sources:
            conv_count, msg_count, skipped = import_source(
                con,
                Path(source),
                roles=roles,
                visible_only=visible_only,
                include_blank=include_blank,
                limit_conversations=limit_conversations,
            )
            result.sources += 1
            result.conversations += conv_count
            result.messages += msg_count
            result.skipped_messages += skipped
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
        description="Copy ChatGPT HTML conversations into a simple transcript SQLite database."
    )
    parser.add_argument("--source", action="append", required=True, help="HTML source path. Can be passed multiple times.")
    parser.add_argument("--output-db", required=True, help="Output .sqlite3 path.")
    parser.add_argument("--force", action="store_true", help="Overwrite output DB if it exists.")
    parser.add_argument("--roles", default="user,assistant", help="Comma-separated roles to keep, or 'all'. Default: user,assistant.")
    parser.add_argument("--all-messages", action="store_true", help="Include hidden/non-visible mapping nodes too.")
    parser.add_argument("--include-blank", action="store_true", help="Keep blank messages.")
    parser.add_argument("--limit-conversations", type=int, default=None, help="Limit conversations per source for tests.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = build_simple_sqlite(
        [Path(item) for item in args.source],
        Path(args.output_db),
        force=args.force,
        roles_value=args.roles,
        visible_only=not args.all_messages,
        include_blank=args.include_blank,
        limit_conversations=args.limit_conversations,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
