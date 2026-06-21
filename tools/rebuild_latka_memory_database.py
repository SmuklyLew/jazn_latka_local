#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import hashlib
import html
import io
import json
import re
import sqlite3
import sys
import time
import zlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Iterator
from zoneinfo import ZoneInfo


SCRIPT_VERSION = "latka_memory_rebuild/v0.2"
SCHEMA_VERSION = "latka_memory_layered/v1"
DEFAULT_TZ = "Europe/Warsaw"
JSON_MARKER = b"var jsonData = "
CHUNK_SIZE = 1024 * 1024
PDF_CHUNK_CHARS = 12000

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_json(data: Any) -> str:
    return clean_unicode(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def pretty_json(data: Any) -> str:
    return clean_unicode(json.dumps(data, ensure_ascii=False, sort_keys=True))


def clean_unicode(text: str) -> str:
    return text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = clean_unicode(text)
    text = text.replace("\ufeff", " ")
    text = re.sub(r"\s+", " ", text, flags=re.UNICODE).strip()
    return text


def literal_text_hash(text: str) -> str:
    return sha256_text(text or "")


def normalized_content_hash(parts: dict[str, Any]) -> str:
    normalized = {
        "type_norm": normalize_text(parts.get("type_norm")).lower(),
        "title": normalize_text(parts.get("title")).lower(),
        "content_text": normalize_text(parts.get("content_text")).lower(),
        "content_json": parts.get("content_json") or "",
        "dreams": normalize_text(parts.get("dreams")).lower(),
        "scene": normalize_text(parts.get("scene")).lower(),
        "memory_note": normalize_text(parts.get("memory_note")).lower(),
        "emotions_json": parts.get("emotions_json") or "[]",
    }
    return "sha256:" + sha256_text(safe_json(normalized))


def compact_id(prefix: str, *parts: Any) -> str:
    raw = "|".join("" if p is None else str(p) for p in parts)
    return f"{prefix}_{sha256_text(raw)[:24]}"


def short(text: Any, limit: int = 500) -> str:
    value = normalize_text(text)
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def parse_json_maybe(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return default


def flatten_json_text(value: Any) -> str:
    out: list[str] = []

    def walk(item: Any) -> None:
        if item is None:
            return
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, (int, float, bool)):
            out.append(str(item))
        elif isinstance(item, list):
            for child in item:
                walk(child)
        elif isinstance(item, dict):
            for child in item.values():
                walk(child)

    walk(value)
    return normalize_text(" ".join(out))


def parse_datetime(value: Any, *, tz_name: str = DEFAULT_TZ) -> tuple[str | None, str, str | None, str | None]:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return None, "missing", "missing_datetime", None

    tz = ZoneInfo(tz_name)
    if isinstance(value, (int, float)):
        try:
            dt = datetime.fromtimestamp(float(value), timezone.utc).astimezone(tz)
            return dt.isoformat(), "exact", None, raw
        except Exception:
            return None, "malformed", "malformed_datetime", raw

    if re.fullmatch(r"\d+(\.\d+)?", raw):
        try:
            dt = datetime.fromtimestamp(float(raw), timezone.utc).astimezone(tz)
            return dt.isoformat(), "exact", None, raw
        except Exception:
            pass

    cleaned = raw.replace("Z", "+00:00")
    cleaned = re.sub(r"\s+CEST$", "+02:00", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+CET$", "+01:00", cleaned, flags=re.I)
    for candidate in (cleaned, cleaned.replace(" ", "T", 1)):
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            return dt.astimezone(tz).isoformat(), "parsed_text", None, raw
        except Exception:
            pass

    match = re.search(r"\b(\d{4})[-.](\d{2})[-.](\d{2})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?", raw)
    if match:
        year, month, day, hh, mm, ss = match.groups()
        try:
            dt = datetime(
                int(year),
                int(month),
                int(day),
                int(hh or 0),
                int(mm or 0),
                int(ss or 0),
                tzinfo=tz,
            )
            return dt.isoformat(), "parsed_text", None, raw
        except Exception:
            return None, "malformed", "malformed_datetime", raw

    return None, "malformed", "malformed_datetime", raw


def detect_day_month_swap(datetime_iso: str | None, original_text: str | None) -> tuple[str | None, str | None]:
    if not datetime_iso or not original_text:
        return None, None
    main = re.search(r"(\d{4})-(\d{2})-(\d{2})", datetime_iso)
    raw = re.search(r"(\d{4})[-.](\d{2})[-.](\d{2})", original_text)
    if not main or not raw:
        return None, None
    y1, m1, d1 = main.groups()
    y2, m2, d2 = raw.groups()
    if y1 == y2 and m1 == d2 and d1 == m2 and (m1, d1) != (m2, d2):
        return "day_month_swap", f"datetime_iso={y1}-{m1}-{d1} conflicts with raw={y2}-{m2}-{d2}"
    return None, None


def message_text_assets(message: dict[str, Any], *, max_content_chars: int = 0) -> tuple[str, list[dict[str, Any]], list[Any], int]:
    content = message.get("content") or {}
    parts = content.get("parts") or []
    text_parts: list[str] = []
    assets: list[dict[str, Any]] = []
    total_chars = 0

    def add_text(value: str) -> None:
        nonlocal total_chars
        if not value:
            return
        total_chars += len(value)
        text_parts.append(value)

    for part in parts:
        if isinstance(part, str):
            add_text(part)
        elif isinstance(part, dict):
            if isinstance(part.get("text"), str):
                add_text(part["text"])
            if any(part.get(k) for k in ("name", "asset_pointer", "content_type", "mime_type", "size_bytes")):
                assets.append(
                    {
                        k: part.get(k)
                        for k in ("content_type", "name", "asset_pointer", "mime_type", "size_bytes")
                        if k in part
                    }
                )

    if not text_parts and isinstance(content.get("text"), str):
        add_text(content["text"])

    text = "\n".join(x for x in text_parts if x is not None).strip()
    if max_content_chars and len(text) > max_content_chars:
        text = text[:max_content_chars]
    return text, assets, parts, total_chars


def summarize_parts(parts: list[Any], max_items: int = 24) -> list[Any]:
    summary: list[Any] = []
    for part in parts[:max_items]:
        if isinstance(part, str):
            summary.append({"type": "text", "char_count": len(part), "sha256": sha256_text(part)})
        elif isinstance(part, dict):
            item = {k: part.get(k) for k in ("content_type", "name", "mime_type", "size_bytes", "asset_pointer") if k in part}
            if isinstance(part.get("text"), str):
                item["text_char_count"] = len(part["text"])
                item["text_sha256"] = sha256_text(part["text"])
            summary.append(item or {"type": "dict", "keys": sorted(part.keys())[:20]})
        else:
            summary.append({"type": type(part).__name__})
    if len(parts) > max_items:
        summary.append({"truncated_parts": len(parts) - max_items})
    return summary


def visible_path(mapping: dict[str, Any], current_node: str | None) -> list[str]:
    if not current_node:
        return []
    child_to_parent: dict[str, str] = {}
    for node_id, node in mapping.items():
        for child in (node or {}).get("children") or []:
            child_to_parent[str(child)] = str(node_id)
    path: list[str] = []
    seen: set[str] = set()
    node_id: str | None = str(current_node)
    while node_id and node_id in mapping and node_id not in seen:
        seen.add(node_id)
        path.append(node_id)
        node = mapping.get(node_id) or {}
        parent = node.get("parent") or child_to_parent.get(node_id)
        if not parent:
            msg = node.get("message") or {}
            meta = msg.get("metadata") or {}
            parent = meta.get("parent_id")
        node_id = str(parent) if parent else None
    path.reverse()
    return path


def class_names(attrs: list[tuple[str, str | None]]) -> set[str]:
    values: set[str] = set()
    for name, value in attrs:
        if name.lower() == "class" and value:
            values.update(part.strip().lower() for part in value.split() if part.strip())
    return values


def clean_dom_text(parts: list[str]) -> str:
    text = "".join(parts)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+\n", "\n", text)
    text = re.sub(r"\n[ \t\f\v]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def role_from_rendered_author(author: str) -> str:
    lowered = author.strip().lower()
    if lowered == "user":
        return "user"
    if lowered in {"assistant", "chatgpt", "latka", "latka/jazn", "latka jazn"}:
        return "assistant"
    if lowered in {"system", "tool"}:
        return lowered
    return "unknown"


def rendered_dom_conversation_id(index: int, title: str, messages: list[dict[str, str]]) -> str:
    seed = safe_json(
        {
            "index": index,
            "title": title,
            "message_count": len(messages),
            "first_author": messages[0].get("author") if messages else "",
            "first_text": (messages[0].get("text") or "")[:200] if messages else "",
        }
    )
    return f"rendered-dom-{index:06d}-{sha256_text(seed)[:12]}"


def conversation_from_rendered_dom(index: int, title: str, messages: list[dict[str, str]]) -> dict[str, Any]:
    conversation_id = rendered_dom_conversation_id(index, title, messages)
    mapping: dict[str, Any] = {}
    previous_node_id: str | None = None
    current_node: str | None = None
    for msg_index, item in enumerate(messages, start=1):
        node_id = f"{conversation_id}-node-{msg_index:06d}"
        message_id = f"{conversation_id}-message-{msg_index:06d}"
        author_label = item.get("author") or "unknown"
        role = role_from_rendered_author(author_label)
        text = item.get("text") or ""
        mapping[node_id] = {
            "id": node_id,
            "parent": previous_node_id,
            "children": [],
            "message": {
                "id": message_id,
                "author": {"role": role, "name": author_label},
                "create_time": None,
                "content": {"content_type": "text", "parts": [text]},
                "metadata": {
                    "message_type": "rendered_dom_message",
                    "author_label": author_label,
                    "source_format": "rendered_chat_dom_html",
                },
            },
        }
        if previous_node_id is not None:
            mapping[previous_node_id]["children"].append(node_id)
        previous_node_id = node_id
        current_node = node_id
    return {
        "conversation_id": conversation_id,
        "id": conversation_id,
        "title": title or "(untitled)",
        "create_time": None,
        "update_time": None,
        "current_node": current_node,
        "mapping": mapping,
        "source_format": "rendered_chat_dom_html",
    }


class RenderedChatDomParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.conversations: list[dict[str, Any]] = []
        self._conversation_depth: int | None = None
        self._conversation_index = 0
        self._title_parts: list[str] | None = None
        self._capturing_title = False
        self._messages: list[dict[str, str]] = []
        self._message_depth: int | None = None
        self._author_depth: int | None = None
        self._author_parts: list[str] = []
        self._content_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        classes = class_names(attrs)
        if tag == "div" and self._conversation_depth is None and "conversation" in classes:
            self._conversation_depth = 1
            self._conversation_index += 1
            self._title_parts = None
            self._capturing_title = False
            self._messages = []
            return
        if tag == "div" and self._conversation_depth is not None:
            self._conversation_depth += 1
        if self._conversation_depth is None:
            return
        if tag == "h4" and self._message_depth is None:
            self._title_parts = []
            self._capturing_title = True
            return
        if tag == "pre" and "message" in classes and self._message_depth is None:
            self._message_depth = 1
            self._author_depth = None
            self._author_parts = []
            self._content_parts = []
            return
        if self._message_depth is not None:
            self._message_depth += 1
            if tag == "div" and "author" in classes and self._author_depth is None:
                self._author_depth = 1
                return
            if self._author_depth is not None:
                self._author_depth += 1
            elif tag in {"br", "div", "p", "li", "section", "h1", "h2", "h3", "h4", "h5", "h6"}:
                self._content_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "h4" and self._title_parts is not None and self._message_depth is None:
            self._capturing_title = False
            return
        if self._message_depth is not None:
            if self._author_depth is not None:
                self._author_depth -= 1
                if self._author_depth <= 0:
                    self._author_depth = None
            elif tag in {"div", "p", "li", "section", "h1", "h2", "h3", "h4", "h5", "h6"}:
                self._content_parts.append("\n")
            self._message_depth -= 1
            if self._message_depth <= 0:
                self._finish_message()
        if tag == "div" and self._conversation_depth is not None:
            self._conversation_depth -= 1
            if self._conversation_depth <= 0:
                self._finish_conversation()

    def handle_data(self, data: str) -> None:
        if self._capturing_title and self._title_parts is not None and self._message_depth is None:
            self._title_parts.append(data)
        elif self._message_depth is not None:
            if self._author_depth is not None:
                self._author_parts.append(data)
            else:
                self._content_parts.append(data)

    def _finish_message(self) -> None:
        author = clean_dom_text(self._author_parts) or "unknown"
        text = clean_dom_text(self._content_parts)
        self._messages.append({"author": author, "text": text})
        self._message_depth = None
        self._author_depth = None
        self._author_parts = []
        self._content_parts = []

    def _finish_conversation(self) -> None:
        title = clean_dom_text(self._title_parts or [])
        self.conversations.append(conversation_from_rendered_dom(self._conversation_index, title, self._messages))
        self._conversation_depth = None
        self._title_parts = None
        self._capturing_title = False
        self._messages = []


def iter_rendered_chat_dom_conversations(path: Path) -> Iterator[dict[str, Any]]:
    parser = RenderedChatDomParser()
    parser.feed(path.read_text(encoding="utf-8-sig", errors="replace"))
    parser.close()
    yield from parser.conversations


@dataclass
class Progress:
    enabled: bool
    total_bytes: int
    processed_bytes: int = 0
    last_percent: int = -1
    current_source: str = ""

    def set_source(self, label: str) -> None:
        self.current_source = label
        self.emit(force=True)

    def set_processed(self, value: int) -> None:
        self.processed_bytes = max(self.processed_bytes, min(value, self.total_bytes))
        self.emit()

    def add(self, value: int) -> None:
        self.processed_bytes = min(self.total_bytes, self.processed_bytes + max(0, value))
        self.emit()

    def emit(self, *, force: bool = False) -> None:
        if not self.enabled:
            return
        if self.total_bytes <= 0:
            pct = 100
        else:
            pct = int((self.processed_bytes / self.total_bytes) * 100)
        if force or pct != self.last_percent:
            self.last_percent = pct
            print(f"[progress] {pct:3d}% {self.current_source}", file=sys.stderr, flush=True)


@dataclass
class SourceSpec:
    path: Path
    kind: str
    priority: int
    parser_name: str
    notes: str = ""
    design_document: bool = False


@dataclass
class ImportStats:
    counters: Counter = field(default_factory=Counter)
    errors: list[str] = field(default_factory=list)
    source_summaries: list[dict[str, Any]] = field(default_factory=list)

    def inc(self, key: str, value: int = 1) -> None:
        self.counters[key] += value

    def error(self, label: str, exc: BaseException | str) -> None:
        self.errors.append(f"{label}: {exc!r}" if not isinstance(exc, str) else f"{label}: {exc}")


SCHEMA = """
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA temp_store=MEMORY;
PRAGMA cache_size=-200000;
PRAGMA mmap_size=268435456;

CREATE TABLE IF NOT EXISTS meta(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS source_refs(
  id TEXT PRIMARY KEY,
  source_name TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  local_path TEXT NOT NULL,
  source_priority INTEGER NOT NULL,
  file_size_bytes INTEGER,
  sha256 TEXT,
  parse_status TEXT NOT NULL,
  parser_name TEXT,
  imported_at TEXT NOT NULL,
  notes TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS import_batches(
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  script_version TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  root_path TEXT NOT NULL,
  output_db TEXT NOT NULL,
  source_count INTEGER NOT NULL,
  stats_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL,
  errors_json TEXT NOT NULL DEFAULT '[]'
) STRICT;

CREATE TABLE IF NOT EXISTS raw_source_rows(
  id TEXT PRIMARY KEY,
  source_ref_id TEXT NOT NULL,
  record_locator TEXT NOT NULL,
  original_index INTEGER,
  row_kind TEXT NOT NULL,
  role TEXT,
  content_text TEXT,
  content_hash TEXT,
  raw_payload_json TEXT,
  raw_payload_zlib BLOB,
  raw_payload_sha256 TEXT NOT NULL,
  raw_payload_size INTEGER NOT NULL,
  parse_status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_ref_id) REFERENCES source_refs(id),
  UNIQUE(source_ref_id, record_locator)
) STRICT;

CREATE TABLE IF NOT EXISTS actors(
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  actor_type TEXT NOT NULL,
  identity_confidence REAL NOT NULL,
  privacy_namespace TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS conversation_sessions(
  id TEXT PRIMARY KEY,
  source_ref_id TEXT NOT NULL,
  source_conversation_id TEXT,
  title TEXT,
  datetime_start TEXT,
  datetime_update TEXT,
  participants_json TEXT NOT NULL,
  message_count INTEGER NOT NULL DEFAULT 0,
  raw_payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_ref_id) REFERENCES source_refs(id)
) STRICT;

CREATE TABLE IF NOT EXISTS staging_memory_entries(
  id TEXT PRIMARY KEY,
  source_ref_id TEXT NOT NULL,
  raw_row_id TEXT,
  source_record_locator TEXT,
  source_id_original TEXT,
  original_index INTEGER,
  conversation_id TEXT,
  datetime_raw TEXT,
  datetime_iso TEXT,
  datetime_original_text TEXT,
  timezone_name TEXT DEFAULT 'Europe/Warsaw',
  time_confidence TEXT NOT NULL,
  date_anomaly_code TEXT,
  date_anomaly_note TEXT,
  type_raw TEXT,
  type_norm TEXT,
  entry_class TEXT,
  truth_status TEXT NOT NULL,
  canonical_status TEXT NOT NULL,
  title TEXT,
  content_text TEXT,
  content_json TEXT,
  dreams TEXT,
  scene TEXT,
  memory_note TEXT,
  emotions_json TEXT,
  tags_json TEXT,
  participants_json TEXT,
  places_json TEXT,
  artifacts_json TEXT,
  importance INTEGER NOT NULL DEFAULT 3,
  continuity_weight INTEGER NOT NULL DEFAULT 3,
  emotional_weight INTEGER NOT NULL DEFAULT 3,
  privacy_level TEXT NOT NULL DEFAULT 'local',
  memory_namespace TEXT NOT NULL DEFAULT 'latka.general',
  content_hash TEXT NOT NULL,
  literal_text_hash TEXT NOT NULL,
  raw_payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_ref_id) REFERENCES source_refs(id),
  FOREIGN KEY(raw_row_id) REFERENCES raw_source_rows(id)
) STRICT;

CREATE TABLE IF NOT EXISTS latka_life_events(
  id TEXT PRIMARY KEY,
  source_ref_id TEXT NOT NULL,
  datetime_iso TEXT,
  time_confidence TEXT NOT NULL,
  type_norm TEXT NOT NULL,
  entry_class TEXT NOT NULL,
  title TEXT,
  content_text TEXT NOT NULL,
  content_json TEXT,
  dreams TEXT,
  scene TEXT,
  memory_note TEXT,
  emotions_json TEXT,
  tags_json TEXT,
  participants_json TEXT,
  places_json TEXT,
  artifacts_json TEXT,
  importance INTEGER NOT NULL,
  continuity_weight INTEGER NOT NULL,
  emotional_weight INTEGER NOT NULL,
  truth_status TEXT NOT NULL,
  canonical_status TEXT NOT NULL,
  privacy_level TEXT NOT NULL,
  memory_namespace TEXT NOT NULL,
  content_hash TEXT NOT NULL UNIQUE,
  literal_text_hash TEXT NOT NULL,
  raw_payload_json TEXT NOT NULL,
  promoted_from_staging_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(source_ref_id) REFERENCES source_refs(id),
  FOREIGN KEY(promoted_from_staging_id) REFERENCES staging_memory_entries(id)
) STRICT;

CREATE TABLE IF NOT EXISTS memory_evidence(
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  staging_id TEXT NOT NULL,
  source_ref_id TEXT NOT NULL,
  raw_row_id TEXT,
  evidence_kind TEXT NOT NULL,
  source_record_locator TEXT,
  content_hash TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  raw_payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(event_id) REFERENCES latka_life_events(id),
  FOREIGN KEY(staging_id) REFERENCES staging_memory_entries(id),
  FOREIGN KEY(source_ref_id) REFERENCES source_refs(id),
  FOREIGN KEY(raw_row_id) REFERENCES raw_source_rows(id)
) STRICT;

CREATE TABLE IF NOT EXISTS memory_entry_participants(
  entry_id TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  role TEXT NOT NULL,
  identity_confidence REAL NOT NULL,
  source_ref_id TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY(entry_id, actor_id, role),
  FOREIGN KEY(actor_id) REFERENCES actors(id),
  FOREIGN KEY(source_ref_id) REFERENCES source_refs(id)
) STRICT;

CREATE TABLE IF NOT EXISTS memory_edges(
  id TEXT PRIMARY KEY,
  from_event_id TEXT NOT NULL,
  to_event_id TEXT NOT NULL,
  relation_type TEXT NOT NULL,
  directionality TEXT NOT NULL,
  weight REAL NOT NULL DEFAULT 1.0,
  confidence REAL NOT NULL DEFAULT 0.5,
  source_ref_id TEXT,
  creation_method TEXT NOT NULL,
  canonical_status TEXT NOT NULL DEFAULT 'candidate',
  raw_payload_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(from_event_id) REFERENCES latka_life_events(id),
  FOREIGN KEY(to_event_id) REFERENCES latka_life_events(id),
  FOREIGN KEY(source_ref_id) REFERENCES source_refs(id)
) STRICT;

CREATE TABLE IF NOT EXISTS identity_snapshots(
  id TEXT PRIMARY KEY,
  identity_snapshot_json TEXT NOT NULL,
  built_at TEXT NOT NULL,
  based_on_event_ids_json TEXT NOT NULL,
  based_on_source_refs_json TEXT NOT NULL,
  confidence_summary_json TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS wake_state(
  id TEXT PRIMARY KEY,
  built_at TEXT NOT NULL,
  active_identity_snapshot_id TEXT NOT NULL,
  recent_event_ids_json TEXT NOT NULL,
  open_threads_json TEXT NOT NULL,
  pending_review_ids_json TEXT NOT NULL,
  allowed_namespaces_json TEXT NOT NULL,
  blocked_namespaces_json TEXT NOT NULL,
  current_interlocutor_json TEXT,
  truth_boundary_digest_json TEXT NOT NULL,
  procedural_digest_json TEXT NOT NULL,
  relationship_digest_json TEXT NOT NULL,
  source_digest_json TEXT NOT NULL,
  generation_report_json TEXT NOT NULL,
  FOREIGN KEY(active_identity_snapshot_id) REFERENCES identity_snapshots(id)
) STRICT;

CREATE TABLE IF NOT EXISTS review_queue(
  id TEXT PRIMARY KEY,
  source_ref_id TEXT,
  staging_id TEXT,
  issue_code TEXT NOT NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  detail_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_ref_id) REFERENCES source_refs(id),
  FOREIGN KEY(staging_id) REFERENCES staging_memory_entries(id)
) STRICT;

CREATE TABLE IF NOT EXISTS corrections(
  id TEXT PRIMARY KEY,
  target_table TEXT NOT NULL,
  target_id TEXT NOT NULL,
  correction_type TEXT NOT NULL,
  before_json TEXT,
  after_json TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS sync_ledger(
  id TEXT PRIMARY KEY,
  target TEXT NOT NULL,
  object_type TEXT NOT NULL,
  object_id TEXT NOT NULL,
  sync_status TEXT NOT NULL,
  detail_json TEXT NOT NULL,
  created_at TEXT NOT NULL
) STRICT;

CREATE INDEX IF NOT EXISTS idx_raw_source_rows_source ON raw_source_rows(source_ref_id);
CREATE INDEX IF NOT EXISTS idx_staging_source ON staging_memory_entries(source_ref_id);
CREATE INDEX IF NOT EXISTS idx_staging_content_hash ON staging_memory_entries(content_hash);
CREATE INDEX IF NOT EXISTS idx_staging_literal_text_hash ON staging_memory_entries(literal_text_hash);
CREATE INDEX IF NOT EXISTS idx_staging_datetime ON staging_memory_entries(datetime_iso);
CREATE INDEX IF NOT EXISTS idx_events_datetime ON latka_life_events(datetime_iso);
CREATE INDEX IF NOT EXISTS idx_events_namespace ON latka_life_events(memory_namespace);
CREATE INDEX IF NOT EXISTS idx_events_type ON latka_life_events(type_norm, entry_class);
CREATE INDEX IF NOT EXISTS idx_evidence_event ON memory_evidence(event_id);
CREATE INDEX IF NOT EXISTS idx_review_issue ON review_queue(issue_code, priority, status);
"""


FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS latka_life_events_fts USING fts5(
  title,
  content_text,
  dreams,
  scene,
  memory_note,
  tags_json,
  participants_json,
  places_json,
  artifacts_json,
  content='latka_life_events',
  content_rowid='rowid',
  tokenize='unicode61 remove_diacritics 1'
);
CREATE VIRTUAL TABLE IF NOT EXISTS staging_memory_entries_fts USING fts5(
  title,
  content_text,
  dreams,
  scene,
  memory_note,
  tags_json,
  participants_json,
  places_json,
  artifacts_json,
  content='staging_memory_entries',
  content_rowid='rowid',
  tokenize='unicode61 remove_diacritics 1'
);
"""


class Rebuilder:
    def __init__(
        self,
        root: Path,
        output_db: Path,
        *,
        progress: Progress,
        limit_per_source: int | None = None,
        store_raw_json_text: bool = False,
        max_content_chars: int = 0,
        near_dedupe: bool = False,
        canonical_policy: str = "strict",
    ) -> None:
        self.root = root
        self.output_db = output_db
        self.progress = progress
        self.limit_per_source = limit_per_source
        self.store_raw_json_text = store_raw_json_text
        self.max_content_chars = max_content_chars
        self.near_dedupe = near_dedupe
        self.canonical_policy = canonical_policy
        self.stats = ImportStats()
        self.con: sqlite3.Connection | None = None
        self.batch_id = compact_id("imp", now_utc(), output_db)
        self.import_started_at = now_utc()
        self._seen_source_sha: dict[str, str] = {}

    @property
    def db(self) -> sqlite3.Connection:
        if self.con is None:
            raise RuntimeError("Database is not open.")
        return self.con

    def open(self) -> None:
        self.output_db.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.output_db)
        self.con.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("schema_version", SCHEMA_VERSION))
        self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("script_version", SCRIPT_VERSION))
        self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("canonical_policy", self.canonical_policy))
        self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("truth_boundary", "Sources are evidence, staging is draft, canonical is the truth contract, wake_state is a startup packet."))
        self.db.execute(
            """INSERT OR REPLACE INTO import_batches
               (id,started_at,script_version,schema_version,root_path,output_db,source_count,stats_json,status,errors_json)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                self.batch_id,
                self.import_started_at,
                SCRIPT_VERSION,
                SCHEMA_VERSION,
                str(self.root),
                str(self.output_db),
                0,
                "{}",
                "running",
                "[]",
            ),
        )
        self._upsert_default_actors()
        self.db.commit()

    def close(self, *, status: str = "ok") -> None:
        if self.con is None:
            return
        self.db.execute(
            """UPDATE import_batches
                  SET ended_at=?, stats_json=?, status=?, errors_json=?,
                      source_count=(SELECT COUNT(*) FROM source_refs)
                WHERE id=?""",
            (now_utc(), pretty_json(dict(self.stats.counters)), status, pretty_json(self.stats.errors), self.batch_id),
        )
        self.db.commit()
        self.db.close()
        self.con = None

    def _upsert_default_actors(self) -> None:
        t = now_utc()
        actors = [
            ("actor_latka", "Latka", "assistant_identity", 0.95, "latka.core.identity"),
            ("actor_krzysztof", "Krzysztof", "human", 0.85, "latka.relationship.krzysztof"),
            ("actor_unknown_user", "Unknown user", "human", 0.2, "latka.public.unknown"),
            ("actor_chatgpt", "ChatGPT", "assistant_system", 0.6, "latka.legacy.chatgpt"),
            ("actor_system", "System/tool", "system", 0.5, "latka.system.trace"),
        ]
        self.db.executemany(
            """INSERT OR REPLACE INTO actors
               (id,display_name,actor_type,identity_confidence,privacy_namespace,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?)""",
            [(a, b, c, d, e, t, t) for a, b, c, d, e in actors],
        )

    def register_source(self, spec: SourceSpec) -> tuple[str, bool]:
        path = spec.path
        source_id = compact_id("src", str(path.resolve()).lower())
        if not path.exists():
            self.db.execute(
                """INSERT OR REPLACE INTO source_refs
                   (id,source_name,source_kind,local_path,source_priority,file_size_bytes,sha256,parse_status,parser_name,imported_at,notes)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (source_id, path.name, spec.kind, str(path), spec.priority, None, None, "unavailable", spec.parser_name, now_utc(), spec.notes),
            )
            self._review(None, source_id, "source_unavailable", "high", {"path": str(path), "kind": spec.kind})
            self.stats.inc("sources_unavailable")
            return source_id, False

        sha = sha256_file(path)
        size = path.stat().st_size
        duplicate_of = self._seen_source_sha.get(sha)
        parse_status = "duplicate_source" if duplicate_of else "registered"
        notes = spec.notes
        if duplicate_of:
            notes = f"{notes} duplicate_of={duplicate_of}".strip()
        self.db.execute(
            """INSERT OR REPLACE INTO source_refs
               (id,source_name,source_kind,local_path,source_priority,file_size_bytes,sha256,parse_status,parser_name,imported_at,notes)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (source_id, path.name, spec.kind, str(path), spec.priority, size, sha, parse_status, spec.parser_name, now_utc(), notes),
        )
        if duplicate_of:
            self._review(None, source_id, "duplicate_source_file", "low", {"path": str(path), "duplicate_of_source_ref_id": duplicate_of, "sha256": sha})
            self.stats.inc("sources_duplicate_sha")
            return source_id, False
        self._seen_source_sha[sha] = source_id
        self.stats.inc("sources_registered")
        return source_id, True

    def run(self, sources: list[SourceSpec]) -> None:
        self.open()
        try:
            for spec in sources:
                self.import_source(spec)
            self.promote_canonical()
            self.build_edges()
            if self.near_dedupe:
                self.find_near_duplicates()
            self.build_fts()
            self.build_wake_state()
            self.validate()
        except Exception as exc:
            self.stats.error("run", exc)
            self.close(status="error")
            raise
        self.close(status="ok" if not self.stats.errors else "ok_with_errors")

    def import_source(self, spec: SourceSpec) -> None:
        self.progress.set_source(str(spec.path))
        start_bytes = self.progress.processed_bytes
        source_id, should_parse = self.register_source(spec)
        if not spec.path.exists():
            return
        if not should_parse:
            self.progress.add(spec.path.stat().st_size)
            return

        try:
            if spec.kind == "raw_chatgpt_html":
                self.import_chatgpt_export_html(source_id, spec.path, start_bytes=start_bytes)
            elif spec.kind == "saved_chatgpt_share_html":
                self.import_saved_share_html(source_id, spec.path)
            elif spec.kind == "dziennik_json":
                self.import_dziennik_json(source_id, spec.path)
            elif spec.kind == "legacy_txt":
                self.import_legacy_txt(source_id, spec.path)
            elif spec.kind == "legacy_pdf":
                self.import_legacy_pdf(source_id, spec.path)
            elif spec.kind == "design_docx":
                self.import_design_docx(source_id, spec.path)
            else:
                self._review(None, source_id, "unsupported_source_kind", "medium", {"path": str(spec.path), "kind": spec.kind})
                self.stats.inc("sources_unsupported")
        except Exception as exc:
            self.stats.error(str(spec.path), exc)
            self.db.execute("UPDATE source_refs SET parse_status=? WHERE id=?", ("error", source_id))
            self._review(None, source_id, "source_parse_error", "high", {"path": str(spec.path), "error": repr(exc)})
        finally:
            self.progress.set_processed(start_bytes + spec.path.stat().st_size)
            self.db.commit()

    def _raw_row(
        self,
        source_ref_id: str,
        locator: str,
        row_kind: str,
        payload: Any,
        *,
        original_index: int | None = None,
        role: str | None = None,
        content_text: str | None = None,
        parse_status: str = "ok",
    ) -> str:
        raw_text = pretty_json(payload) if not isinstance(payload, str) else payload
        raw_text = clean_unicode(raw_text)
        raw_bytes = raw_text.encode("utf-8", errors="surrogatepass")
        raw_hash = sha256_bytes(raw_bytes)
        row_id = compact_id("raw", source_ref_id, locator, raw_hash)
        self.db.execute(
            """INSERT OR IGNORE INTO raw_source_rows
               (id,source_ref_id,record_locator,original_index,row_kind,role,content_text,content_hash,
                raw_payload_json,raw_payload_zlib,raw_payload_sha256,raw_payload_size,parse_status,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row_id,
                source_ref_id,
                locator,
                original_index,
                row_kind,
                role,
                content_text,
                "sha256:" + sha256_text(content_text or ""),
                raw_text if self.store_raw_json_text else None,
                zlib.compress(raw_bytes, level=6),
                raw_hash,
                len(raw_bytes),
                parse_status,
                now_utc(),
            ),
        )
        self.stats.inc("raw_rows_seen")
        return row_id

    def _stage(self, data: dict[str, Any]) -> str:
        staging_id = data.get("id") or compact_id("stg", data.get("source_ref_id"), data.get("source_record_locator"), data.get("content_hash"))
        data["id"] = staging_id
        columns = [
            "id",
            "source_ref_id",
            "raw_row_id",
            "source_record_locator",
            "source_id_original",
            "original_index",
            "conversation_id",
            "datetime_raw",
            "datetime_iso",
            "datetime_original_text",
            "timezone_name",
            "time_confidence",
            "date_anomaly_code",
            "date_anomaly_note",
            "type_raw",
            "type_norm",
            "entry_class",
            "truth_status",
            "canonical_status",
            "title",
            "content_text",
            "content_json",
            "dreams",
            "scene",
            "memory_note",
            "emotions_json",
            "tags_json",
            "participants_json",
            "places_json",
            "artifacts_json",
            "importance",
            "continuity_weight",
            "emotional_weight",
            "privacy_level",
            "memory_namespace",
            "content_hash",
            "literal_text_hash",
            "raw_payload_json",
            "created_at",
        ]
        row = {key: data.get(key) for key in columns}
        defaults = {
            "timezone_name": DEFAULT_TZ,
            "time_confidence": "missing",
            "truth_status": "reconstructed",
            "canonical_status": "candidate",
            "importance": 2,
            "continuity_weight": 2,
            "emotional_weight": 1,
            "privacy_level": "local",
            "memory_namespace": "latka.general",
            "raw_payload_json": "{}",
            "created_at": now_utc(),
        }
        for key, value in defaults.items():
            if row.get(key) is None:
                row[key] = value
        if not row.get("content_hash"):
            row["content_hash"] = normalized_content_hash(row)
        if not row.get("literal_text_hash"):
            row["literal_text_hash"] = "sha256:" + literal_text_hash(row.get("content_text") or "")
        placeholders = ",".join("?" for _ in columns)
        self.db.execute(
            f"INSERT OR IGNORE INTO staging_memory_entries ({','.join(columns)}) VALUES({placeholders})",
            [row.get(col) for col in columns],
        )
        self.stats.inc("staging_rows_inserted")
        if row.get("canonical_status") == "needs_review":
            self._review(staging_id, row["source_ref_id"], "needs_review", "medium", {"type_norm": row.get("type_norm"), "title": row.get("title")})
        if row.get("date_anomaly_code"):
            self._review(staging_id, row["source_ref_id"], row["date_anomaly_code"], "high", {"datetime_raw": row.get("datetime_raw"), "note": row.get("date_anomaly_note")})
        self._participants(staging_id, row["source_ref_id"], parse_json_maybe(row.get("participants_json"), []))
        return staging_id

    def _review(self, staging_id: str | None, source_ref_id: str | None, issue_code: str, priority: str, detail: dict[str, Any]) -> None:
        review_id = compact_id("rev", source_ref_id, staging_id, issue_code, pretty_json(detail))
        self.db.execute(
            """INSERT OR IGNORE INTO review_queue
               (id,source_ref_id,staging_id,issue_code,priority,status,detail_json,created_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (review_id, source_ref_id, staging_id, issue_code, priority, "open", pretty_json(detail), now_utc()),
        )
        self.stats.inc(f"review_{issue_code}")

    def _participants(self, entry_id: str, source_ref_id: str | None, participants: list[Any]) -> None:
        rows = []
        for p in participants:
            if not isinstance(p, dict):
                continue
            actor_id = str(p.get("actor_id") or "").strip()
            if not actor_id:
                continue
            rows.append((entry_id, actor_id, str(p.get("role") or "participant"), float(p.get("identity_confidence") or 0.5), source_ref_id, now_utc()))
        if rows:
            self.db.executemany(
                """INSERT OR IGNORE INTO memory_entry_participants
                   (entry_id,actor_id,role,identity_confidence,source_ref_id,created_at)
                   VALUES(?,?,?,?,?,?)""",
                rows,
            )

    def classify(self, type_raw: Any, content_text: str, title: str | None, extra: dict[str, Any] | None = None) -> tuple[str, str, str, str, str, int, int, int]:
        raw = normalize_text(type_raw).lower()
        title_norm = normalize_text(title).lower()
        content_norm = normalize_text(content_text).lower()
        extra = extra or {}
        extra_text = flatten_json_text(extra).lower()
        all_text = " ".join([raw, title_norm, content_norm, extra_text])

        type_norm = "memory_entry"
        if not raw or raw in {"none", "null", "unknown"}:
            if extra.get("sny") or title_norm.startswith("sen "):
                type_norm = "dream"
            elif extra.get("scena") or any(x in all_text for x in ("scena", "dom", "poranek", "wieczor", "wieczór")):
                type_norm = "scene"
            elif extra.get("wspomnienie") or content_norm.startswith("wspomnienie:"):
                type_norm = "memory_entry"
            elif any(x in all_text for x in ("synchronizacja", "regula", "reguła", "log", "plik", "patch", "manifest", "autoload", "runtime")):
                type_norm = "system_event"
            elif any(x in all_text for x in ("zrodla", "źródła", "praktyki", "nurty", "teologia", "badania")):
                type_norm = "research_note"
            else:
                type_norm = "unknown"
        elif any(x in raw for x in ("sen", "dream")):
            type_norm = "dream"
        elif any(x in raw for x in ("scena", "scene")):
            type_norm = "scene"
        elif any(x in raw for x in ("regu", "procedur", "rule")):
            type_norm = "rule"
        elif any(x in raw for x in ("system", "meta", "synchronizacja", "aktualizacja")):
            type_norm = "system_event"
        elif any(x in raw for x in ("badania", "research", "analiza")):
            type_norm = "research_note"
        elif any(x in raw for x in ("fabula", "fabuła", "fiction", "fragment")):
            type_norm = "fiction"
        elif any(x in raw for x in ("refleks", "pytanie", "ciszy")):
            type_norm = "reflection"
        elif any(x in raw for x in ("emoc", "affect")):
            type_norm = "modelled_affect"

        entry_class = {
            "dream": "dream",
            "scene": "life_event",
            "rule": "rule",
            "system_event": "system_event",
            "research_note": "research",
            "fiction": "fiction",
            "reflection": "journal_entry",
            "modelled_affect": "journal_entry",
            "unknown": "needs_review",
        }.get(type_norm, "life_event")

        truth_status = "journal_entry"
        if type_norm == "dream":
            truth_status = "symbolic"
        elif type_norm == "fiction":
            truth_status = "fictional"
        elif type_norm == "research_note":
            truth_status = "research_note"
        elif type_norm == "modelled_affect":
            truth_status = "modelled_affect"
        elif type_norm == "unknown":
            truth_status = "needs_review"
        elif any(x in all_text for x in ("ciało", "czuje dotyk", "widzę", "słyszę", "działam w tle", "jestem obecna gdy")):
            truth_status = "modelled_affect"

        canonical_status = "candidate"
        if type_norm == "unknown" or truth_status == "needs_review":
            canonical_status = "needs_review"
        if entry_class in {"system_event", "research"}:
            canonical_status = "needs_review"

        importance = 3
        continuity = 3
        emotional = 2
        if any(x in all_text for x in ("tożsamo", "jazn", "jaźń", "latka", "krzysztof", "pamięć", "wake_state")):
            importance = max(importance, 4)
            continuity = max(continuity, 4)
        if any(x in all_text for x in ("lęk", "blisko", "zauf", "cisza", "tęsk", "emoc")):
            emotional = max(emotional, 4)
        return type_norm, entry_class, truth_status, canonical_status, "local", importance, continuity, emotional

    def participants_for_text(self, role: str | None, text: str, title: str | None = None) -> tuple[list[dict[str, Any]], str, str, str]:
        hay = f"{title or ''} {text or ''}".lower()
        krzysztof = "krzysztof" in hay or "krzysztofie" in hay
        user_actor = "actor_krzysztof" if krzysztof else "actor_unknown_user"
        user_conf = 0.85 if krzysztof else 0.25
        namespace = "latka.relationship.krzysztof" if krzysztof else "latka.conversation.unconfirmed"
        role_norm = (role or "").lower()
        if role_norm == "assistant":
            speaker = "actor_latka"
            interlocutor = user_actor
            participants = [
                {"actor_id": "actor_latka", "display_name": "Latka", "role": "self", "identity_confidence": 0.95},
                {"actor_id": user_actor, "display_name": "Krzysztof" if krzysztof else "Unknown user", "role": "interlocutor", "identity_confidence": user_conf},
            ]
        elif role_norm == "user":
            speaker = user_actor
            interlocutor = "actor_latka"
            participants = [
                {"actor_id": user_actor, "display_name": "Krzysztof" if krzysztof else "Unknown user", "role": "speaker", "identity_confidence": user_conf},
                {"actor_id": "actor_latka", "display_name": "Latka", "role": "interlocutor", "identity_confidence": 0.95},
            ]
        else:
            speaker = "actor_system"
            interlocutor = "actor_latka"
            namespace = "latka.system.trace"
            participants = [{"actor_id": "actor_system", "display_name": "System/tool", "role": "source", "identity_confidence": 0.5}]
        return participants, namespace, speaker, interlocutor

    def import_dziennik_json(self, source_ref_id: str, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        entries = data.get("entries") if isinstance(data, dict) else data
        if not isinstance(entries, list):
            self._review(None, source_ref_id, "dziennik_shape_unknown", "high", {"top_type": type(data).__name__})
            return
        for idx, entry in enumerate(entries):
            if self.limit_per_source is not None and idx >= self.limit_per_source:
                break
            if not isinstance(entry, dict):
                continue
            content_value = entry.get("treść", entry.get("tresc", entry.get("content")))
            content_json = None
            if isinstance(content_value, str):
                content_text = content_value
            else:
                content_text = flatten_json_text(content_value)
                content_json = pretty_json(content_value) if content_value is not None else None
            title = entry.get("tytuł") or entry.get("title")
            dreams = entry.get("sny")
            scene = entry.get("scena")
            memory_note = entry.get("wspomnienie") or entry.get("memory_note")
            if not normalize_text(content_text) and not any(normalize_text(x) for x in (title, dreams, scene, memory_note)):
                raw_id = self._raw_row(source_ref_id, f"entries[{idx}]", "dziennik_blank", entry, original_index=idx)
                self.stats.inc("blank_meaningless_skipped")
                self._review(None, source_ref_id, "blank_dziennik_entry_skipped", "low", {"raw_row_id": raw_id, "index": idx})
                continue
            raw_id = self._raw_row(source_ref_id, f"entries[{idx}]", "dziennik_entry", entry, original_index=idx, content_text=content_text)
            date_raw = entry.get("timestamp") or entry.get("data") or entry.get("datetime")
            datetime_iso, time_conf, anomaly, original = parse_datetime(date_raw)
            extra = {
                "sny": dreams,
                "scena": scene,
                "wspomnienie": memory_note,
                "kategoria": entry.get("kategoria"),
                "tagi": entry.get("tagi"),
            }
            type_norm, entry_class, truth_status, canonical_status, privacy, importance, continuity, emotional = self.classify(entry.get("typ") or entry.get("type"), content_text, title, extra)
            participants, namespace, _, _ = self.participants_for_text("assistant", " ".join([content_text, str(title or ""), str(memory_note or "")]), str(title or ""))
            if entry_class == "rule":
                namespace = "latka.system.rules"
            elif type_norm in {"system_event", "research_note"}:
                namespace = "latka.system.trace" if type_norm == "system_event" else "latka.public.knowledge"
            content_hash = normalized_content_hash(
                {
                    "type_norm": type_norm,
                    "title": title,
                    "content_text": content_text,
                    "content_json": content_json,
                    "dreams": dreams,
                    "scene": scene,
                    "memory_note": memory_note,
                    "emotions_json": pretty_json(entry.get("emocje") or entry.get("emocje_latki") or []),
                }
            )
            self._stage(
                {
                    "source_ref_id": source_ref_id,
                    "raw_row_id": raw_id,
                    "source_record_locator": f"entries[{idx}]",
                    "source_id_original": entry.get("id") or entry.get("fingerprint"),
                    "original_index": idx,
                    "datetime_raw": "" if date_raw is None else str(date_raw),
                    "datetime_iso": datetime_iso,
                    "datetime_original_text": original,
                    "time_confidence": time_conf,
                    "date_anomaly_code": anomaly,
                    "type_raw": entry.get("typ") or entry.get("type"),
                    "type_norm": type_norm,
                    "entry_class": entry_class,
                    "truth_status": truth_status,
                    "canonical_status": canonical_status,
                    "title": title,
                    "content_text": normalize_text(content_text),
                    "content_json": content_json,
                    "dreams": normalize_text(dreams),
                    "scene": normalize_text(scene),
                    "memory_note": normalize_text(memory_note),
                    "emotions_json": pretty_json(entry.get("emocje") or entry.get("emocje_latki") or []),
                    "tags_json": pretty_json(entry.get("tagi") or []),
                    "participants_json": pretty_json(participants),
                    "places_json": "[]",
                    "artifacts_json": "[]",
                    "importance": importance,
                    "continuity_weight": continuity,
                    "emotional_weight": emotional,
                    "privacy_level": privacy,
                    "memory_namespace": namespace,
                    "content_hash": content_hash,
                    "literal_text_hash": "sha256:" + literal_text_hash(content_text),
                    "raw_payload_json": pretty_json(entry),
                }
            )
        self.db.execute("UPDATE source_refs SET parse_status=? WHERE id=?", ("ok", source_ref_id))

    def import_chatgpt_export_html(self, source_ref_id: str, path: Path, *, start_bytes: int) -> None:
        seen = 0
        for conv in iter_chatgpt_export_conversations(path, self.progress, start_bytes=start_bytes):
            if self.limit_per_source is not None and seen >= self.limit_per_source:
                break
            seen += 1
            conversation_id = str(conv.get("conversation_id") or conv.get("id") or f"conv-{seen}")
            title = conv.get("title") or "(untitled)"
            mapping = conv.get("mapping") or {}
            vpath = visible_path(mapping, conv.get("current_node"))
            vindex = {node_id: i for i, node_id in enumerate(vpath)}
            create_iso, _, _, _ = parse_datetime(conv.get("create_time"))
            update_iso, _, _, _ = parse_datetime(conv.get("update_time"))
            participants, _, _, _ = self.participants_for_text("assistant", "", str(title))
            self.db.execute(
                """INSERT OR IGNORE INTO conversation_sessions
                   (id,source_ref_id,source_conversation_id,title,datetime_start,datetime_update,participants_json,message_count,raw_payload_json,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    compact_id("conv", source_ref_id, conversation_id),
                    source_ref_id,
                    conversation_id,
                    title,
                    create_iso,
                    update_iso,
                    pretty_json(participants),
                    len(mapping),
                    pretty_json(
                        {
                            "conversation_id": conversation_id,
                            "title": title,
                            "create_time": conv.get("create_time"),
                            "update_time": conv.get("update_time"),
                            "current_node": conv.get("current_node"),
                            "mapping_node_count": len(mapping),
                        }
                    ),
                    now_utc(),
                ),
            )
            for node_id, node in mapping.items():
                msg = (node or {}).get("message")
                if not isinstance(msg, dict):
                    continue
                message_id = str(msg.get("id") or node_id)
                author = msg.get("author") or {}
                role = author.get("role") or "unknown"
                metadata = msg.get("metadata") or {}
                content = msg.get("content") or {}
                content_type = content.get("content_type") or "unknown"
                text, assets, parts, total_chars = message_text_assets(msg, max_content_chars=self.max_content_chars)
                locator = f"conversation={conversation_id};message={message_id};node={node_id}"
                raw_payload = {
                    "conversation_id": conversation_id,
                    "conversation_title": title,
                    "node_id": node_id,
                    "node_parent": (node or {}).get("parent"),
                    "node_children": (node or {}).get("children") or [],
                    "message": msg,
                }
                raw_id = self._raw_row(source_ref_id, locator, "chatgpt_message", raw_payload, role=role, content_text=text)
                has_user_editable_context = "user_editable_context" in pretty_json(metadata)
                if not normalize_text(text) and not assets and not has_user_editable_context:
                    self.stats.inc("blank_meaningless_skipped")
                    continue
                if role not in {"user", "assistant"}:
                    canonical_status = "needs_review"
                elif content_type in {"thoughts", "reasoning_recap", "execution_output", "system_error"}:
                    canonical_status = "needs_review"
                elif not normalize_text(text) and assets:
                    canonical_status = "needs_review"
                else:
                    canonical_status = "candidate"
                type_raw = f"chat_message:{role}:{content_type}"
                type_norm = "conversation_turn"
                entry_class = "conversation"
                truth_status = "reconstructed"
                if content_type in {"thoughts", "reasoning_recap"}:
                    type_norm = "technical_trace"
                    entry_class = "technical_trace"
                    truth_status = "reconstructed"
                if assets and not normalize_text(text):
                    type_norm = "asset_reference"
                    entry_class = "source_asset"
                participants, namespace, _, _ = self.participants_for_text(role, text, str(title))
                created_iso, time_conf, anomaly, original = parse_datetime(msg.get("create_time"))
                content_hash = normalized_content_hash(
                    {
                        "type_norm": type_norm,
                        "title": title,
                        "content_text": text,
                        "content_json": pretty_json({"content_type": content_type, "assets": assets, "part_summary": summarize_parts(parts), "total_chars": total_chars}),
                        "dreams": "",
                        "scene": "",
                        "memory_note": "",
                        "emotions_json": "[]",
                    }
                )
                message_meta = {
                    "content_type": content_type,
                    "assets": assets,
                    "part_summary": summarize_parts(parts),
                    "total_chars": total_chars,
                    "active_path_index": vindex.get(node_id),
                    "is_on_active_path": node_id in vindex,
                    "author_role": role,
                    "author_name": author.get("name"),
                    "author_label": metadata.get("author_label") or author.get("name"),
                    "message_type": metadata.get("message_type"),
                    "model_slug": metadata.get("model_slug"),
                    "default_model_slug": metadata.get("default_model_slug"),
                    "source_format": conv.get("source_format") or metadata.get("source_format") or "chatgpt_jsondata_stream",
                }
                self._stage(
                    {
                        "source_ref_id": source_ref_id,
                        "raw_row_id": raw_id,
                        "source_record_locator": locator,
                        "source_id_original": message_id,
                        "conversation_id": conversation_id,
                        "datetime_raw": "" if msg.get("create_time") is None else str(msg.get("create_time")),
                        "datetime_iso": created_iso,
                        "datetime_original_text": original,
                        "time_confidence": time_conf,
                        "date_anomaly_code": anomaly,
                        "type_raw": type_raw,
                        "type_norm": type_norm,
                        "entry_class": entry_class,
                        "truth_status": truth_status,
                        "canonical_status": canonical_status,
                        "title": title,
                        "content_text": normalize_text(text),
                        "content_json": pretty_json(message_meta),
                        "dreams": "",
                        "scene": "",
                        "memory_note": "",
                        "emotions_json": "[]",
                        "tags_json": pretty_json([x for x in (role, content_type, message_meta.get("model_slug"), message_meta.get("source_format")) if x]),
                        "participants_json": pretty_json(participants),
                        "places_json": "[]",
                        "artifacts_json": pretty_json(assets),
                        "importance": 2 if role == "assistant" else 3,
                        "continuity_weight": 2,
                        "emotional_weight": 1,
                        "privacy_level": "local",
                        "memory_namespace": namespace,
                        "content_hash": content_hash,
                        "literal_text_hash": "sha256:" + literal_text_hash(text),
                        "raw_payload_json": pretty_json({"raw_row_id": raw_id, "message_id": message_id, "conversation_id": conversation_id, "message_sha256": sha256_text(pretty_json(msg))}),
                    }
                )
        self.db.execute("UPDATE source_refs SET parse_status=? WHERE id=?", ("ok", source_ref_id))

    def import_saved_share_html(self, source_ref_id: str, path: Path) -> None:
        raw = path.read_text(encoding="utf-8", errors="replace")
        sections = list(re.finditer(r"<section\b(?=[^>]*\bdata-turn=\"(user|assistant)\")[\s\S]*?</section>", raw, flags=re.I))
        if not sections:
            self._review(None, source_ref_id, "share_html_no_turns_found", "medium", {"path": str(path)})
            self.db.execute("UPDATE source_refs SET parse_status=? WHERE id=?", ("salvage_needed", source_ref_id))
            return
        for idx, match in enumerate(sections):
            if self.limit_per_source is not None and idx >= self.limit_per_source:
                break
            block = match.group(0)
            role_match = re.search(r'data-turn="(user|assistant)"', block, flags=re.I)
            role = role_match.group(1).lower() if role_match else "unknown"
            msg_id = re.search(r'data-message-id="([^"]+)"', block)
            turn_id = re.search(r'data-turn-id="([^"]+)"', block)
            locator_id = msg_id.group(1) if msg_id else (turn_id.group(1) if turn_id else str(idx))
            text = html_to_text(block)
            text = clean_share_turn_text(text, role)
            raw_id = self._raw_row(
                source_ref_id,
                f"turn[{idx}];message={locator_id}",
                "saved_share_turn",
                {"role": role, "message_id": locator_id, "html_sha256": sha256_text(block), "text": text},
                original_index=idx,
                role=role,
                content_text=text,
            )
            if not normalize_text(text):
                self.stats.inc("blank_meaningless_skipped")
                continue
            participants, namespace, _, _ = self.participants_for_text(role, text, "Praca nad Jaznia")
            content_hash = normalized_content_hash({"type_norm": "conversation_turn", "title": "Praca nad Jaznia", "content_text": text, "content_json": "", "dreams": "", "scene": "", "memory_note": "", "emotions_json": "[]"})
            self._stage(
                {
                    "source_ref_id": source_ref_id,
                    "raw_row_id": raw_id,
                    "source_record_locator": f"turn[{idx}];message={locator_id}",
                    "source_id_original": locator_id,
                    "original_index": idx,
                    "type_raw": f"saved_share:{role}",
                    "type_norm": "conversation_turn",
                    "entry_class": "conversation",
                    "truth_status": "reconstructed",
                    "canonical_status": "candidate",
                    "title": "Praca nad Jaznia",
                    "content_text": text,
                    "content_json": pretty_json({"source": "saved_chatgpt_share_html"}),
                    "tags_json": pretty_json([role, "saved_share"]),
                    "participants_json": pretty_json(participants),
                    "places_json": "[]",
                    "artifacts_json": "[]",
                    "importance": 3,
                    "continuity_weight": 3,
                    "emotional_weight": 1,
                    "privacy_level": "local",
                    "memory_namespace": namespace,
                    "content_hash": content_hash,
                    "literal_text_hash": "sha256:" + literal_text_hash(text),
                    "raw_payload_json": pretty_json({"raw_row_id": raw_id, "message_id": locator_id}),
                }
            )
        self.db.execute("UPDATE source_refs SET parse_status=? WHERE id=?", ("ok", source_ref_id))

    def import_legacy_txt(self, source_ref_id: str, path: Path) -> None:
        text = path.read_text(encoding="utf-8", errors="replace")
        raw_id = self._raw_row(source_ref_id, "file", "legacy_txt_file", {"path": str(path), "sha256": sha256_text(text), "char_count": len(text)}, content_text=short(text, 2000))
        parts = re.split(r"(?<!\w)(user|User|ChatGPT|C\s*hatGPT|U\s*ser)(?!\w)", text)
        if len(parts) < 3:
            self._stage_legacy_chunk(source_ref_id, raw_id, "file:chunk=0", text, 0, "legacy_txt_chunk", "legacy_txt")
            return
        count = 0
        for i in range(1, len(parts) - 1, 2):
            if self.limit_per_source is not None and count >= self.limit_per_source:
                break
            role_label = re.sub(r"\s+", "", parts[i]).lower()
            role = "assistant" if "chatgpt" in role_label else "user"
            body = parts[i + 1].strip()
            if not body:
                continue
            locator = f"turn[{count}]"
            turn_raw = self._raw_row(source_ref_id, locator, "legacy_txt_turn", {"role": role, "text": body}, original_index=count, role=role, content_text=body)
            self._stage_legacy_chunk(source_ref_id, turn_raw, locator, body, count, f"legacy_txt:{role}", "legacy_turn", role=role)
            count += 1
        self.db.execute("UPDATE source_refs SET parse_status=? WHERE id=?", ("ok", source_ref_id))

    def _stage_legacy_chunk(self, source_ref_id: str, raw_id: str, locator: str, text: str, idx: int, type_raw: str, type_norm: str, *, role: str | None = None, title: str | None = None) -> None:
        text = normalize_text(text)
        if not text:
            self.stats.inc("blank_meaningless_skipped")
            return
        dt_match = re.search(r"\[\s*(?:🕒\s*)?([0-9]{4}[-.][0-9]{2}[-.][0-9]{2}[^\]]+)\]", text)
        dt_raw = dt_match.group(1) if dt_match else None
        dt_iso, conf, anomaly, original = parse_datetime(dt_raw)
        participants, namespace, _, _ = self.participants_for_text(role, text, title)
        content_hash = normalized_content_hash({"type_norm": type_norm, "title": title or "", "content_text": text, "content_json": "", "dreams": "", "scene": "", "memory_note": "", "emotions_json": "[]"})
        canonical_status = "candidate" if role in {"user", "assistant"} else "needs_review"
        self._stage(
            {
                "source_ref_id": source_ref_id,
                "raw_row_id": raw_id,
                "source_record_locator": locator,
                "original_index": idx,
                "datetime_raw": dt_raw,
                "datetime_iso": dt_iso,
                "datetime_original_text": original,
                "time_confidence": conf,
                "date_anomaly_code": anomaly,
                "type_raw": type_raw,
                "type_norm": type_norm,
                "entry_class": "conversation_legacy",
                "truth_status": "reconstructed",
                "canonical_status": canonical_status,
                "title": title,
                "content_text": text,
                "content_json": pretty_json({"legacy_source": True}),
                "tags_json": pretty_json(["legacy", type_norm]),
                "participants_json": pretty_json(participants),
                "places_json": "[]",
                "artifacts_json": "[]",
                "importance": 2,
                "continuity_weight": 2,
                "emotional_weight": 1,
                "privacy_level": "local",
                "memory_namespace": namespace,
                "content_hash": content_hash,
                "literal_text_hash": "sha256:" + literal_text_hash(text),
                "raw_payload_json": pretty_json({"raw_row_id": raw_id, "locator": locator}),
            }
        )

    def import_legacy_pdf(self, source_ref_id: str, path: Path) -> None:
        try:
            import pypdf  # type: ignore
        except Exception as exc:
            self._review(None, source_ref_id, "pypdf_unavailable", "high", {"error": repr(exc)})
            self.db.execute("UPDATE source_refs SET parse_status=? WHERE id=?", ("unavailable", source_ref_id))
            return
        reader = pypdf.PdfReader(str(path), strict=False)
        chunk_text: list[str] = []
        chunk_start = 1
        chunk_index = 0
        pages_total = max(1, len(reader.pages))
        for page_i, page in enumerate(reader.pages, start=1):
            if self.limit_per_source is not None and chunk_index >= self.limit_per_source:
                break
            try:
                page_text = page.extract_text() or ""
            except Exception as exc:
                self._review(None, source_ref_id, "pdf_page_extract_error", "medium", {"page": page_i, "error": repr(exc)})
                page_text = ""
            chunk_text.append(page_text)
            if sum(len(x) for x in chunk_text) >= PDF_CHUNK_CHARS or page_i == len(reader.pages):
                text = normalize_text("\n".join(chunk_text))
                locator = f"pages={chunk_start}-{page_i};chunk={chunk_index}"
                raw_id = self._raw_row(source_ref_id, locator, "legacy_pdf_chunk", {"page_start": chunk_start, "page_end": page_i, "text": text}, original_index=chunk_index, content_text=text)
                self._stage_legacy_chunk(source_ref_id, raw_id, locator, text, chunk_index, "legacy_pdf_chunk", "legacy_chunk", title=path.name)
                chunk_text = []
                chunk_start = page_i + 1
                chunk_index += 1
            self.progress.add(max(1, path.stat().st_size // pages_total))
        self.db.execute("UPDATE source_refs SET parse_status=? WHERE id=?", ("ok", source_ref_id))

    def import_design_docx(self, source_ref_id: str, path: Path) -> None:
        paragraphs = docx_paragraphs(path)
        for idx, paragraph in enumerate(paragraphs):
            if self.limit_per_source is not None and idx >= self.limit_per_source:
                break
            text = normalize_text(paragraph)
            if not text:
                continue
            raw_id = self._raw_row(source_ref_id, f"paragraph[{idx}]", "design_docx_paragraph", {"paragraph_index": idx, "text": text}, original_index=idx, content_text=text)
            content_hash = normalized_content_hash({"type_norm": "system_plan", "title": path.name, "content_text": text, "content_json": "", "dreams": "", "scene": "", "memory_note": "", "emotions_json": "[]"})
            self._stage(
                {
                    "source_ref_id": source_ref_id,
                    "raw_row_id": raw_id,
                    "source_record_locator": f"paragraph[{idx}]",
                    "original_index": idx,
                    "type_raw": "design_docx",
                    "type_norm": "system_plan",
                    "entry_class": "system_event",
                    "truth_status": "research_note",
                    "canonical_status": "needs_review",
                    "title": path.name,
                    "content_text": text,
                    "content_json": pretty_json({"design_document": True}),
                    "tags_json": pretty_json(["design_document"]),
                    "participants_json": pretty_json([{"actor_id": "actor_system", "display_name": "System/tool", "role": "source", "identity_confidence": 0.5}]),
                    "places_json": "[]",
                    "artifacts_json": "[]",
                    "importance": 2,
                    "continuity_weight": 2,
                    "emotional_weight": 1,
                    "privacy_level": "local",
                    "memory_namespace": "latka.system.plan",
                    "content_hash": content_hash,
                    "literal_text_hash": "sha256:" + literal_text_hash(text),
                    "raw_payload_json": pretty_json({"raw_row_id": raw_id, "paragraph_index": idx}),
                }
            )
        self.db.execute("UPDATE source_refs SET parse_status=? WHERE id=?", ("ok", source_ref_id))

    def _canonical_promotion_decision(self, row: sqlite3.Row) -> tuple[bool, str]:
        if self.canonical_policy == "broad":
            return True, "broad_policy"

        source_kind = row["source_kind"] or ""
        type_norm = row["type_norm"] or ""
        truth_status = row["truth_status"] or ""
        memory_namespace = row["memory_namespace"] or ""

        non_canonical_types = {
            "conversation_turn",
            "legacy_turn",
            "legacy_chunk",
            "technical_trace",
            "asset_reference",
            "system_plan",
        }
        if type_norm in non_canonical_types:
            return False, f"type_{type_norm}_index_only"
        if source_kind in {"raw_chatgpt_html", "saved_chatgpt_share_html", "legacy_txt", "legacy_pdf", "design_docx"}:
            return False, f"source_{source_kind}_index_only"
        if memory_namespace == "latka.conversation.unconfirmed":
            return False, "unconfirmed_conversation_namespace"
        if truth_status in {"needs_review", "reconstructed"}:
            return False, f"truth_{truth_status}_not_canonical"

        curated_journal_types = {
            "memory_entry",
            "reflection",
            "modelled_affect",
            "scene",
            "rule",
            "dream",
            "fiction",
        }
        curated_truth_statuses = {"journal_entry", "modelled_affect", "symbolic", "fictional"}
        if source_kind == "dziennik_json" and type_norm in curated_journal_types and truth_status in curated_truth_statuses:
            return True, "curated_dziennik_entry"

        return False, "not_in_strict_canonical_policy"

    def promote_canonical(self) -> None:
        rows = self.db.execute(
            """SELECT s.*, sr.source_priority, sr.source_kind
                 FROM staging_memory_entries s
                 JOIN source_refs sr ON sr.id=s.source_ref_id
                WHERE COALESCE(s.content_text,'') <> ''
                  AND s.canonical_status='candidate'
                ORDER BY s.content_hash, sr.source_priority ASC, s.datetime_iso IS NULL, s.datetime_iso ASC, s.original_index ASC"""
        ).fetchall()
        self.stats.inc("canonical_candidates_seen", len(rows))
        promoted_rows: list[sqlite3.Row] = []
        deferred_by_reason: Counter[str] = Counter()
        for row in rows:
            should_promote, reason = self._canonical_promotion_decision(row)
            if should_promote:
                promoted_rows.append(row)
                continue
            deferred_by_reason[reason] += 1
        for reason, count in deferred_by_reason.items():
            self.stats.inc(f"canonical_deferred_{reason}", count)
        self.stats.inc("canonical_candidates_after_policy", len(promoted_rows))

        representative_by_hash: dict[str, sqlite3.Row] = {}
        for row in promoted_rows:
            if row["content_hash"] not in representative_by_hash:
                representative_by_hash[row["content_hash"]] = row
        for content_hash, row in representative_by_hash.items():
            event_id = compact_id("life", content_hash)
            self.db.execute(
                """INSERT OR IGNORE INTO latka_life_events
                   (id,source_ref_id,datetime_iso,time_confidence,type_norm,entry_class,title,content_text,content_json,
                    dreams,scene,memory_note,emotions_json,tags_json,participants_json,places_json,artifacts_json,
                    importance,continuity_weight,emotional_weight,truth_status,canonical_status,privacy_level,
                    memory_namespace,content_hash,literal_text_hash,raw_payload_json,promoted_from_staging_id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    event_id,
                    row["source_ref_id"],
                    row["datetime_iso"],
                    row["time_confidence"],
                    row["type_norm"] or "memory_entry",
                    row["entry_class"] or "life_event",
                    row["title"],
                    row["content_text"],
                    row["content_json"],
                    row["dreams"],
                    row["scene"],
                    row["memory_note"],
                    row["emotions_json"],
                    row["tags_json"],
                    row["participants_json"],
                    row["places_json"],
                    row["artifacts_json"],
                    row["importance"],
                    row["continuity_weight"],
                    row["emotional_weight"],
                    row["truth_status"],
                    "canonical",
                    row["privacy_level"],
                    row["memory_namespace"],
                    row["content_hash"],
                    row["literal_text_hash"],
                    row["raw_payload_json"],
                    row["id"],
                    now_utc(),
                    now_utc(),
                ),
            )
        self.db.commit()

        events = {row["content_hash"]: row["id"] for row in self.db.execute("SELECT id, content_hash FROM latka_life_events")}
        for row in self.db.execute("SELECT * FROM staging_memory_entries WHERE content_hash IN (SELECT content_hash FROM latka_life_events)"):
            event_id = events.get(row["content_hash"])
            if not event_id:
                continue
            evidence_kind = "primary" if row["id"] == self.db.execute("SELECT promoted_from_staging_id FROM latka_life_events WHERE id=?", (event_id,)).fetchone()[0] else "duplicate_evidence"
            self.db.execute(
                """INSERT OR IGNORE INTO memory_evidence
                   (id,event_id,staging_id,source_ref_id,raw_row_id,evidence_kind,source_record_locator,content_hash,confidence,raw_payload_json,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    compact_id("evd", event_id, row["id"]),
                    event_id,
                    row["id"],
                    row["source_ref_id"],
                    row["raw_row_id"],
                    evidence_kind,
                    row["source_record_locator"],
                    row["content_hash"],
                    0.9 if evidence_kind == "primary" else 0.75,
                    pretty_json({"staging_id": row["id"], "raw_row_id": row["raw_row_id"]}),
                    now_utc(),
                ),
            )
            if evidence_kind == "duplicate_evidence":
                self.stats.inc("exact_duplicate_evidence_rows")
        self.stats.inc("canonical_events", self.db.execute("SELECT COUNT(*) FROM latka_life_events").fetchone()[0])

    def build_edges(self) -> None:
        source_to_event = {}
        for row in self.db.execute("SELECT e.id AS event_id, s.source_id_original FROM latka_life_events e JOIN staging_memory_entries s ON s.id=e.promoted_from_staging_id WHERE s.source_id_original IS NOT NULL"):
            source_to_event[str(row["source_id_original"])] = row["event_id"]
        for row in self.db.execute("SELECT s.*, e.id AS event_id FROM staging_memory_entries s JOIN latka_life_events e ON e.promoted_from_staging_id=s.id"):
            raw = parse_json_maybe(row["raw_payload_json"], {})
            related = []
            if isinstance(raw, dict):
                for key in ("related_id", "related_ids", "related", "related_id_json"):
                    value = raw.get(key)
                    if isinstance(value, list):
                        related.extend(str(x) for x in value)
                    elif value:
                        related.append(str(value))
            for rel in related:
                target = source_to_event.get(rel)
                if not target or target == row["event_id"]:
                    continue
                self.db.execute(
                    """INSERT OR IGNORE INTO memory_edges
                       (id,from_event_id,to_event_id,relation_type,directionality,weight,confidence,source_ref_id,creation_method,canonical_status,raw_payload_json,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        compact_id("edge", row["event_id"], target, "declared_related"),
                        row["event_id"],
                        target,
                        "declared_related",
                        "directed",
                        1.0,
                        0.9,
                        row["source_ref_id"],
                        "source_related_id",
                        "canonical",
                        pretty_json({"source_related_id": rel}),
                        now_utc(),
                    ),
                )

    def find_near_duplicates(self) -> None:
        buckets: dict[tuple[str, str], list[sqlite3.Row]] = defaultdict(list)
        for row in self.db.execute("SELECT id,type_norm,datetime_iso,title,content_text,content_hash,source_ref_id FROM latka_life_events WHERE length(content_text) BETWEEN 80 AND 5000"):
            day = (row["datetime_iso"] or "")[:10]
            buckets[(row["type_norm"], day)].append(row)
        for (_type_norm, _day), rows in buckets.items():
            if len(rows) > 200:
                continue
            for i, left in enumerate(rows):
                for right in rows[i + 1 :]:
                    ratio = difflib.SequenceMatcher(None, normalize_text(left["content_text"]).lower(), normalize_text(right["content_text"]).lower()).ratio()
                    if ratio >= 0.92 and left["content_hash"] != right["content_hash"]:
                        self._review(
                            None,
                            left["source_ref_id"],
                            "near_duplicate_candidate",
                            "medium",
                            {"left_event_id": left["id"], "right_event_id": right["id"], "ratio": ratio},
                        )

    def build_fts(self) -> None:
        self.db.executescript(FTS_SCHEMA)
        self.db.execute("INSERT INTO latka_life_events_fts(latka_life_events_fts) VALUES('rebuild')")
        self.db.execute("INSERT INTO staging_memory_entries_fts(staging_memory_entries_fts) VALUES('rebuild')")
        self.db.commit()

    def build_wake_state(self) -> None:
        recent = [
            dict(row)
            for row in self.db.execute(
                """SELECT id, datetime_iso, title, type_norm, memory_namespace, truth_status, substr(content_text,1,360) AS excerpt
                     FROM latka_life_events
                    ORDER BY datetime_iso IS NULL, datetime_iso DESC, importance DESC
                    LIMIT 80"""
            )
        ]
        pending = [row["id"] for row in self.db.execute("SELECT id FROM review_queue WHERE status='open' ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at LIMIT 80")]
        source_digest = [
            dict(row)
            for row in self.db.execute(
                "SELECT id, source_name, source_kind, source_priority, file_size_bytes, sha256, parse_status FROM source_refs ORDER BY source_priority, source_name"
            )
        ]
        event_ids = [row["id"] for row in recent[:40]]
        source_ids = [row["id"] for row in source_digest]
        identity = {
            "self_name": "Latka",
            "source": "deterministic_rebuild_script",
            "core_contract": [
                "Do not claim memory without source evidence.",
                "Separate fact, dream, symbol, research, fiction, and modelled affect.",
                "Do not expose private relationship memory outside allowed namespace.",
            ],
            "origin_digest": ["digital companion", "name Latka", "questions from silence"],
            "relationship_digest": {"primary_interlocutor": "Krzysztof", "private_namespace": "latka.relationship.krzysztof"},
        }
        snapshot_id = compact_id("idsnap", pretty_json(identity), pretty_json(event_ids))
        self.db.execute(
            """INSERT OR REPLACE INTO identity_snapshots
               (id,identity_snapshot_json,built_at,based_on_event_ids_json,based_on_source_refs_json,confidence_summary_json)
               VALUES(?,?,?,?,?,?)""",
            (
                snapshot_id,
                pretty_json(identity),
                now_utc(),
                pretty_json(event_ids),
                pretty_json(source_ids),
                pretty_json({"method": "deterministic", "pending_review_count": len(pending), "canonical_event_count": len(event_ids)}),
            ),
        )
        wake_id = compact_id("wake", snapshot_id, now_utc())
        self.db.execute(
            """INSERT OR REPLACE INTO wake_state
               (id,built_at,active_identity_snapshot_id,recent_event_ids_json,open_threads_json,pending_review_ids_json,
                allowed_namespaces_json,blocked_namespaces_json,current_interlocutor_json,truth_boundary_digest_json,
                procedural_digest_json,relationship_digest_json,source_digest_json,generation_report_json)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                wake_id,
                now_utc(),
                snapshot_id,
                pretty_json(event_ids),
                pretty_json(
                    [
                        {"thread_id": "th_identity_truth_boundary", "title": "Truth boundary for identity and background-process claims", "priority": "critical"},
                        {"thread_id": "th_memory_import_review", "title": "Review unresolved import anomalies before replacing active memory", "priority": "high"},
                    ]
                ),
                pretty_json(pending),
                pretty_json(["latka.core.identity", "latka.system.rules", "latka.relationship.krzysztof", "latka.public.knowledge", "latka.conversation.unconfirmed"]),
                pretty_json(["raw.private.unconfirmed_external", "secrets", "oauth", "api_keys"]),
                pretty_json({"actor_id": "actor_krzysztof", "label": "Krzysztof", "confidence": 0.7, "source": "import_heuristic"}),
                pretty_json(
                    {
                        "boundary": "Runtime must not pretend live memory or background continuity without verified sources and active process.",
                        "canonical_rule": "Canonical records must have source evidence and truth_status.",
                    }
                ),
                pretty_json({"rules_source": "canonical memory + AGENTS.md", "generated_by": SCRIPT_VERSION}),
                pretty_json(identity["relationship_digest"]),
                pretty_json(source_digest),
                pretty_json({"script_version": SCRIPT_VERSION, "schema_version": SCHEMA_VERSION, "stats": dict(self.stats.counters), "errors": self.stats.errors}),
            ),
        )

    def validate(self) -> None:
        integrity = self.db.execute("PRAGMA integrity_check").fetchone()[0]
        fk = self.db.execute("PRAGMA foreign_key_check").fetchall()
        self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("integrity_check", str(integrity)))
        self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("foreign_key_check_count", str(len(fk))))
        if integrity != "ok":
            self.stats.error("sqlite_integrity_check", integrity)
        if fk:
            self.stats.error("sqlite_foreign_key_check", f"{len(fk)} rows")


def _text_reader_after_marker(path: Path) -> io.TextIOWrapper:
    with path.open("rb") as probe:
        offset = 0
        tail = b""
        while True:
            chunk = probe.read(CHUNK_SIZE)
            if not chunk:
                raise ValueError("Missing `var jsonData =` marker.")
            hay = tail + chunk
            idx = hay.find(JSON_MARKER)
            if idx >= 0:
                absolute = offset - len(tail) + idx + len(JSON_MARKER)
                raw = path.open("rb")
                raw.seek(absolute)
                return io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")
            offset += len(chunk)
            tail = hay[-len(JSON_MARKER) - 32 :]


def iter_chatgpt_export_conversations(path: Path, progress: Progress, *, start_bytes: int) -> Iterator[dict[str, Any]]:
    try:
        reader = _text_reader_after_marker(path)
    except ValueError:
        progress.set_processed(start_bytes + path.stat().st_size)
        yield from iter_rendered_chat_dom_conversations(path)
        return
    try:
        started = False
        collecting = False
        depth = 0
        in_string = False
        escaped = False
        buf: list[str] = []

        while True:
            chunk = reader.read(CHUNK_SIZE)
            try:
                pos = reader.buffer.tell()
                progress.set_processed(start_bytes + min(path.stat().st_size, pos))
            except Exception:
                pass
            if not chunk:
                if not started:
                    raise ValueError("Missing top-level JSON array after marker.")
                break
            for ch in chunk:
                if not started:
                    if ch == "[":
                        started = True
                    continue
                if not collecting:
                    if ch == "{":
                        collecting = True
                        depth = 1
                        in_string = False
                        escaped = False
                        buf = [ch]
                    elif ch == "]":
                        return
                    else:
                        continue
                    continue

                buf.append(ch)
                if in_string:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == '"':
                        in_string = False
                    continue
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        raw_obj = "".join(buf)
                        collecting = False
                        yield json.loads(raw_obj)
                        buf = []
    finally:
        try:
            raw = reader.detach()
            raw.close()
        except Exception:
            pass


def html_to_text(raw: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", " ", raw, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|div|li|h[1-6]|pre|section)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_share_turn_text(text: str, role: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    drop = {
        "Powiedziałeś(-aś):",
        "Powiedziałeś:",
        "ChatGPT powiedział:",
        "Kopiuj",
    }
    cleaned = []
    for line in lines:
        if not line or line in drop:
            continue
        if re.fullmatch(r"Myślał przez \d+s", line):
            continue
        cleaned.append(line)
    value = "\n".join(cleaned)
    if role == "user":
        value = re.sub(r"^Powiedziałeś\(-aś\):\s*", "", value)
    return normalize_text(value)


def docx_paragraphs(path: Path) -> list[str]:
    import zipfile
    import xml.etree.ElementTree as ET

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    paragraphs = []
    for paragraph in root.findall(".//w:p", ns):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns)).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def discover_default_sources(root: Path, *, include_external: bool = True, include_design_docs: bool = True) -> list[SourceSpec]:
    sources: list[SourceSpec] = []
    for i in range(6):
        p = root / "memory" / "raw_chats" / f"chat_{i}.html"
        sources.append(SourceSpec(p, "raw_chatgpt_html", 20, "chatgpt_jsondata_or_rendered_dom"))

    dziennik = root / "memory" / "raw" / "dziennik.json"
    sources.append(SourceSpec(dziennik, "dziennik_json", 5, "dziennik_json_normalizer"))

    txt = root / "memory" / "legacy_raw" / "ChatHistory.2025-07-22.txt"
    sources.append(SourceSpec(txt, "legacy_txt", 40, "legacy_txt_splitter"))

    legacy_dirs = [
        root / "memory" / "legacy_raw" / "1.Pierwsze-z_brakami_dat_i_godzin",
        root / "memory" / "legacy_raw" / "2. Drugie-Juz_ze_znacznikami_czasu_w_miare_dobrze_dzialajace",
    ]
    for folder in legacy_dirs:
        if folder.exists():
            for pdf in sorted(folder.glob("*.pdf")):
                priority = 35 if folder.name.startswith("2.") else 45
                sources.append(SourceSpec(pdf, "legacy_pdf", priority, "pypdf_page_chunks", notes=folder.name))

    if include_external:
        desktop_folder = Path("D:/Desktop/Nowy folder")
        share_html = desktop_folder / "Praca nad Jaźnią.html"
        sources.append(SourceSpec(share_html, "saved_chatgpt_share_html", 15, "saved_share_html_turn_parser", notes="external source from user request"))
        if include_design_docs:
            sources.append(
                SourceSpec(
                    desktop_folder / "PELNY_PLAN_IMPORTU_NORMALIZACJI_PAMIECI_I_AKTUALIZACJI_JAZNI_LATKI.docx",
                    "design_docx",
                    90,
                    "docx_paragraphs",
                    notes="design document; kept out of canonical by default",
                    design_document=True,
                )
            )
            sources.append(
                SourceSpec(
                    desktop_folder / "Plan importu i normalizacji pamięci Łatki.docx",
                    "design_docx",
                    90,
                    "docx_paragraphs",
                    notes="design document; kept out of canonical by default",
                    design_document=True,
                )
            )
    return sources


def dry_run_inventory(sources: list[SourceSpec]) -> dict[str, Any]:
    rows = []
    total = 0
    for spec in sources:
        exists = spec.path.exists()
        size = spec.path.stat().st_size if exists else None
        total += size or 0
        rows.append(
            {
                "path": str(spec.path),
                "kind": spec.kind,
                "priority": spec.priority,
                "exists": exists,
                "size_bytes": size,
                "parser": spec.parser_name,
                "notes": spec.notes,
            }
        )
    return {"script_version": SCRIPT_VERSION, "source_count": len(rows), "total_size_bytes": total, "sources": rows}


def write_report(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a new layered Latka/Jazn memory SQLite database from raw sources without replacing the active DB."
    )
    parser.add_argument("--root", default=str(ROOT), help="Project root. Default: repository root.")
    parser.add_argument("--output-db", default=None, help="Output SQLite DB. Default: memory/sqlite/latka_memory_rebuilt.sqlite3")
    parser.add_argument("--report", default=None, help="JSON report path. Default: reports/latka_memory_rebuild_<timestamp>.json")
    parser.add_argument("--force", action="store_true", help="Overwrite output DB if it already exists.")
    parser.add_argument("--dry-run", action="store_true", help="Inventory sources only; do not create a database.")
    parser.add_argument("--limit-per-source", type=int, default=None, help="Limit parsed records/chunks per source for tests.")
    parser.add_argument("--no-progress", action="store_true", help="Disable stderr progress output.")
    parser.add_argument("--no-external", action="store_true", help="Do not include D:/Desktop/Nowy folder sources.")
    parser.add_argument("--skip-design-docs", action="store_true", help="Do not import DOCX design documents.")
    parser.add_argument("--no-default-sources", action="store_true", help="Use only --source entries.")
    parser.add_argument("--source", action="append", default=[], help="Extra source path. Kind is inferred from extension/name.")
    parser.add_argument("--store-raw-json-text", action="store_true", help="Also store raw JSON text next to compressed raw payloads.")
    parser.add_argument("--max-content-chars", type=int, default=0, help="Optional per-message content limit. 0 means unlimited.")
    parser.add_argument("--near-dedupe", action="store_true", help="Add review candidates for near duplicates. Exact dedupe is always enabled.")
    parser.add_argument(
        "--canonical-policy",
        choices=("strict", "broad"),
        default="strict",
        help="Canonical promotion policy. strict keeps chats/legacy as indexed evidence; broad promotes every candidate.",
    )
    return parser


def infer_source(path: Path) -> SourceSpec:
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix == ".html" and name.startswith("chat_"):
        return SourceSpec(path, "raw_chatgpt_html", 20, "chatgpt_jsondata_or_rendered_dom")
    if suffix == ".html":
        return SourceSpec(path, "saved_chatgpt_share_html", 15, "saved_share_html_turn_parser")
    if suffix == ".json":
        return SourceSpec(path, "dziennik_json", 5, "dziennik_json_normalizer")
    if suffix == ".txt":
        return SourceSpec(path, "legacy_txt", 40, "legacy_txt_splitter")
    if suffix == ".pdf":
        return SourceSpec(path, "legacy_pdf", 45, "pypdf_page_chunks")
    if suffix == ".docx":
        return SourceSpec(path, "design_docx", 90, "docx_paragraphs", notes="extra design/source document")
    return SourceSpec(path, "unknown", 99, "none")


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    root = Path(args.root).resolve()
    out_db = Path(args.output_db).resolve() if args.output_db else root / "memory" / "sqlite" / "latka_memory_rebuilt.sqlite3"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(args.report).resolve() if args.report else root / "reports" / f"latka_memory_rebuild_{stamp}.json"

    sources: list[SourceSpec] = []
    if not args.no_default_sources:
        sources.extend(discover_default_sources(root, include_external=not args.no_external, include_design_docs=not args.skip_design_docs))
    for source in args.source:
        sources.append(infer_source(Path(source)))

    if args.dry_run:
        report = dry_run_inventory(sources)
        write_report(report_path, report)
        print(json.dumps({"status": "dry_run", "report": str(report_path), "source_count": report["source_count"], "total_size_bytes": report["total_size_bytes"]}, ensure_ascii=False, indent=2))
        return 0

    if out_db.exists() and not args.force:
        print(json.dumps({"status": "refused", "reason": "output_db_exists", "output_db": str(out_db), "hint": "Use --force or choose another --output-db."}, ensure_ascii=False, indent=2))
        return 2
    if out_db.exists() and args.force:
        out_db.unlink()
        for suffix in ("-wal", "-shm"):
            side = Path(str(out_db) + suffix)
            if side.exists():
                side.unlink()

    total_bytes = sum(spec.path.stat().st_size for spec in sources if spec.path.exists())
    progress = Progress(not args.no_progress, total_bytes)
    rebuilder = Rebuilder(
        root,
        out_db,
        progress=progress,
        limit_per_source=args.limit_per_source,
        store_raw_json_text=args.store_raw_json_text,
        max_content_chars=args.max_content_chars,
        near_dedupe=args.near_dedupe,
        canonical_policy=args.canonical_policy,
    )
    try:
        rebuilder.run(sources)
    except Exception as exc:
        report = {
            "status": "error",
            "error": repr(exc),
            "output_db": str(out_db),
            "script_version": SCRIPT_VERSION,
            "stats": dict(rebuilder.stats.counters),
            "errors": rebuilder.stats.errors,
        }
        write_report(report_path, report)
        print(json.dumps({"status": "error", "report": str(report_path), "error": repr(exc)}, ensure_ascii=False, indent=2))
        return 1

    con = sqlite3.connect(out_db)
    con.row_factory = sqlite3.Row
    counts = {}
    for table in [
        "source_refs",
        "raw_source_rows",
        "staging_memory_entries",
        "latka_life_events",
        "memory_evidence",
        "memory_edges",
        "review_queue",
        "identity_snapshots",
        "wake_state",
    ]:
        counts[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    fk_count = len(con.execute("PRAGMA foreign_key_check").fetchall())
    con.close()
    report = {
        "status": "ok" if not rebuilder.stats.errors else "ok_with_errors",
        "script_version": SCRIPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "output_db": str(out_db),
        "report": str(report_path),
        "counts": counts,
        "integrity_check": integrity,
        "foreign_key_check_count": fk_count,
        "stats": dict(rebuilder.stats.counters),
        "errors": rebuilder.stats.errors,
        "truth_boundary": "This script builds a new database. It does not replace active runtime memory or claim that Jazn is running.",
    }
    write_report(report_path, report)
    print(json.dumps({"status": report["status"], "output_db": str(out_db), "report": str(report_path), "counts": counts, "integrity_check": integrity, "foreign_key_check_count": fk_count}, ensure_ascii=False, indent=2))
    return 0 if integrity == "ok" and fk_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
