from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
SCHEMA_VERSION="creative_material_detector/v14.6.10"
@dataclass(slots=True)
class CreativeMaterialReport:
    creative_material_present: bool; material_kind: str; preserve_default: bool; evidence: list[str]; schema_version: str=SCHEMA_VERSION
    def to_dict(self)->dict[str,Any]: return asdict(self)
class CreativeMaterialDetector:
    def detect(self,text:str)->CreativeMaterialReport:
        low=(text or '').lower(); lines=[l for l in text.splitlines() if l.strip()]
        if 'lyrics' in low or '[chorus' in low or '[verse' in low or len(lines)>10:
            return CreativeMaterialReport(True,'lyrics_or_structured_text',True,['lyrics_tags_or_multiline'])
        if 'prompt' in low or 'generator' in low:
            return CreativeMaterialReport(True,'prompt_or_generator_instruction',True,['prompt_generator_marker'])
        return CreativeMaterialReport(False,'none',False,[])
