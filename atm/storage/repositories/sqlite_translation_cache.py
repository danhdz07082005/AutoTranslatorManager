import sqlite3
import os
import threading
import time
import contextlib
from typing import Dict, Optional, List
from contextlib import contextmanager

from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class SQLiteTranslationCache:
    """Thread-safe SQLite repository for translation cache with WAL and busy_timeout."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False, isolation_level=None)
        c.execute("PRAGMA auto_vacuum=FULL;")
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("PRAGMA synchronous=NORMAL;")
        c.execute("PRAGMA busy_timeout=30000;")
        return c

    @contextlib.contextmanager
    def transaction(self):
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

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
                    hit_count INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (source_lang, target_lang, category, original)
                )
            ''')
            # Thêm index cho last_accessed_at để dọn dẹp nhanh hơn
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_accessed ON cache(last_accessed_at)")

    def get(self, source_lang: str, target_lang: str, category: str, original: str, debounce_seconds: float = 300.0) -> Optional[str]:
        # Avoid explicit transaction block for SELECT to prevent SQLite from creating 
        # a new journal/lock for every single read operation in a tight loop.
        with contextlib.closing(self._get_connection()) as conn:
            cursor = conn.execute("""
                SELECT translated, last_accessed_at, hit_count 
                FROM cache 
                WHERE source_lang = ? AND target_lang = ? AND category = ? AND original = ?
            """, (source_lang, target_lang, category, original))
            
            row = cursor.fetchone()
            if row:
                translated, last_accessed_at, hit_count = row
                now = time.time()
                # Ch? c?p nh?t l?i n?u th?i gian truy c?p vu?t qu? th?i gian debounce
                if now - last_accessed_at > debounce_seconds:
                    # Update without locking the main thread with a transaction
                    try:
                        conn.execute("""
                            UPDATE cache SET last_accessed_at = ?, hit_count = ?
                            WHERE source_lang = ? AND target_lang = ? AND category = ? AND original = ?
                        """, (now, hit_count + 1, source_lang, target_lang, category, original))
                    except sqlite3.OperationalError:
                        pass # Ignore lock errors on hit_count updates to avoid crashing reads
                
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
        
        # Auto-vacuum is enabled on the DB, so we don't need manual VACUUM here anymore.
        pass

    def run_integrity_check(self) -> bool:
        with self.transaction() as conn:
            cursor = conn.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            return result and result[0] == "ok"

    def invalidate_by_term(self, source_lang: str, target_lang: str, term: str) -> int:
        """Xóa các bản dịch chứa term (từ vựng) bị thay đổi trong Glossary."""
        with self.transaction() as conn:
            # Dùng %term% để tìm chuỗi con. SQLite LIKE mặc định không phân biệt hoa thường với ASCII.
            cursor = conn.execute("""
                DELETE FROM cache
                WHERE source_lang = ? AND target_lang = ? AND original LIKE ?
            """, (source_lang, target_lang, f'%{term}%'))
            return cursor.rowcount

    def batch_invalidate_by_terms(self, source_lang: str, target_lang: str, terms: list) -> int:
        """Batch-delete cache entries containing ANY of the given terms in a SINGLE transaction.
        
        This is O(1) transactions instead of O(N) transactions like calling invalidate_by_term
        in a loop - critical for large glossary imports (10,000+ terms).
        """
        if not terms:
            return 0
        total_deleted = 0
        with self.transaction() as conn:
            for term in terms:
                cursor = conn.execute("""
                    DELETE FROM cache
                    WHERE source_lang = ? AND target_lang = ? AND original LIKE ?
                """, (source_lang, target_lang, f'%{term}%'))
                total_deleted += cursor.rowcount
        return total_deleted
