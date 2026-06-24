from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import os

DEFAULT_MAX_SQLITE_FILE_BYTES = 480 * 1024 * 1024


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "tak", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, ""))
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, ""))
    except Exception:
        return default

@dataclass(slots=True)
class JaznConfig:
    version: str = "v14.8.3.4.093"
    root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1])
    timezone: str = "Europe/Warsaw"
    timestamp_format: str = "[🕒 %Y-%m-%d %H:%M:%S GMT%z, %A, Europe/Warsaw]"
    memory_db_name: str = field(default_factory=lambda: os.environ.get("JAZN_RUNTIME_MEMORY_DB", "memory/sqlite/runtime_write_v1/runtime_memory.sqlite3").strip())
    audit_db_name: str = field(default_factory=lambda: os.environ.get("JAZN_AUDIT_DB", "memory/sqlite/runtime_write_v1/runtime_audit.sqlite3").strip())
    conversation_archive_manifest_name: str = field(default_factory=lambda: os.environ.get("JAZN_CONVERSATION_ARCHIVE_MANIFEST", "memory/sqlite/conversation_archive_v1/conversation_archive_manifest.sqlite3").strip())
    conversation_fts_dir_name: str = field(default_factory=lambda: os.environ.get("JAZN_CONVERSATION_FTS_DIR", "memory/sqlite/conversation_fts_v1").strip())
    conversation_staging_dir_name: str = field(default_factory=lambda: os.environ.get("JAZN_CONVERSATION_STAGING_DIR", "memory/sqlite/staging_v1").strip())
    runtime_workspace_dir_name: str = field(default_factory=lambda: os.environ.get("JAZN_RUNTIME_WORKSPACE_DIR", "workspace_runtime").strip())
    conversation_shard_manifest_name: str = field(default_factory=lambda: os.environ.get("JAZN_CONVERSATION_SHARD_MANIFEST", "memory/sqlite/runtime_write_v1/runtime_memory_shards.json").strip())
    audit_shard_manifest_name: str = field(default_factory=lambda: os.environ.get("JAZN_AUDIT_SHARD_MANIFEST", "memory/sqlite/runtime_write_v1/runtime_audit_shards.json").strip())
    max_sqlite_file_bytes: int = field(default_factory=lambda: _env_int("JAZN_MAX_SQLITE_FILE_BYTES", DEFAULT_MAX_SQLITE_FILE_BYTES))
    canon_path: str = "latka_jazn/resources/canon/LATKA_IDENTITY_CANON.json"
    private_canon_override_path: str = "memory/raw/LATKA_IDENTITY_CANON.json"
    bootstrap_path: str = "memory/raw/LATKA_BOOTSTRAP_SYSTEM.txt"
    raw_memory_dir: str = "memory/raw"
    versioned_memory_dir: str = "memory/versioned_sources"
    require_first_person_identity: bool = True
    network_time_first: bool = field(default_factory=lambda: _env_bool("JAZN_NETWORK_TIME_FIRST", False))
    local_time_fallback: bool = True
    startup_status_default_mode: str = field(default_factory=lambda: os.environ.get("JAZN_STARTUP_STATUS_MODE", "fast").strip().lower())
    sqlite_health_default_mode: str = field(default_factory=lambda: os.environ.get("JAZN_SQLITE_HEALTH_MODE", "metadata").strip().lower())
    turn_trace_enabled: bool = field(default_factory=lambda: _env_bool("JAZN_TURN_TRACE", False))
    network_time_allowed_in_normal_turn: bool = field(default_factory=lambda: _env_bool("JAZN_NETWORK_TIME_IN_TURN", False))
    auto_import_raw_chat_html_on_bootstrap: bool = True
    raw_chat_html_auto_import_limit: int | None = None
    idle_reflection_thresholds: tuple[int, ...] = (300, 600, 21600)

    allow_network: bool = field(default_factory=lambda: _env_bool("JAZN_ALLOW_NETWORK", True))
    network_default_timeout_connect_seconds: float = field(default_factory=lambda: _env_float("JAZN_NETWORK_TIMEOUT_CONNECT", 3.0))
    network_default_timeout_read_seconds: float = field(default_factory=lambda: _env_float("JAZN_NETWORK_TIMEOUT_READ", 6.0))
    network_max_retries: int = field(default_factory=lambda: _env_int("JAZN_NETWORK_MAX_RETRIES", 1))
    network_user_agent: str = "LatkaJazn/14.8.3"
    network_cache_required: bool = True
    network_cache_ttl_seconds: int = 604800
    network_respect_robots_and_terms: bool = True

    dictionary_allow_network: bool = field(default_factory=lambda: _env_bool("JAZN_DICTIONARY_ALLOW_NETWORK", True))
    dictionary_network_cache_required: bool = True
    dictionary_online_lookup_timeout_seconds: float = field(default_factory=lambda: _env_float("JAZN_DICTIONARY_TIMEOUT", 4.0))
    dictionary_provider_order: tuple[str, ...] = (
        "local_cache", "local_mini_lexicon", "morfeusz_optional",
        "wiktionary_mediawiki_api", "sjp_reference", "wsjp_reference", "plwordnet_optional", "languagetool_optional",
    )
    lexical_resources_registry_path: str = "latka_jazn/resources/nlp/verified_sources.json"
    latka_project_lexicon_path: str = "latka_jazn/resources/nlp/latka_project_lexicon.json"
    lexical_resource_cache_name: str = field(default_factory=lambda: os.environ.get("JAZN_LEXICAL_RESOURCE_CACHE", "workspace_runtime/dictionary_cache.sqlite3").strip())
    lexical_resource_cache_ttl_seconds: int = field(default_factory=lambda: _env_int("JAZN_LEXICAL_RESOURCE_CACHE_TTL", 604800))
    lexical_resource_status_include_optional: bool = field(default_factory=lambda: _env_bool("JAZN_LEXICAL_STATUS_OPTIONAL", True))


    research_allow_network: bool = field(default_factory=lambda: _env_bool("JAZN_RESEARCH_ALLOW_NETWORK", True))
    research_requires_chatgpt_web_when_local_provider_missing: bool = True
    test_mode: bool = field(default_factory=lambda: _env_bool("JAZN_TEST_MODE", False))

    model_adapter: str = field(default_factory=lambda: os.environ.get("JAZN_MODEL_ADAPTER", "null").strip().lower())
    model_name: str = field(default_factory=lambda: os.environ.get("JAZN_MODEL_NAME", "gpt-5.2").strip())
    model_api_base: str = field(default_factory=lambda: os.environ.get("JAZN_MODEL_API_BASE", "https://api.openai.com/v1").strip().rstrip("/"))
    model_timeout_seconds: float = field(default_factory=lambda: _env_float("JAZN_MODEL_TIMEOUT", 45.0))
    model_max_output_tokens: int = field(default_factory=lambda: _env_int("JAZN_MODEL_MAX_OUTPUT_TOKENS", 800))
    local_model_name: str = field(default_factory=lambda: os.environ.get("JAZN_LOCAL_MODEL_NAME", "").strip())
    local_model_api_base: str = field(default_factory=lambda: os.environ.get("JAZN_LOCAL_MODEL_API_BASE", "http://127.0.0.1:11434").strip().rstrip("/"))

    @property
    def runtime_workspace_dir(self) -> Path:
        return self.root / self.runtime_workspace_dir_name

    @property
    def conversation_archive_manifest_path(self) -> Path:
        return self.root / self.conversation_archive_manifest_name

    @property
    def conversation_fts_dir(self) -> Path:
        return self.root / self.conversation_fts_dir_name

    @property
    def conversation_staging_dir(self) -> Path:
        return self.root / self.conversation_staging_dir_name

    @property
    def lexical_resource_cache_path(self) -> Path:
        return self.root / self.lexical_resource_cache_name

    def _active_shard_path(self, manifest_name: str, logical_database: str, role: str, default_db_name: str) -> Path:
        try:
            from .db.shard_manifest import SQLiteShardManager
            return SQLiteShardManager(
                self.root,
                manifest_name,
                logical_database=logical_database,
                role=role,
                default_db_path=default_db_name,
                max_file_bytes=self.max_sqlite_file_bytes,
            ).rotate_if_needed()
        except Exception:
            return self.root / default_db_name

    @property
    def memory_db_path(self) -> Path:
        return self._active_shard_path(
            self.conversation_shard_manifest_name,
            "chat_context",
            "canonical_runtime_conversation_memory",
            self.memory_db_name,
        )

    @property
    def audit_db_path(self) -> Path:
        return self._active_shard_path(
            self.audit_shard_manifest_name,
            "chat_context_audit",
            "canonical_realtime_audit",
            self.audit_db_name,
        )

    @property
    def network_timeout(self) -> tuple[float, float]:
        return (self.network_default_timeout_connect_seconds, self.network_default_timeout_read_seconds)

    def resolve(self, rel: str) -> Path:
        return self.root / rel
