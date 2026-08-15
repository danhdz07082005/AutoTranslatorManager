"""Fuzzy translation-memory suggestions that always require user approval."""

from __future__ import annotations

import threading
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Iterable

from atm.storage.repositories.translation_memory_repository import (
    TranslationMemoryRepository,
)
from atm.utils.logger import get_logger


logger = get_logger(__name__, "launcher.log")


@dataclass(frozen=True, slots=True)
class TranslationMemoryEntry:
    source_lang: str
    target_lang: str
    category: str
    source_text: str
    translated_text: str
    source: str = "user"
    confidence: str = "confirmed"
    last_used: str = ""


@dataclass(frozen=True, slots=True)
class TranslationMemorySuggestion:
    source_text: str
    translated_text: str
    category: str
    similarity: float


class TranslationMemory:
    """A small, persistent fuzzy index kept separate from exact cache hits.

    ``suggest`` is read-only.  Consumers must explicitly call ``remember``
    after a user accepts a suggestion, which makes fuzzy matches safe by
    default.
    """

    SCHEMA_VERSION = 1
    DEFAULT_THRESHOLD = 0.85
    _instance: "TranslationMemory | None" = None
    _instance_lock = threading.Lock()

    def __new__(
        cls, repository: TranslationMemoryRepository | None = None
    ) -> "TranslationMemory":
        if repository is not None:
            instance = super().__new__(cls)
            instance._initialize(repository)
            return instance
        with cls._instance_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialize(TranslationMemoryRepository())
                cls._instance = instance
            return cls._instance

    @classmethod
    def reset_singleton_for_tests(cls) -> None:
        with cls._instance_lock:
            cls._instance = None

    def _initialize(self, repository: TranslationMemoryRepository) -> None:
        self.repository = repository
        self._lock = threading.RLock()
        raw_entries = repository.load().get("entries", [])
        self._entries: list[TranslationMemoryEntry] = []
        for raw_entry in raw_entries:
            entry = self._from_mapping(raw_entry)
            if entry is not None:
                self._entries.append(entry)

    def remember(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        category: str = "unknown",
        *,
        source: str = "user",
        confidence: str = "confirmed",
        save: bool = True,
    ) -> None:
        """Record a translation only after explicit confirmation by a caller."""
        entry = TranslationMemoryEntry(
            source_lang=source_lang,
            target_lang=target_lang,
            category=category or "unknown",
            source_text=source_text,
            translated_text=translated_text,
            source=source if source in {"user", "api"} else "user",
            confidence=confidence if confidence in {"confirmed", "auto"} else "confirmed",
            last_used=datetime.now(timezone.utc).isoformat(),
        )
        if not self._is_valid(entry):
            raise ValueError("Translation-memory source and translation must be non-empty strings.")

        with self._lock:
            self._entries = [
                current
                for current in self._entries
                if not (
                    current.source_lang == entry.source_lang
                    and current.target_lang == entry.target_lang
                    and current.category == entry.category
                    and current.source_text == entry.source_text
                )
            ]
            self._entries.append(entry)
            if save:
                self._save_unlocked()

    def get_exact(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        category: str = "unknown",
    ) -> str | None:
        """Return an exact TM hit, preferring user-confirmed entries."""

        with self._lock:
            matches = [
                entry
                for entry in self._entries
                if entry.source_lang == source_lang
                and entry.target_lang == target_lang
                and entry.category == (category or "unknown")
                and entry.source_text == source_text
            ]
        matches.sort(
            key=lambda entry: (
                entry.source != "user",
                entry.confidence != "confirmed",
                entry.last_used,
            )
        )
        return matches[0].translated_text if matches else None

    def suggest(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        category: str = "unknown",
        threshold: float = DEFAULT_THRESHOLD,
        limit: int = 5,
    ) -> list[TranslationMemorySuggestion]:
        """Find similar entries without changing any translation result."""
        threshold = max(0.0, min(1.0, threshold))
        normalized_source = self._normalize(source_text)
        if not normalized_source:
            return []

        with self._lock:
            candidates = list(self._entries)

        suggestions = []
        for entry in candidates:
            if entry.source_lang != source_lang or entry.target_lang != target_lang:
                continue
            # Context is significant. Unknown historical entries may be shown
            # only to an unknown request and never bleed into a typed category.
            if entry.category != (category or "unknown"):
                continue
            similarity = SequenceMatcher(
                None, normalized_source, self._normalize(entry.source_text)
            ).ratio()
            if similarity >= threshold:
                suggestions.append(
                    TranslationMemorySuggestion(
                        source_text=entry.source_text,
                        translated_text=entry.translated_text,
                        category=entry.category,
                        similarity=round(similarity, 4),
                    )
                )
        suggestions.sort(key=lambda candidate: candidate.similarity, reverse=True)
        return suggestions[: max(1, limit)]

    def entries(self) -> Iterable[TranslationMemoryEntry]:
        with self._lock:
            return tuple(self._entries)

    def _save_unlocked(self) -> None:
        self.repository.save(
            {
                "schema_version": self.SCHEMA_VERSION,
                "entries": [asdict(entry) for entry in self._entries],
            }
        )

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(unicodedata.normalize("NFC", text).casefold().split())

    @classmethod
    def _from_mapping(cls, raw_entry: object) -> TranslationMemoryEntry | None:
        if not isinstance(raw_entry, dict):
            return None
        try:
            entry = TranslationMemoryEntry(
                source_lang=str(raw_entry["source_lang"]),
                target_lang=str(raw_entry["target_lang"]),
                category=str(raw_entry.get("category", "unknown")),
                source_text=str(raw_entry["source_text"]),
                translated_text=str(raw_entry["translated_text"]),
                source=str(raw_entry.get("source", "user")),
                confidence=str(raw_entry.get("confidence", "confirmed")),
                last_used=str(raw_entry.get("last_used", "")),
            )
        except KeyError:
            return None
        return entry if cls._is_valid(entry) else None

    @staticmethod
    def _is_valid(entry: TranslationMemoryEntry) -> bool:
        return bool(entry.source_text.strip() and entry.translated_text.strip())
