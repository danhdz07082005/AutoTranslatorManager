import os
import json
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

def atomic_write(filepath: str, data: str) -> bool:
    """Ghi file JSON an toàn (atomic write) để tránh corrupt data khi bị crash ngang"""
    tmp_path = filepath + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, filepath)
        return True
    except Exception as e:
        logger.error(f"Atomic write failed for {filepath}: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return False
