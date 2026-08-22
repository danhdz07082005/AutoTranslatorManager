import sys
import os
import threading
import webbrowser
import time
import mimetypes

mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')



from atm.utils.logger import get_logger
from atm.container.bootstrap import bootstrap_app
from atm.ui.api import BackendApi
from atm.ui.server import create_server
from atm.core.lifecycle import ApplicationLifecycle

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

    api.server_port = port
    os.environ['ATM_SERVER_PORT'] = str(port)
    logger.info(f"Starting local HTTP server on port {port}")
    server = create_server(port, api)
    
    # Chạy server ở thread riêng
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    
    # Mở trình duyệt mặc định
    import time
    url = f"http://127.0.0.1:{port}?t={int(time.time())}"
    logger.info(f"Mở trình duyệt: {url}")
    time.sleep(0.5) # Chờ server sẵn sàng
    webbrowser.open(url)
    
    print(f"\n[ATM] Giao dien dang chay tai: {url}")
    print("[ATM] Vui long KHONG dong cua so dong lenh nay trong luc su dung!")
    print("[ATM] (Dong cua so nay se tat hoan toan ung dung)\n")
    
    lifecycle = ApplicationLifecycle()
    
    # Giữ main thread sống
    try:
        while not lifecycle.should_shutdown():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Nhan tin hieu Ctrl+C")

    logger.info("Bat dau quy trinh tat (Graceful Shutdown)...")
    lifecycle.begin_shutdown()
    
    # Dọn dẹp an toàn
    try:
        # Lấy tất cả game_id đang hoạt động
        active_games = set(list(api.active_deployers.keys()) + list(api.cancel_flags.keys()))
        for game_id in active_games:
            logger.info(f"Dừng game/translation: {game_id}")
            api.stop_game(game_id)
            
        logger.info("Tat JobManager...")
        api.job_manager.shutdown(wait=True)
            
    except Exception as e:
        logger.error(f"Lỗi trong quá trình dọn dẹp game process: {e}")
        
    logger.info("Tat HTTP server...")
    server.shutdown()
    logger.info("ATM da tat hoan toan.")
    sys.exit(0)

if __name__ == "__main__":
    main()
