import subprocess
import threading
from typing import Callable, Optional
from atm.utils.logger import get_logger

logger = get_logger(__name__, "deploy.log")

class ProcessMonitor:
    """Theo dõi vòng đời của một tiến trình (Game)."""
    
    def __init__(self) -> None:
        self.process: Optional[subprocess.Popen] = None
        self.monitor_thread: Optional[threading.Thread] = None

    def start_and_monitor(self, exe_path: str, cwd: str, on_exit_callback: Callable[[], None]) -> bool:
        """
        Chạy exe và tạo một luồng chạy ngầm để chờ tiến trình tắt, 
        sau đó gọi callback để dọn rác.
        """
        try:
            logger.info(f"Starting process: {exe_path} in {cwd}")
            self.process = subprocess.Popen(exe_path, cwd=cwd)
            
            def wait_for_exit() -> None:
                if self.process:
                    self.process.wait()
                    logger.info("Process exited. Triggering cleanup callback.")
                    on_exit_callback()

            self.monitor_thread = threading.Thread(target=wait_for_exit, daemon=True)
            self.monitor_thread.start()
            return True
            
        except Exception as e:
            logger.error(f"Failed to start process {exe_path}: {e}")
            # Nếu khởi động thất bại, gọi dọn rác ngay lập tức
            on_exit_callback()
            return False
