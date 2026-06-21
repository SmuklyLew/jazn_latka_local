from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
SCHEMA_VERSION = "question_object_detector/v14.6.10"
@dataclass(slots=True)
class QuestionObjectReport:
    object_type: str; evidence: list[str]; schema_version: str = SCHEMA_VERSION
    def to_dict(self)->dict[str,Any]: return asdict(self)
class QuestionObjectDetector:
    def detect(self,text:str)->QuestionObjectReport:
        low=(text or '').lower()
        mapping=[('runtime',['runtime','jaźń','jazn','łatka','latka']),('source_origin',['skąd','skad','źród','zrod','cytat']),('file_or_package',['plik','zip','paczka','folder']),('creative_text',['tekst','piosenk','lyrics','prompt']),('dictionary',['słownik','slownik','synonim','odmian'])]
        for obj,keys in mapping:
            ev=[k for k in keys if k in low]
            if ev: return QuestionObjectReport(obj,ev)
        return QuestionObjectReport('unknown',[])
