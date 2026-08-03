import sys
import os
import logging
import webview

# Đảm bảo thư mục cha được nạp vào sys.path để tránh lỗi ModuleNotFoundError
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from atm.utils.logger import get_logger
from atm.container.bootstrap import bootstrap_app

def main() -> None:
    # 1. Setup logging
    logger = get_logger(__name__, "launcher.log")
    
    logger.info("=========================================")
    logger.info("   AUTO TRANSLATOR MANAGER LAUNCHING     ")
    logger.info("=========================================")
    
    # 2. Bootstrap application (DI, Plugins, EventBus)
    bootstrap_app()
    
    # 3. Khởi tạo Web UI Backend API
    from atm.ui.api import BackendApi
    api = BackendApi()
    
    # Tính toán đường dẫn tới index.html
    # Khi chạy qua PyInstaller, sys._MEIPASS chứa các file add-data
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    html_path = os.path.join(base_path, 'atm', 'ui', 'web', 'index.html')
    
    # 4. Tạo cửa sổ WebView
    window = webview.create_window(
        title='Auto Translator Manager', 
        url=html_path, 
        js_api=api,
        width=1000,
        height=650,
        min_size=(800, 500)
    )
    api.set_window(window)
    
    # 5. Chạy WebView
    webview.start(debug=False)

if __name__ == "__main__":
    main()
