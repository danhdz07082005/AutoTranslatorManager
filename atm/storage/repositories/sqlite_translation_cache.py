import sqlite3
import os
import threading
import time
from typing import Dict, Optional, List
from contextlib import contextmanager

from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class SQLiteTranslationCache:
    """Thread-safe SQLite repository for translation cache with WAL and busy_timeout."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            c = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            c.execute("PRAGMA journal_mode=WAL;")
            c.execute("PRAGMA synchronous=NORMAL;")
            c.execute("PRAGMA busy_timeout=30000;")
            self._local.conn = c
        return self._local.conn

    @contextmanager
    def transaction(self):
        conn = self.conn
        try:
            with conn:
                yield conn
        except Exception as e:
            logger.error(f"Transaction failed: {e}", exc_info=True)
            raise

    def _init_db(self):
        with self.transaction() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    category TEXT NOT NULL,
                    original TEXT NOT NULL,
                    translated TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_accessed_at REAL NOT NULL,
                    PRIMARY KEY (source_lang, target_lang, category, original)
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_last_accessed 
                ON cache(last_accessed_at)
            ''')

    def get(self, source_lang: str, target_lang: str, category: str, original: str, debounce_seconds: float = 300.0) -> Optional[str]:
        # Avoid explicit transaction block for SELECT to prevent SQLite from creating 
        # a new journal/lock for every single read operation in a tight loop.
        cursor = self.conn.execute('''
            SELECT translated, last_accessed_at FROM cache 
            WHERE source_lang = ? AND target_lang = ? AND category = ? AND original = ?
        ''', (source_lang, target_lang, category, original))
        row = cursor.fetchone()
        
        if row:
            translated, last_accessed_at = row
            now = time.time()
            if now - last_accessed_at > debounce_seconds:
                with self.transaction() as conn:
                    conn.execute('''
                        UPDATE cache SET last_accessed_at = ? 
                        WHERE source_lang = ? AND target_lang = ? AND category = ? AND original = ?
                    ''', (now, source_lang, target_lang, category, original))
            return translated
        return None

    def set(self, source_lang: str, target_lang: str, category: str, original: str, translated: str):
        now = time.time()
        with self.transaction() as conn:
            conn.execute('''
                INSERT INTO cache (source_lang, target_lang, category, original, translated, created_at, last_accessed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_lang, target_lang, category, original) DO UPDATE SET 
                    translated = excluded.translated,
                    last_accessed_at = excluded.last_accessed_at
            ''', (source_lang, target_lang, category, original, translated, now, now))

    def set_batch(self, entries: List[tuple[str, str, str, str, str]]):
        """entries is a list of (source_lang, target_lang, category, original, translated)"""
        now = time.time()
        with self.transaction() as conn:
            conn.executemany('''
                INSERT INTO cache (source_lang, target_lang, category, original, translated, created_at, last_accessed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_lang, target_lang, category, original) DO UPDATE SET 
                    translated = excluded.translated,
                    last_accessed_at = excluded.last_accessed_at
            ''', [(sl, tl, cat, orig, trans, now, now) for sl, tl, cat, orig, trans in entries])

    def count(self) -> int:
        with self.transaction() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM cache")
            return cursor.fetchone()[0]

    def prune_old_entries(self, days_old: int = 30, limit: int = 1000) -> int:
        cutoff_time = time.time() - (days_old * 24 * 3600)
        with self.transaction() as conn:
            cursor = conn.execute('''
                DELETE FROM cache
                WHERE rowid IN (
                    SELECT rowid FROM cache
                    WHERE last_accessed_at < ?
                    LIMIT ?
                )
            ''', (cutoff_time, limit))
            return cursor.rowcount

    def clear(self, keep_count: int = 0):
        with self.transaction() as conn:
            if keep_count <= 0:
                conn.execute("DELETE FROM cache")
            else:
                conn.execute('''
                    DELETE FROM cache
                    WHERE rowid NOT IN (
                        SELECT rowid FROM cache
                        ORDER BY last_accessed_at DESC
                        LIMIT ?
                    )
                ''', (keep_count,))
        
        # Force WAL checkpoint to allow VACUUM to shrink the file effectively
        with self.transaction() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

        # Run VACUUM outside the transaction block to reclaim disk space
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("VACUUM")

    def run_integrity_check(self) -> bool:
        with self.transaction() as conn:
            cursor = conn.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            return result and result[0] == "ok"
