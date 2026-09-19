import sqlite3
import os
import time
import contextlib
from typing import Dict, Optional, List, Tuple

from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class SQLiteGameLinesRepository:
    """Thread-safe SQLite repository for game_lines (game specific translation data)."""
    
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
        # Fast read check: if table already exists, do not trigger a write transaction
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='game_lines'")
            if cursor.fetchone():
                return
        finally:
            conn.close()

        with self.transaction() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS game_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    original TEXT NOT NULL,
                    translated TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'default',
                    source_file TEXT,
                    source_path TEXT,
                    version INTEGER NOT NULL DEFAULT 1,
                    updated_at REAL NOT NULL,
                    UNIQUE(game_id, original, category)
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_game_lines_game_id 
                ON game_lines(game_id)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_game_lines_game_updated 
                ON game_lines(game_id, updated_at DESC)
            ''')

    def list_by_game(self, game_id: str, page: int = 1, limit: int = 50, query: Optional[str] = None) -> dict:
        offset = (page - 1) * limit
        
        sql = "SELECT id, original, translated, category, version, updated_at FROM game_lines WHERE game_id = ?"
        params = [game_id]
        
        if query:
            sql += " AND (original LIKE ? OR translated LIKE ?)"
            like_val = f"%{query}%"
            params.extend([like_val, like_val])
            
        sql += " ORDER BY id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        count_sql = "SELECT COUNT(*) FROM game_lines WHERE game_id = ?"
        count_params = [game_id]
        if query:
            count_sql += " AND (original LIKE ? OR translated LIKE ?)"
            count_params.extend([like_val, like_val])
            
        with contextlib.closing(self._get_connection()) as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            
            count_cursor = conn.execute(count_sql, count_params)
            total = count_cursor.fetchone()[0]
        
        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "original": row[1],
                "translated": row[2],
                "category": row[3],
                "version": row[4],
                "updated_at": row[5]
            })
            
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit
        }

    def get_all_by_game(self, game_id: str) -> dict:
        """Fetch all translations for a game as a dict of {original: translated}.
        Ordered by updated_at ASC so the most recent edits overwrite older entries in dict."""
        with contextlib.closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT original, translated FROM game_lines WHERE game_id = ? ORDER BY updated_at ASC", (game_id,))
            return {row[0]: row[1] for row in cursor.fetchall()}

    def count_by_game(self, game_id: str) -> int:
        """Count total lines stored for a game."""
        with contextlib.closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM game_lines WHERE game_id = ?", (game_id,))
            return cursor.fetchone()[0]

    def update(self, item_id: int, game_id: str, translated: str, expected_version: int) -> bool:
        """
        Updates a translation if the expected_version matches AND it belongs to the game_id.
        Also synchronizes any sibling rows with the same original text.
        Returns True if successful, False if version mismatch or not found.
        """
        now = time.time()
        with self.transaction() as conn:
            cursor = conn.execute("SELECT original FROM game_lines WHERE id = ? AND game_id = ?", (item_id, game_id))
            row = cursor.fetchone()
            if not row:
                return False
            orig_text = row[0]

            cursor = conn.execute('''
                UPDATE game_lines 
                SET translated = ?, version = version + 1, updated_at = ?
                WHERE id = ? AND game_id = ? AND version = ?
            ''', (translated, now, item_id, game_id, expected_version))
            
            if cursor.rowcount > 0:
                conn.execute('''
                    UPDATE game_lines 
                    SET translated = ?, updated_at = ?
                    WHERE game_id = ? AND original = ? AND id != ?
                ''', (translated, now, game_id, orig_text, item_id))
                return True
            return False

    def batch_update(self, game_id: str, items: List[Tuple[int, str, int]]) -> dict:
        """
        items: list of (id, translated, expected_version)
        Returns dict with saved (list of dicts), conflicts, errors
        """
        saved = []
        conflicts = []
        errors = []
        
        now = time.time()
        with self.transaction() as conn:
            if not items:
                return {"saved": saved, "conflicts": conflicts, "errors": errors}
                
            # 1. Bulk select all items to get current versions and validate game_id
            item_ids = [item[0] for item in items]
            
            db_items = {}
            # Chunking to avoid SQLite variable limit (usually 999 or 32766)
            CHUNK_SIZE = 500
            for i in range(0, len(item_ids), CHUNK_SIZE):
                chunk = item_ids[i:i + CHUNK_SIZE]
                placeholders = ','.join(['?'] * len(chunk))
                cursor = conn.execute(f"SELECT id, original, translated, version, game_id FROM game_lines WHERE id IN ({placeholders})", chunk)
                for row in cursor.fetchall():
                    db_items[row[0]] = {"original": row[1], "translated": row[2], "version": row[3], "game_id": row[4]}
            
            # Prepare batch updates
            update_data = []
            
            for item_id, translated, expected_version in items:
                db_item = db_items.get(item_id)
                if not db_item:
                    errors.append({"id": item_id, "message": "Not found"})
                    continue
                    
                if db_item["game_id"] != game_id:
                    errors.append({"id": item_id, "message": "Game ID mismatch"})
                    continue
                    
                if db_item["version"] != expected_version:
                    conflicts.append({
                        "id": item_id,
                        "current_translated": db_item["translated"],
                        "current_version": db_item["version"]
                    })
                    continue
                
                # Valid for update
                update_data.append((translated, now, item_id, game_id, expected_version))
                saved.append({
                    "id": item_id,
                    "original": db_item["original"],
                    "translated": translated,
                    "version": expected_version + 1
                })
            
            if update_data:
                conn.executemany('''
                    UPDATE game_lines
                    SET translated = ?, version = version + 1, updated_at = ?
                    WHERE id = ? AND game_id = ? AND version = ?
                ''', update_data)
                
        return {
            "saved": saved,
            "conflicts": conflicts,
            "errors": errors
        }

    def insert_or_ignore(self, game_id: str, original: str, translated: str, category: str = "default", source_file: str = None, source_path: str = None):
        """Insert a new line if it doesn't exist, ignore otherwise."""
        now = time.time()
        with self.transaction() as conn:
            conn.execute('''
                INSERT OR IGNORE INTO game_lines 
                (game_id, original, translated, category, source_file, source_path, version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            ''', (game_id, original, translated, category, source_file, source_path, now))

    def batch_insert(self, game_id: str, items: List[dict]):
        """Batch insert lines. items is a list of dicts with original, translated, category, source_file, source_path."""
        if not items:
            return
        now = time.time()
        rows = []
        for it in items:
            rows.append((
                game_id, 
                it.get("original", ""), 
                it.get("translated", ""), 
                it.get("category", "default"),
                it.get("source_file"), 
                it.get("source_path"),
                now
            ))
            
        with self.transaction() as conn:
            conn.executemany('''
                INSERT OR IGNORE INTO game_lines 
                (game_id, original, translated, category, source_file, source_path, version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            ''', rows)

    def get_by_id(self, item_id: int) -> Optional[dict]:
        with contextlib.closing(self._get_connection()) as conn:
            cursor = conn.execute("SELECT id, game_id, original, translated, category, version, updated_at FROM game_lines WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "game_id": row[1],
                    "original": row[2],
                    "translated": row[3],
                    "category": row[4],
                    "version": row[5],
                    "updated_at": row[6]
                }
            return None

    def get_stats_by_game(self) -> list:
        with self.transaction() as conn:
            cursor = conn.execute('''
                SELECT game_id, COUNT(*) as count 
                FROM game_lines 
                GROUP BY game_id
            ''')
            return [{"game_id": row[0], "count": row[1]} for row in cursor.fetchall()]

    def clear_all(self) -> int:
        """Clear all game lines across all games."""
        with self.transaction() as conn:
            cursor = conn.execute("DELETE FROM game_lines")
            deleted = cursor.rowcount
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        try:
            conn.execute("VACUUM")
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            conn.close()
        return deleted

    def clear_by_game(self, game_id: str, keep_count: int = 0) -> list:
        deleted_originals = []
        with self.transaction() as conn:
            if keep_count <= 0:
                cursor = conn.execute("SELECT original FROM game_lines WHERE game_id = ?", (game_id,))
                deleted_originals = [row[0] for row in cursor.fetchall()]
                conn.execute("DELETE FROM game_lines WHERE game_id = ?", (game_id,))
            else:
                cursor = conn.execute('''
                    SELECT original FROM game_lines 
                    WHERE game_id = ? AND id NOT IN (
                        SELECT id FROM game_lines 
                        WHERE game_id = ?
                        ORDER BY updated_at DESC
                        LIMIT ?
                    )
                ''', (game_id, game_id, keep_count))
                deleted_originals = [row[0] for row in cursor.fetchall()]
                
                conn.execute('''
                    DELETE FROM game_lines 
                    WHERE game_id = ? AND id NOT IN (
                        SELECT id FROM game_lines 
                        WHERE game_id = ?
                        ORDER BY updated_at DESC
                        LIMIT ?
                    )
                ''', (game_id, game_id, keep_count))
        
        # Run VACUUM and wal_checkpoint(TRUNCATE) outside transaction to reclaim disk space
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        try:
            conn.execute("VACUUM")
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            conn.close()
        return deleted_originals
