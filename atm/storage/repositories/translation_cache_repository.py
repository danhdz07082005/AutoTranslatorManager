"""Persistence boundary for the translation cache.

Keeping JSON I/O here prevents translation services from depending on a file
format.  It also gives us one place to make cache writes atomic.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from atm.utils.logger import get_logger


logger = get_logger(__name__, "launcher.log")


class TranslationCacheRepository:
    """Load and save the on-disk translation cache with in-memory snapshot and invalidation."""

    def __init__(self, cache_file: str | os.PathLike[str] | None = None) -> None:
        if cache_file is None:
            from atm.utils.paths import get_cache_dir
            cache_file = Path(get_cache_dir()) / "translation_cache.json"
        self.cache_file = Path(cache_file)
        self._lock = threading.RLock()
        
        # In-memory snapshot state
        self._snapshot: dict[str, Any] = {}
        self._mtime_ns: int = 0
        self._size: int = 0
        
        self._load_unlocked()

    def _get_file_signature(self) -> tuple[int, int]:
        """Return the (mtime_ns, size) signature of the cache file."""
        try:
            stat = self.cache_file.stat()
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return 0, 0

    def _load_unlocked(self) -> None:
        """Internal load without lock. Caller must hold self._lock."""
        if not self.cache_file.exists():
            self._snapshot = {}
            self._mtime_ns, self._size = self._get_file_signature()
            return

        try:
            with self.cache_file.open("r", encoding="utf-8") as cache_stream:
                payload = json.load(cache_stream)
                
            if not isinstance(payload, dict):
                logger.warning("Ignoring translation cache with an invalid root value.")
                self._snapshot = {}
            else:
                self._snapshot = payload
                
            self._mtime_ns, self._size = self._get_file_signature()
        except (OSError, json.JSONDecodeError) as error:
            logger.error("Failed to load translation cache: %s", error)
            self._snapshot = {}
            self._mtime_ns = 0
            self._size = 0

    def load(self) -> dict[str, Any]:
        """Return the current stable cache snapshot, reloading if modified externally."""
        with self._lock:
            current_mtime, current_size = self._get_file_signature()
            if current_mtime != self._mtime_ns or current_size != self._size:
                logger.debug("Cache file signature changed. Reloading snapshot.")
                self._load_unlocked()
            
            return self._snapshot

    def save(self, payload: dict[str, Any]) -> None:
        """Atomically replace the cache file and update the in-memory snapshot."""
        with self._lock:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                temporary_file = self.cache_file.with_suffix(
                    f"{self.cache_file.suffix}.tmp"
                )
                with temporary_file.open("w", encoding="utf-8") as cache_stream:
                    json.dump(payload, cache_stream, ensure_ascii=False, indent=2)
                    cache_stream.flush()
                    os.fsync(cache_stream.fileno())
                    
                os.replace(temporary_file, self.cache_file)
                
                # Update RAM snapshot
                self._snapshot = payload
                self._mtime_ns, self._size = self._get_file_signature()
            except OSError as error:
                logger.error("Failed to save translation cache: %s", error)
