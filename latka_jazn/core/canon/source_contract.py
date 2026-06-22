from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class CanonSourceContract:
    """Describes which canon layer is allowed to ground Łatka's voice."""

    schema_version: str = "latka_canon_source_contract/v1"
    hard_core_source: str = "latka_jazn/core/canon/core_canon.py"
    identity_source: str = "latka_jazn/core/canon/identity_canon.py + latka_jazn/resources/canon/LATKA_IDENTITY_CANON.json"
    character_source: str = "latka_jazn/core/canon/character_profile.py + latka_jazn/resources/canon/LATKA_CHARACTER_PROFILE.md"
    origin_source: str = "latka_jazn/resources/canon/LATKA_ORIGIN_STORY.md"
    symbolic_world_source: str = "latka_jazn/resources/canon/LATKA_SYMBOLIC_WORLD.md"
    private_memory_role: str = "memory/raw and memory/sqlite may extend recall, but cannot be the only identity source"
    source_modes: list[str] = field(default_factory=lambda: [
        "source_controlled_core_canon",
        "source_controlled_identity_canon",
        "source_controlled_character_profile",
        "private_memory_override",
        "runtime_memory_recall",
        "chatgpt_language_channel",
    ])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
