"""Context-aware translation cache facade.

The cache is deliberately kept behind ``TranslationCacheRepository`` so core
translation code does not read or write JSON files directly.  Version 2 keys
entries by ``(source language, target language, category, original text)``.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from typing import Any

from atm.storage.repositories.translation_cache_repository import (
    TranslationCacheRepository,
)
from atm.utils.logger import get_logger


logger = get_logger(__name__, "launcher.log")


class TranslationCache:
    """Thread-safe cache for exact translations, partitioned by context."""

    SCHEMA_VERSION = 2
    LEGACY_CATEGORY = "unknown"
    MANUAL_CATEGORY = "global"
    _instance: "TranslationCache | None" = None
    _instance_lock = threading.Lock()

    def __new__(
        cls, repository: TranslationCacheRepository | None = None
    ) -> "TranslationCache":
        # Production code uses a single in-memory cache.  Passing a repository
        # creates an isolated instance, which is useful for tests and migrations.
        if repository is not None:
            instance = super().__new__(cls)
            instance._initialize(repository)
            return instance

        with cls._instance_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialize(TranslationCacheRepository())
                cls._instance = instance
            return cls._instance

    @classmethod
    def reset_singleton_for_tests(cls) -> None:
        """Reset process state for an isolated test; not used by application code."""
        with cls._instance_lock:
            cls._instance = None

    def _initialize(self, repository: TranslationCacheRepository) -> None:
        self.repository = repository
        # Retained as a compatibility attribute for callers that display the
        # cache file location.  I/O itself stays in the repository.
        self.cache_file = str(repository.cache_file)
        self._cache_lock = threading.RLock()
        raw_payload = repository.load()
        self.cache, migrated = self.migrate_payload(raw_payload)
        if migrated:
            logger.info("Migrated translation cache to context-aware schema v2.")
            self._save_unlocked()

    @classmethod
    def migrate_payload(
        cls, payload: dict[str, Any]
    ) -> tuple[dict[str, dict[str, dict[str, dict[str, str]]]], bool]:
        """Turn legacy ``text -> translation`` cache data into schema v2.

        Legacy entries are preserved under ``unknown`` rather than discarded.
        Known categories intentionally do not read those entries automatically:
        an old context-free translation must not override a context-specific one.
        """
        if (
            payload.get("schema_version") == cls.SCHEMA_VERSION
            and isinstance(payload.get("entries"), dict)
        ):
            return cls._sanitize_entries(payload["entries"]), False

        # Accept a pre-release nested representation as current data as well.
        if payload.get("entries") is not None and isinstance(payload["entries"], dict):
            return cls._sanitize_entries(payload["entries"]), True

        migrated: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
        for source_lang, target_languages in payload.items():
            if not isinstance(source_lang, str) or not isinstance(target_languages, dict):
                continue
            source_entries = migrated.setdefault(source_lang, {})
            for target_lang, values in target_languages.items():
                if not isinstance(target_lang, str) or not isinstance(values, dict):
                    continue
                target_entries = source_entries.setdefault(target_lang, {})
                # If data is already category -> text -> translation, keep it.
                nested_categories = all(
                    isinstance(category_values, dict)
                    for category_values in values.values()
                )
                if nested_categories and values:
                    for category, category_values in values.items():
                        if not isinstance(category, str):
                            continue
                        clean_values = {
                            text: translated
                            for text, translated in category_values.items()
                            if isinstance(text, str) and isinstance(translated, str)
                        }
                        if clean_values:
                            target_entries[category] = clean_values
                    continue

                legacy_entries = {
                    text: translated
                    for text, translated in values.items()
                    if isinstance(text, str) and isinstance(translated, str)
                }
                if legacy_entries:
                    target_entries[cls.LEGACY_CATEGORY] = legacy_entries
        return migrated, bool(payload)

    @staticmethod
    def _sanitize_entries(
        entries: dict[str, Any]
    ) -> dict[str, dict[str, dict[str, dict[str, str]]]]:
        clean_entries: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
        for source_lang, target_languages in entries.items():
            if not isinstance(source_lang, str) or not isinstance(target_languages, dict):
                continue
            for target_lang, categories in target_languages.items():
                if not isinstance(target_lang, str) or not isinstance(categories, dict):
                    continue
                for category, text_values in categories.items():
                    if not isinstance(category, str) or not isinstance(text_values, dict):
                        continue
                    values = {
                        text: translated
                        for text, translated in text_values.items()
                        if isinstance(text, str) and isinstance(translated, str)
                    }
                    if values:
                        clean_entries.setdefault(source_lang, {}).setdefault(
                            target_lang, {}
                        )[category] = values
        return clean_entries

    def get(
        self,
        source_lang: str,
        target_lang: str,
        text: str,
        category: str = LEGACY_CATEGORY,
    ) -> str | None:
        """Return an exact contextual cache hit, if one exists."""
        with self._cache_lock:
            contextual_hit = (
                self.cache.get(source_lang, {})
                .get(target_lang, {})
                .get(category, {})
                .get(text)
            )
            if contextual_hit is not None:
                return contextual_hit
            # Entries made through the user dictionary/editor are deliberately
            # global. Legacy ``unknown`` entries are *not* a fallback because
            # they lack reliable semantic context.
            if category != self.MANUAL_CATEGORY:
                return (
                    self.cache.get(source_lang, {})
                    .get(target_lang, {})
                    .get(self.MANUAL_CATEGORY, {})
                    .get(text)
                )
            return None

    def set(
        self,
        source_lang: str,
        target_lang: str,
        text: str,
        translated: str,
        category: str = LEGACY_CATEGORY,
    ) -> None:
        """Store one contextual exact-match translation."""
        if not isinstance(text, str) or not isinstance(translated, str):
            raise TypeError("Translation cache keys and values must be strings.")
        with self._cache_lock:
            values = self._category_entries(source_lang, target_lang, category)
            values[text] = translated
            self._enforce_limit(source_lang, target_lang)

    def set_batch(
        self,
        source_lang: str,
        target_lang: str,
        texts: list[str],
        translated_texts: list[str],
        category: str = LEGACY_CATEGORY,
    ) -> None:
        """Store aligned translations in one category, ignoring missing results."""
        with self._cache_lock:
            values = self._category_entries(source_lang, target_lang, category)
            for text, translated in zip(texts, translated_texts):
                if isinstance(text, str) and isinstance(translated, str):
                    values[text] = translated
            self._enforce_limit(source_lang, target_lang)

    def iter_entries(self) -> Iterator[tuple[str, str, str, str, str]]:
        """Yield ``source, target, category, original, translated`` entries."""
        with self._cache_lock:
            snapshot = [
                (source, target, category, text, translated)
                for source, target_languages in self.cache.items()
                for target, categories in target_languages.items()
                for category, values in categories.items()
                for text, translated in values.items()
            ]
        yield from snapshot

    def save_to_disk(self) -> None:
        with self._cache_lock:
            self._save_unlocked()

    def _category_entries(
        self, source_lang: str, target_lang: str, category: str
    ) -> dict[str, str]:
        return (
            self.cache.setdefault(source_lang, {})
            .setdefault(target_lang, {})
            .setdefault(category or self.LEGACY_CATEGORY, {})
        )

    def _save_unlocked(self) -> None:
        self.repository.save(
            {
                "schema_version": self.SCHEMA_VERSION,
                "entries": self.cache,
            }
        )

    def _enforce_limit(
        self, source_lang: str, target_lang: str, max_size: int = 50_000
    ) -> None:
        categories = self.cache.get(source_lang, {}).get(target_lang, {})
        current_size = sum(len(values) for values in categories.values())
        if current_size <= max_size:
            return

        overflow = max(5_000, current_size - max_size)
        removed = 0
        for category in list(categories):
            values = categories[category]
            while values and removed < overflow:
                oldest_text = next(iter(values))
                del values[oldest_text]
                removed += 1
            if not values:
                del categories[category]
            if removed >= overflow:
                break
        logger.warning(
            "Trimmed %s translation-cache entries for %s -> %s.",
            removed,
            source_lang,
            target_lang,
        )
