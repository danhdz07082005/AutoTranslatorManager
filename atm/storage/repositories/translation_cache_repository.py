"""Persistence boundary for the translation cache.

Keeping JSON I/O here prevents translation services from depending on a file
format.  It also gives us one place to make cache writes atomic.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from atm.utils.logger import get_logger


logger = get_logger(__name__, "launcher.log")


class TranslationCacheRepository:
    """Load and save the on-disk translation cache."""

    def __init__(self, cache_file: str | os.PathLike[str] | None = None) -> None:
        if cache_file is None:
            project_root = Path(__file__).resolve().parents[3]
            cache_file = project_root / "data" / "translation_cache.json"
        self.cache_file = Path(cache_file)

    def load(self) -> dict[str, Any]:
        """Return raw cache data, treating a missing/corrupt file as empty."""
        if not self.cache_file.exists():
            return {}

        try:
            with self.cache_file.open("r", encoding="utf-8") as cache_stream:
                payload = json.load(cache_stream)
        except (OSError, json.JSONDecodeError) as error:
            logger.error("Failed to load translation cache: %s", error)
            return {}

        if not isinstance(payload, dict):
            logger.warning("Ignoring translation cache with an invalid root value.")
            return {}
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        """Atomically replace the cache file after writing valid JSON."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            temporary_file = self.cache_file.with_suffix(
                f"{self.cache_file.suffix}.tmp"
            )
            with temporary_file.open("w", encoding="utf-8") as cache_stream:
                json.dump(payload, cache_stream, ensure_ascii=False, indent=2)
            os.replace(temporary_file, self.cache_file)
        except OSError as error:
            logger.error("Failed to save translation cache: %s", error)

