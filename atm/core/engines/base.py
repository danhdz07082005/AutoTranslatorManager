from typing import List
from atm.core.engines.ir import LocalizationEntry

class BaseExtractor:
    def __init__(self, game_dir: str):
        self.game_dir = game_dir
        
    def extract(self) -> List[LocalizationEntry]:
        raise NotImplementedError("Subclasses must implement extract()")

class BaseInjector:
    def __init__(self, game_dir: str):
        self.game_dir = game_dir
        
    def inject(self, entries: List[LocalizationEntry]) -> bool:
        raise NotImplementedError("Subclasses must implement inject()")

class BaseAuditor:
    def audit(self, entries: List[LocalizationEntry]) -> dict:
        total = len(entries)
        if total == 0:
            return {"total": 0, "translated": 0, "coverage_percent": 0.0, "confidence_breakdown": {}}
            
        translated = sum(1 for e in entries if e.translation_status in ["translated", "reviewed"])
        coverage = (translated / total) * 100
        
        high = sum(1 for e in entries if e.confidence >= 0.8)
        medium = sum(1 for e in entries if 0.4 <= e.confidence < 0.8)
        low = sum(1 for e in entries if e.confidence < 0.4)
        
        return {
            "total": total,
            "translated": translated,
            "untranslated": total - translated,
            "coverage_percent": round(coverage, 2),
            "confidence_breakdown": {
                "high": high,
                "medium": medium,
                "low": low
            }
        }

