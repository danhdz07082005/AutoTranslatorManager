"""CLI helper for migrating legacy text-only translation cache keys.

Usage:
    python -m atm.core.translation.migrate_cache [optional-cache-file]
"""

from __future__ import annotations

import sys

from atm.core.translation.cache_manager import TranslationCache
from atm.storage.repositories.translation_cache_repository import TranslationCacheRepository


def migrate_cache(cache_file: str | None = None) -> bool:
    """Persist the v2 context-aware representation and return whether it changed."""
    repository = TranslationCacheRepository(cache_file)
    raw_cache = repository.load()
    entries, migrated = TranslationCache.migrate_payload(raw_cache)
    if migrated:
        repository.save(
            {
                "schema_version": TranslationCache.SCHEMA_VERSION,
                "entries": entries,
            }
        )
    return migrated


if __name__ == "__main__":
    changed = migrate_cache(sys.argv[1] if len(sys.argv) > 1 else None)
    print("Translation cache migrated." if changed else "Translation cache is current.")
