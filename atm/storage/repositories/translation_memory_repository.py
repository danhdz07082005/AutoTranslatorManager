"""Persistence boundary for user-confirmed translation-memory entries."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from atm.utils.logger import get_logger


logger = get_logger(__name__, "launcher.log")


class TranslationMemoryRepository:
    """Store translation memory independently from the exact-match cache."""

    def __init__(self, memory_file: str | os.PathLike[str] | None = None) -> None:
        if memory_file is None:
            project_root = Path(__file__).resolve().parents[3]
            memory_file = project_root / "data" / "translation_memory.json"
        self.memory_file = Path(memory_file)

    def load(self) -> dict[str, Any]:
        if not self.memory_file.exists():
            return {"schema_version": 1, "entries": []}
        try:
            with self.memory_file.open("r", encoding="utf-8") as memory_stream:
                payload = json.load(memory_stream)
        except (OSError, json.JSONDecodeError) as error:
            logger.error("Failed to load translation memory: %s", error)
            return {"schema_version": 1, "entries": []}
        if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
            logger.warning("Ignoring translation memory with an invalid format.")
            return {"schema_version": 1, "entries": []}
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        temporary_file: Path | None = None
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            temporary_file = self.memory_file.with_name(
                f"{self.memory_file.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
            )
            with temporary_file.open("w", encoding="utf-8") as memory_stream:
                json.dump(payload, memory_stream, ensure_ascii=False, indent=2)

            last_error: OSError | None = None
            for attempt in range(5):
                try:
                    os.replace(temporary_file, self.memory_file)
                    return
                except OSError as error:
                    last_error = error
                    time.sleep(0.15 * (attempt + 1))
            if last_error is not None:
                raise last_error
        except OSError as error:
            logger.error("Failed to save translation memory: %s", error)
            if temporary_file is not None:
                try:
                    temporary_file.unlink(missing_ok=True)
                except OSError:
                    pass
