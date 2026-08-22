import pytest
import sqlite3
import threading
import time
from atm.storage.repositories.sqlite_translation_cache import SQLiteTranslationCache

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_cache.db"
    return SQLiteTranslationCache(str(db_file))

def test_sqlite_cache_set_get(temp_db):
    temp_db.set("ja", "vi", "default", "hello", "xin cho")
    val = temp_db.get("ja", "vi", "default", "hello")
    assert val == "xin cho"
    assert temp_db.get("ja", "vi", "default", "missing") is None

def test_sqlite_cache_upsert(temp_db):
    temp_db.set("ja", "vi", "default", "hello", "xin cho")
    temp_db.set("ja", "vi", "default", "hello", "chAo mi ng0?Ai")
    val = temp_db.get("ja", "vi", "default", "hello")
    assert val == "chAo mi ng0?Ai"
    assert temp_db.count() == 1

def test_sqlite_cache_batch(temp_db):
    data = [("ja", "vi", "default", f"k{i}", f"v{i}") for i in range(100)]
    temp_db.set_batch(data)
    assert temp_db.count() == 100
    assert temp_db.get("ja", "vi", "default", "k50") == "v50"

def test_sqlite_concurrency(temp_db):
    temp_db.set("ja", "vi", "default", "key", "value")
    
    errors = []
    def reader():
        try:
            for _ in range(100):
                temp_db.get("ja", "vi", "default", "key")
        except Exception as e:
            errors.append(e)

    def writer():
        try:
            for i in range(100):
                temp_db.set("ja", "vi", "default", f"new_key_{i}", f"val_{i}")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=reader) for _ in range(4)]
    threads.append(threading.Thread(target=writer))
    
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert temp_db.count() == 101

def test_auto_prune(temp_db):
    temp_db.set("ja", "vi", "default", "k1", "v1")
    temp_db.set("ja", "vi", "default", "k2", "v2")
    
    # Manual update to last_accessed_at to simulate old entries
    with temp_db.transaction() as conn:
        old_time = time.time() - (40 * 24 * 3600)
        conn.execute("UPDATE cache SET last_accessed_at = ?", (old_time,))
    
    deleted = temp_db.prune_old_entries(days_old=30, limit=1)
    assert deleted == 1
    assert temp_db.count() == 1
