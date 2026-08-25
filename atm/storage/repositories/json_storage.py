import os
import json
import uuid
import time
from atm.utils.logger import get_logger

logger = get_logger(__name__, "json_storage.log")

def atomic_write(filepath: str, data: str) -> bool:
    """Ghi file JSON an toàn (atomic write) với retry để tránh WinError 5/32"""
    tmp_path = filepath + f".{uuid.uuid4().hex}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
            
        for attempt in range(5):
            try:
                os.replace(tmp_path, filepath)
                return True
            except OSError as e:
                if attempt == 4:
                    raise
                time.sleep(0.1)
    except Exception as e:
        logger.error(f"Atomic write failed for {filepath}: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return False
