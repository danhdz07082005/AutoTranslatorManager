# -*- coding: utf-8 -*-
import os
from typing import List
from atm.core.engines.base import BaseExtractor
from atm.core.engines.ir import LocalizationEntry

class BakinExtractor(BaseExtractor):
    def extract(self) -> List[LocalizationEntry]:
        # Mock extraction
        entries = []
        entries.append(LocalizationEntry(
            engine="Bakin",
            source_path="data/ItemDatabase",
            field_path="name",
            source_text="Potion",
            category="item_name",
            confidence=1.00,
            confidence_reason="Known schema field"
        ))
        entries.append(LocalizationEntry(
            engine="Bakin",
            source_path="data/Map001",
            field_path="events/1/message",
            source_text="Hello traveler!",
            category="dialogue",
            confidence=0.85,
            confidence_reason="Standard event structure"
        ))
        entries.append(LocalizationEntry(
            engine="Bakin",
            source_path="data/bakinengine.dll",
            field_path="unknown_offset",
            source_text="Player",
            category="unknown",
            confidence=0.30,
            confidence_reason="Binary blob string"
        ))
        return entries

