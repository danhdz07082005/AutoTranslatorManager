import os
import shutil
import tempfile
import uuid
from typing import List, Dict, Any, Union
from atm.utils.logger import get_logger

logger = get_logger(__name__, "deploy.log")

def atomic_write(filepath: str, content: Union[str, bytes], mode: str = 'w', encoding: str = 'utf-8') -> bool:
    tmp_path = f"{filepath}.{uuid.uuid4().hex}.tmp"
    try:
        if 'b' in mode:
            with open(tmp_path, mode) as f:
                f.write(content)
        else:
            with open(tmp_path, mode, encoding=encoding) as f:
                f.write(content)
        
        os.replace(tmp_path, filepath)
        return True
    except Exception as e:
        logger.error(f"Atomic write failed for {filepath}: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False

class CopyResult:
    def __init__(self, success: bool, items: List[str] = None, error: str = None):
        self.success = success
        self.copied_items = items or []
        self.error = error

def copy_payload(src_dir: str, dest_dir: str) -> CopyResult:
    copied_items = []
    
    def recursive_copy(current_src, current_dest):
        os.makedirs(current_dest, exist_ok=True)
        for item in os.listdir(current_src):
            s = os.path.join(current_src, item)
            d = os.path.join(current_dest, item)
            
            if os.path.exists(d):
                if os.path.isdir(s):
                    recursive_copy(s, d)
                else:
                    logger.warning(f"File {d} already exists. Skipping.")
            else:
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
                copied_items.append(d)
                logger.info(f"Copied: {s} -> {d}")
                
    try:
        recursive_copy(src_dir, dest_dir)
        return CopyResult(True, copied_items)
    except Exception as e:
        logger.error(f"Error copying payload from {src_dir} to {dest_dir}: {e}")
        return CopyResult(False, copied_items, str(e))

def cleanup_items(items: List[str]) -> None:
    import time
    items_sorted = sorted(items, key=lambda x: len(x), reverse=True)
    for item in items_sorted:
        for attempt in range(4):
            try:
                if not os.path.exists(item):
                    break
                if os.path.isdir(item):
                    shutil.rmtree(item)
                    logger.info(f"Cleaned up directory: {item}")
                else:
                    os.remove(item)
                    logger.info(f"Cleaned up file: {item}")
                break  # Success, exit retry loop
            except Exception as e:
                if attempt < 3:
                    time.sleep(0.5)  # Wait for OS to release file locks
                else:
                    logger.error(f"Failed to cleanup {item} after 4 attempts: {e}")
