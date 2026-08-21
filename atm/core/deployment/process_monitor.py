import subprocess
import threading
import time
import psutil
from typing import Callable, Optional
from atm.utils.logger import get_logger

logger = get_logger(__name__, "deploy.log")

class ProcessMonitor:
    """Theo dõi vòng đời của một tiến trình (Game) và toàn bộ tiến trình con."""
    
    def __init__(self) -> None:
        self.process: Optional[subprocess.Popen] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.is_monitoring = False

    def start_and_monitor(self, exe_path: str, cwd: str, on_exit_callback: Callable[[], None]) -> bool:
        """
        Chạy exe và tạo một luồng chạy ngầm để chờ tiến trình (và các tiến trình con) tắt, 
        sau đó gọi callback để dọn rác. Tránh lỗi cleanup sớm khi game có launcher.
        """
        try:
            logger.info(f"Starting process: {exe_path} in {cwd}")
            self.process = subprocess.Popen(exe_path, cwd=cwd)
            self.is_monitoring = True
            
            def wait_for_exit() -> None:
                # Đợi một chút để tiến trình con (nếu có) kịp spawn
                time.sleep(2.0)
                
                try:
                    if not self.process:
                        return
                    
                    main_pid = self.process.pid
                    try:
                        parent = psutil.Process(main_pid)
                    except psutil.NoSuchProcess:
                        logger.info("Main process exited immediately.")
                        if self.is_monitoring:
                            self.is_monitoring = False
                            on_exit_callback()
                        return

                    while self.is_monitoring:
                        try:
                            # Lấy toàn bộ cây tiến trình
                            procs = [parent] + parent.children(recursive=True)
                        except psutil.NoSuchProcess:
                            procs = []
                            
                        still_alive = False
                        for p in procs:
                            try:
                                if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                                    still_alive = True
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                                
                        if not still_alive:
                            break
                            
                        time.sleep(1.0) # Poll mỗi giây
                        
                except Exception as e:
                    logger.error(f"Process monitoring error: {e}")
                finally:
                    if self.is_monitoring:
                        logger.info("Process tree exited. Triggering cleanup callback.")
                        self.is_monitoring = False
                        on_exit_callback()

            self.monitor_thread = threading.Thread(target=wait_for_exit, daemon=True)
            self.monitor_thread.start()
            return True
            
        except Exception as e:
            logger.error(f"Failed to start process {exe_path}: {e}")
            self.is_monitoring = False
            # Nếu khởi động thất bại, gọi dọn rác ngay lập tức
            on_exit_callback()
            return False

    def stop(self) -> None:
        """Dừng tiến trình và toàn bộ cây tiến trình nếu đang chạy."""
        self.is_monitoring = False
        if self.process:
            logger.info("Stopping process tree manually...")
            try:
                main_pid = self.process.pid
                try:
                    parent = psutil.Process(main_pid)
                    procs = parent.children(recursive=True)
                    # Kill con trước
                    for p in procs:
                        try:
                            p.kill()
                        except psutil.NoSuchProcess:
                            pass
                    # Kill cha sau
                    parent.kill()
                except psutil.NoSuchProcess:
                    # Nếu parent chết rồi thì pass
                    pass
            except Exception as e:
                logger.error(f"Error killing process tree: {e}")
