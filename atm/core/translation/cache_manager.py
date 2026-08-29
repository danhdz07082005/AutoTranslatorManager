import os
import shutil
import threading
from typing import Iterator

from atm.storage.repositories.translation_cache_repository import TranslationCacheRepository
from atm.storage.repositories.sqlite_translation_cache import SQLiteTranslationCache
from atm.utils.logger import get_logger

logger = get_logger(__name__, "translation.log")

class TranslationCache:
    """
    Manages the global translation cache.
    Backed by SQLite Translation Cache for thread safety and high concurrency.
    Supports automatic migration from legacy JSON on first load.
    """
    
    LEGACY_CATEGORY = "default"
    MANUAL_CATEGORY = "manual"
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self.db_path = os.path.join(data_dir, "translation_cache.db")
        self.legacy_json_path = os.path.join(data_dir, "translation_cache.json")
        self.repo = SQLiteTranslationCache(self.db_path)
        self._write_lock = threading.Lock()
        
        self._migrate_if_needed()
        self._start_background_prune()
        
    def _start_background_prune(self):
        """Run pruning in a background thread to avoid blocking startup."""
        def _prune():
            try:
                deleted = self.repo.prune_old_entries(days_old=30)
                if deleted > 0:
                    logger.info(f"Auto-pruned {deleted} old translation cache entries.")
            except Exception as e:
                logger.error(f"Failed to auto-prune cache: {e}")
                
        threading.Thread(target=_prune, daemon=True, name="CachePrunerThread").start()
        
    def _migrate_if_needed(self):
        """Migrate legacy JSON translation cache to SQLite if it exists."""
        if not os.path.exists(self.legacy_json_path):
            return
            
        with self._write_lock:
            if not os.path.exists(self.legacy_json_path):
                return
            
            # If DB is already populated, we just rename the old JSON and skip
            if self.repo.count() > 0:
                logger.info("SQLite cache already populated. Backing up old JSON.")
                shutil.move(self.legacy_json_path, self.legacy_json_path + ".bak")
                return
                
            logger.info("Migrating legacy JSON cache to SQLite...")
            try:
                # Need to use the old TranslationCacheRepository to load the JSON
                old_repo = TranslationCacheRepository(self.legacy_json_path)
                payload = old_repo.load()
                entries = payload.get("entries", {})
                
                batch = []
                for source_lang, target_languages in entries.items():
                    for target_lang, categories in target_languages.items():
                        for category, values in categories.items():
                            for original, translated in values.items():
                                if isinstance(original, str) and isinstance(translated, str):
                                    batch.append((source_lang, target_lang, category, original, translated))
                
                if batch:
                    self.repo.set_batch(batch)
                    logger.info(f"Successfully migrated {len(batch)} entries to SQLite.")
                
                # Backup the old JSON file
                shutil.move(self.legacy_json_path, self.legacy_json_path + ".bak")
            except Exception as e:
                logger.error(f"Failed to migrate legacy JSON cache: {e}")

    def get(self, source_lang: str, target_lang: str, text: str, category: str = LEGACY_CATEGORY) -> str | None:
        """Return an exact contextual cache hit from SQLite."""
        # Try specific category first
        hit = self.repo.get(source_lang, target_lang, category, text)
        if hit is not None:
            return hit
            
        # Fallback to manual category
        if category != self.MANUAL_CATEGORY:
            return self.repo.get(source_lang, target_lang, self.MANUAL_CATEGORY, text)
            
        return None

    def set(self, source_lang: str, target_lang: str, text: str, translated: str, category: str = LEGACY_CATEGORY) -> None:
        """Store one contextual exact-match translation."""
        if not isinstance(text, str) or not isinstance(translated, str):
            raise TypeError("Translation cache keys and values must be strings.")
        self.repo.set(source_lang, target_lang, category, text, translated)

    def set_batch(self, source_lang: str, target_lang: str, texts: list[str], translated_texts: list[str], category: str = LEGACY_CATEGORY) -> None:
        """Store aligned translations in one category."""
        batch = [
            (source_lang, target_lang, category, t, tr)
            for t, tr in zip(texts, translated_texts)
            if isinstance(t, str) and isinstance(tr, str)
        ]
        if batch:
            self.repo.set_batch(batch)

    def iter_entries(self) -> Iterator[tuple[str, str, str, str, str]]:
        """Yield ``source, target, category, original, translated`` entries."""
        with self.repo.transaction() as conn:
            cursor = conn.execute("SELECT source_lang, target_lang, category, original, translated FROM cache")
            while True:
                rows = cursor.fetchmany(1000)
                if not rows:
                    break
                for row in rows:
                    yield row

    def save_to_disk(self) -> None:
        """No-op for SQLite, retained for backward compatibility."""
        pass

    def search(self, q: str, page: int = 1, limit: int = 50) -> dict:
        """Search entries in SQLite with pagination."""
        offset = (page - 1) * limit
        q_like = f"%{q}%" if q else "%"
        
        with self.repo.transaction() as conn:
            if q:
                # Count total matching
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM cache 
                    WHERE original LIKE ? OR translated LIKE ?
                ''', (q_like, q_like))
                total = cursor.fetchone()[0]
                
                # Fetch page
                cursor = conn.execute('''
                    SELECT source_lang, target_lang, category, original, translated 
                    FROM cache 
                    WHERE original LIKE ? OR translated LIKE ?
                    ORDER BY original, category, source_lang, target_lang
                    LIMIT ? OFFSET ?
                ''', (q_like, q_like, limit, offset))
            else:
                # Count total
                cursor = conn.execute("SELECT COUNT(*) FROM cache")
                total = cursor.fetchone()[0]
                
                # Fetch page
                cursor = conn.execute('''
                    SELECT source_lang, target_lang, category, original, translated 
                    FROM cache 
                    ORDER BY original, category, source_lang, target_lang
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
                
            items = []
            for row in cursor.fetchall():
                items.append({
                    "source_lang": row[0],
                    "target_lang": row[1],
                    "category": row[2],
                    "original": row[3],
                    "translated": row[4]
                })
                
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit
        }

    def clear(self, keep_count: int | None = None) -> None:
        """Clear the cache, optionally keeping `keep_count` newest entries globally."""
        if keep_count is None:
            keep_count = 0
        self.repo.clear(keep_count)

    def invalidate_by_term(self, source_lang: str, target_lang: str, term: str) -> int:
        """Invalidate cache entries containing a specific term."""
        return self.repo.invalidate_by_term(source_lang, target_lang, term)
