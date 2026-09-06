import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name: str, log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
    """
    Tạo và cấu hình logger với RotatingFileHandler.
    Mỗi module nên gọi: logger = get_logger(__name__, "module_name.log")
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(level)
        
        file_path = os.path.join(LOG_DIR, log_file)
        
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Thay vì dùng RotatingFileHandler (hay gây WinError 32 trên Windows), ta dùng FileHandler chế độ 'w' (xoá cũ)
        file_handler = logging.FileHandler(file_path, mode='w', encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        # Thêm console handler khi debug
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger
