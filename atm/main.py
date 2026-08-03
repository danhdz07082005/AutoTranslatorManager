import sys
import os
import webview

# Tăng recursion limit để tránh lỗi AccessibilityObject trên Windows (.NET backend)
sys.setrecursionlimit(10000)

# Đảm bảo thư mục cha được nạp vào sys.path để tránh lỗi ModuleNotFoundError
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from atm.utils.logger import get_logger
from atm.container.bootstrap import bootstrap_app

def main() -> None:
    logger = get_logger(__name__, "launcher.log")
    
    logger.info("=========================================")
    logger.info("   AUTO TRANSLATOR MANAGER LAUNCHING     ")
    logger.info("=========================================")
    
    # Bootstrap application (DI, Plugins, EventBus)
    bootstrap_app()
    
    # Khởi tạo Web UI Backend API
    from atm.ui.api import BackendApi
    api = BackendApi()
    
    # Tính toán đường dẫn tới index.html
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    html_path = os.path.join(base_path, 'atm', 'ui', 'web', 'index.html')
    
    # Tạo cửa sổ WebView
    window = webview.create_window(
        title='Auto Translator Manager', 
        url=html_path, 
        js_api=api,
        width=1000,
        height=650,
        min_size=(800, 500)
    )
    api.set_window(window)
    
    # Chạy WebView - dùng private_mode=False để tránh lỗi COM trên một số máy Windows
    webview.start(debug=False, private_mode=False)

if __name__ == "__main__":
    main()
