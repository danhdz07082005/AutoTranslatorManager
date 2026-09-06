import sqlite3
import time
import contextlib
import threading
from typing import Optional, List


from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class SQLiteTranslationCache:
    """Thread-safe SQLite repository for translation cache with WAL and busy_timeout."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            c = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False, isolation_level=None)
            c.execute("PRAGMA auto_vacuum=FULL;")
            c.execute("PRAGMA journal_mode=WAL;")
            c.execute("PRAGMA synchronous=NORMAL;")
            c.execute("PRAGMA busy_timeout=30000;")
            self._local.conn = c
        return self._local.conn

    @contextlib.contextmanager
    def transaction(self):
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE;")
            yield conn
            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")
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
                    hit_count INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (source_lang, target_lang, category, original)
                )
            ''')
            # Thêm index cho last_accessed_at để dọn dẹp nhanh hơn
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_accessed ON cache(last_accessed_at)")

    def get(self, source_lang: str, target_lang: str, category: str, original: str, debounce_seconds: float = 300.0) -> Optional[str]:
        # Avoid explicit transaction block for SELECT to prevent SQLite from creating 
        # a new journal/lock for every single read operation in a tight loop.
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT translated, last_accessed_at, hit_count 
                FROM cache 
                WHERE source_lang = ? AND target_lang = ? AND category = ? AND original = ?
            """, (source_lang, target_lang, category, original))
            
            row = cursor.fetchone()
            if row:
                translated, last_accessed_at, hit_count = row
                now = time.time()
                # Chỉ cập nhật lại nếu thời gian truy cập vượt quá thời gian debounce
                if now - last_accessed_at > debounce_seconds:
                    # Update without locking the main thread with a transaction
                    try:
                        conn.execute("""
                            UPDATE cache SET last_accessed_at = ?, hit_count = ?
                            WHERE source_lang = ? AND target_lang = ? AND category = ? AND original = ?
                        """, (now, hit_count + 1, source_lang, target_lang, category, original))
                    except sqlite3.OperationalError as e:
                        logger.debug(f"Failed to update cache hit count (non-critical): {e}")
                        
                return translated
            return None
        except sqlite3.Error as e:
            logger.error(f"SQLite GET error: {e}")
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
        conn = self._get_connection()
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

    def clear(self, keep_count: int = 0, clear_game_lines: bool = False):
        with self.transaction() as conn:
            if keep_count <= 0:
                conn.execute("DELETE FROM cache")
                if clear_game_lines:
                    table_exists = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='game_lines'"
                    ).fetchone()
                    if table_exists:
                        conn.execute("DELETE FROM game_lines")
            else:
                conn.execute('''
                    DELETE FROM cache
                    WHERE rowid NOT IN (
                        SELECT rowid FROM cache
                        ORDER BY last_accessed_at DESC
                        LIMIT ?
                    )
                ''', (keep_count,))
        
        # Close connection and run VACUUM + wal_checkpoint(TRUNCATE) on a dedicated connection
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        try:
            conn.execute("VACUUM")
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            conn.close()

    def run_integrity_check(self) -> bool:
        conn = self._get_connection()
        cursor = conn.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        return bool(result and result[0] == "ok")

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
        
        Args:
            source_lang: The source language code (e.g. 'auto')
            target_lang: The target language code (e.g. 'vi')
            terms: List of string terms to invalidate
        Returns:
            Number of rows deleted
        """
        if not terms:
            return 0
            
        total_deleted = 0
        CHUNK_SIZE = 500
        with self.transaction() as conn:
            for i in range(0, len(terms), CHUNK_SIZE):
                chunk = terms[i:i + CHUNK_SIZE]
                like_clauses = " OR ".join(["original LIKE ?" for _ in chunk])
                query = f"DELETE FROM cache WHERE source_lang = ? AND target_lang = ? AND ({like_clauses})"
                
                params = [source_lang, target_lang]
                params.extend([f"%{term}%" for term in chunk])
                
                cursor = conn.execute(query, params)
                total_deleted += cursor.rowcount
        return total_deleted

    def batch_delete_exact(self, originals: list) -> int:
        """Delete exact cache entries based on a list of original strings."""
        if not originals:
            return 0
            
        total_deleted = 0
        CHUNK_SIZE = 500
        with self.transaction() as conn:
            for i in range(0, len(originals), CHUNK_SIZE):
                chunk = originals[i:i + CHUNK_SIZE]
                placeholders = ",".join(["?" for _ in chunk])
                query = f"DELETE FROM cache WHERE original IN ({placeholders})"
                cursor = conn.execute(query, chunk)
                total_deleted += cursor.rowcount
        return total_deleted
