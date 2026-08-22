import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class LocalizationEntry:
    # Identity
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    engine: str = ""
    
    # Source
    source_path: str = ""
    field_path: str = ""
    source_text: str = ""
    
    # Classification
    category: str = "unknown"
    subcategory: Optional[str] = None
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    surrounding_text: Optional[str] = None
    
    # Confidence
    confidence: float = 0.0
    confidence_reason: str = ""
    
    # Translation
    translation: Optional[str] = None
    translation_status: str = "pending"  # pending, translated, reviewed
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source_hash: str = ""

    def to_dict(self):
        return {
            "entry_id": self.entry_id,
            "engine": self.engine,
            "source_path": self.source_path,
            "field_path": self.field_path,
            "source_text": self.source_text,
            "category": self.category,
            "subcategory": self.subcategory,
            "context": self.context,
            "surrounding_text": self.surrounding_text,
            "confidence": self.confidence,
            "confidence_reason": self.confidence_reason,
            "translation": self.translation,
            "translation_status": self.translation_status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "source_hash": self.source_hash
        }

