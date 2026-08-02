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
    try:
        for item in os.listdir(src_dir):
            s = os.path.join(src_dir, item)
            d = os.path.join(dest_dir, item)
            
            if os.path.exists(d):
                logger.warning(f"File/Folder {item} already exists in target. Skipping to avoid overwriting user data.")
                continue
                
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
                
            copied_items.append(d)
            logger.info(f"Copied: {item} -> {dest_dir}")
            
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
