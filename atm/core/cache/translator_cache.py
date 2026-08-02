import sqlite3
import os
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

CACHE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "cache.db")

class TranslatorCache:
    """Bộ nhớ đệm SQLite để lưu các câu đã dịch, giảm thiểu API Call."""
    
    def __init__(self) -> None:
        self._init_db()
        
    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(CACHE_DB_PATH)
        
    def _init_db(self) -> None:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS translation_cache (
                        original_text TEXT,
                        source_lang TEXT,
                        target_lang TEXT,
                        translated_text TEXT,
                        translator_id TEXT,
                        PRIMARY KEY (original_text, source_lang, target_lang, translator_id)
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize TranslatorCache DB: {e}")

    def get_translation(self, original_text: str, source_lang: str, target_lang: str, translator_id: str) -> str | None:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT translated_text FROM translation_cache
                    WHERE original_text = ? AND source_lang = ? AND target_lang = ? AND translator_id = ?
                """, (original_text, source_lang, target_lang, translator_id))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None

    def save_translation(self, original_text: str, source_lang: str, target_lang: str, translator_id: str, translated_text: str) -> None:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO translation_cache 
                    (original_text, source_lang, target_lang, translated_text, translator_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (original_text, source_lang, target_lang, translated_text, translator_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Cache write error: {e}")
