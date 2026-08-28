import os
import shutil
from typing import List
from atm.utils.logger import get_logger

logger = get_logger(__name__, "deploy.log")

def copy_payload(src_dir: str, dest_dir: str) -> List[str]:
    """
    Copy toàn bộ nội dung từ src_dir sang dest_dir.
    Trả về danh sách các đường dẫn tuyệt đối của các file/folder đã copy 
    để sau này phục vụ việc dọn rác (cleanup).
    """
    copied_items = []
    
    def recursive_copy(current_src, current_dest):
        os.makedirs(current_dest, exist_ok=True)
        for item in os.listdir(current_src):
            s = os.path.join(current_src, item)
            d = os.path.join(current_dest, item)
            
            if os.path.exists(d):
                if os.path.isdir(s):
                    # Directory exists, recursively merge it
                    recursive_copy(s, d)
                else:
                    # File exists, skip to avoid overwriting user data
                    logger.warning(f"File {d} already exists. Skipping to avoid overwriting user data.")
            else:
                # Does not exist, copy and track
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
                copied_items.append(d)
                logger.info(f"Copied: {s} -> {d}")
                
    try:
        recursive_copy(src_dir, dest_dir)
    except Exception as e:
        logger.error(f"Error copying payload from {src_dir} to {dest_dir}: {e}")
        
    return copied_items

def cleanup_items(items: List[str]) -> None:
    """Xóa sạch sẽ các file/folder đã được copy vào (dựa theo danh sách truyền vào)."""
    for item in items:
        try:
            if not os.path.exists(item):
                continue
            if os.path.isdir(item):
                shutil.rmtree(item)
                logger.info(f"Cleaned up directory: {item}")
            else:
                os.remove(item)
                logger.info(f"Cleaned up file: {item}")
        except Exception as e:
            logger.error(f"Failed to cleanup {item}: {e}")
