import sys
import os
import tempfile
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
    
    # Tạo thư mục tạm riêng cho WebView2 user data (tránh lỗi "resource in use")
    storage_path = tempfile.mkdtemp(prefix="atm_webview_")
    
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
    
    # Chạy WebView
    # private_mode=True (mặc định) = tạo thư mục tạm mỗi lần chạy, không bị khóa
    # storage_path = thư mục riêng cho WebView2 data, tránh xung đột
    try:
        webview.start(debug=False, storage_path=storage_path)
    except Exception as e:
        logger.error(f"WebView failed: {e}")
        logger.info("Thử mở trình duyệt thay thế...")
        # Fallback: mở bằng trình duyệt mặc định
        import webbrowser
        webbrowser.open(f"file:///{html_path}")
        input("Nhấn Enter để thoát...")
    finally:
        # Dọn thư mục tạm
        try:
            import shutil
            shutil.rmtree(storage_path, ignore_errors=True)
        except Exception:
            pass

if __name__ == "__main__":
    main()
