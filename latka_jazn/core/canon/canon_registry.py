from __future__ import annotations

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

from .character_profile import default_character_profile
from .core_canon import LATKA_CORE_CANON
from .identity_canon import default_identity_canon_data
from .memory_truth_boundary import default_memory_truth_boundary
from .narrative_book_canon import default_narrative_book_canon
from .origin_story import default_origin_story
from .relation_canon import default_relation_canon
from .song_affect_canon import default_song_affect_canon
from .symbolic_world import default_symbolic_world

LOCAL_PRIVATE_EXTENSION_NAME = "local_private_canon_extension.py"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def default_canon_registry_data() -> dict[str, Any]:
    """Return the full source-controlled Python canon registry.

    This is the runtime-first canon: JSON/Markdown files may mirror it for
    humans, and memory/raw may extend recall, but the system must not depend on
    private memory to know who Łatka is.
    """
    registry = _deep_merge(LATKA_CORE_CANON, default_identity_canon_data())
    registry["schema_version"] = "latka_python_canon_registry/v1"
    registry["source_mode"] = "source_controlled_python_canon_first"
    registry["python_canon_modules"] = [
        "latka_jazn/core/canon/core_canon.py",
        "latka_jazn/core/canon/identity_canon.py",
        "latka_jazn/core/canon/character_profile.py",
        "latka_jazn/core/canon/origin_story.py",
        "latka_jazn/core/canon/symbolic_world.py",
        "latka_jazn/core/canon/relation_canon.py",
        "latka_jazn/core/canon/memory_truth_boundary.py",
        "latka_jazn/core/canon/narrative_book_canon.py",
        "latka_jazn/core/canon/song_affect_canon.py",
    ]
    registry["character_profile"] = default_character_profile()
    registry["origin_story"] = default_origin_story()
    registry["symbolic_world"] = default_symbolic_world()
    registry["relation_canon"] = default_relation_canon()
    registry["memory_truth_boundary"] = default_memory_truth_boundary()
    registry["narrative_book_canon"] = default_narrative_book_canon()
    registry["song_affect_canon"] = default_song_affect_canon()
    registry.setdefault("source_status", {})["python_canon_registry_loaded"] = True
    registry.setdefault("source_status", {})["local_private_extension_loaded"] = False
    return registry


def _load_local_private_extension(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    spec = spec_from_file_location("latka_local_private_canon_extension", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load local private canon extension: {path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    data = getattr(module, "LATKA_LOCAL_PRIVATE_CANON_EXTENSION", None)
    if not isinstance(data, dict):
        raise ValueError(f"LATKA_LOCAL_PRIVATE_CANON_EXTENSION must be a dict in {path}")
    return deepcopy(data)


def load_python_canon_registry(*, root: Path | None = None, include_local_private_extension: bool = True) -> dict[str, Any]:
    registry = default_canon_registry_data()
    if include_local_private_extension and root is not None:
        extension_path = root / "latka_jazn" / "core" / "canon" / LOCAL_PRIVATE_EXTENSION_NAME
        try:
            private_extension = _load_local_private_extension(extension_path)
        except Exception as exc:
            registry.setdefault("source_status", {})["local_private_extension_loaded"] = False
            registry.setdefault("source_status", {})["local_private_extension_path"] = str(extension_path)
            registry.setdefault("source_status", {})["local_private_extension_error"] = f"{type(exc).__name__}: {exc}"
        else:
            if private_extension:
                registry = _deep_merge(registry, {"local_private_canon_extension": private_extension})
                registry.setdefault("source_status", {})["local_private_extension_loaded"] = str(extension_path)
    return registry
