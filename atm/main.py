import sys
import os

# Đảm bảo thư mục cha được nạp vào sys.path để tránh lỗi ModuleNotFoundError
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from atm.container.bootstrap import bootstrap_app
from atm.ui.views.main_view import MainApp
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

def main() -> None:
    try:
        logger.info("=========================================")
        logger.info("   AUTO TRANSLATOR MANAGER LAUNCHING     ")
        logger.info("=========================================")
        
        # Bước 1: Khởi tạo các DI Container và Load config
        bootstrap_app()
        
        # Bước 2: Khởi chạy UI chính
        app = MainApp()
        app.mainloop()
        
    except Exception as e:
        logger.critical(f"Application crashed during startup: {e}", exc_info=True)
        sys.exit(1)
        
if __name__ == "__main__":
    main()
