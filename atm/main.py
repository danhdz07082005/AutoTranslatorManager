import sys
import os
import threading
import webbrowser
import time

# Tăng recursion limit để tránh lỗi (dù không còn dùng pywebview nhưng cứ giữ cho chắc)
sys.setrecursionlimit(10000)

# Đảm bảo thư mục cha được nạp vào sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from atm.utils.logger import get_logger
from atm.container.bootstrap import bootstrap_app
from atm.ui.api import BackendApi
from atm.ui.server import create_server

def main() -> None:
    logger = get_logger(__name__, "launcher.log")
    
    logger.info("=========================================")
    logger.info("   AUTO TRANSLATOR MANAGER LAUNCHING     ")
    logger.info("=========================================")
    
    # Bootstrap application
    bootstrap_app()
    
    # Khởi tạo API
    api = BackendApi()
    
    # Khởi tạo HTTP Server trên cổng ngẫu nhiên 
    # (hoặc cố định, nhưng để tránh xung đột cổng thì dùng cổng động)
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()

    logger.info(f"Starting local HTTP server on port {port}")
    server = create_server(port, api)
    
    # Chạy server ở thread riêng
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    
    # Mở trình duyệt mặc định
    url = f"http://127.0.0.1:{port}"
    logger.info(f"Mở trình duyệt: {url}")
    time.sleep(0.5) # Chờ server sẵn sàng
    webbrowser.open(url)
    
    print(f"\n[ATM] Giao dien dang chay tai: {url}")
    print("[ATM] Vui long KHONG dong cua so dong lenh nay trong luc su dung!")
    print("[ATM] (Dong cua so nay se tat hoan toan ung dung)\n")
    
    # Giữ main thread sống
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Tat server...")
        server.shutdown()
        sys.exit(0)

if __name__ == "__main__":
    main()
