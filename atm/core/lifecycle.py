import time
import threading
from enum import Enum, auto
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class AppState(Enum):
    RUNNING = auto()
    SHUTDOWN_REQUESTED = auto()
    SHUTTING_DOWN = auto()
    STOPPED = auto()

class ApplicationLifecycle:
    """Quản lý trạng thái và chu kỳ sống của ứng dụng (Graceful Shutdown & Heartbeat)."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ApplicationLifecycle, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.state = AppState.RUNNING
        self.active_clients = {}
        self.grace_period_seconds = 15
        self.start_time = time.time()
        self.last_active_time = time.time()
        self.lock = threading.Lock()
        
    def update_heartbeat(self, client_id: str):
        """Cập nhật thời gian ping cuối của một client."""
        with self.lock:
            if self.state == AppState.RUNNING:
                self.active_clients[client_id] = time.time()
                self.last_active_time = time.time()
                
    def request_shutdown(self) -> bool:
        """Yêu cầu tắt ứng dụng từ người dùng."""
        with self.lock:
            if self.state == AppState.RUNNING:
                self.state = AppState.SHUTDOWN_REQUESTED
                logger.info("🔌 Received explicit shutdown request.")
                return True
            return False

    def is_shutdown_requested(self) -> bool:
        return self.state == AppState.SHUTDOWN_REQUESTED
        
    def begin_shutdown(self):
        """Đánh dấu bắt đầu quá trình dọn dẹp và tắt server."""
        with self.lock:
            self.state = AppState.SHUTTING_DOWN
            
    def is_shutting_down(self) -> bool:
        return self.state in (AppState.SHUTTING_DOWN, AppState.STOPPED)

    def should_shutdown(self) -> bool:
        """Kiểm tra xem hệ thống có nên tắt (do request hoặc do mồ côi)."""
        with self.lock:
            if self.state == AppState.SHUTDOWN_REQUESTED:
                return True
                
            if self.state == AppState.RUNNING:
                now = time.time()
                # Remove dead clients
                dead_clients = [cid for cid, t in self.active_clients.items() if now - t > self.grace_period_seconds]
                for cid in dead_clients:
                    del self.active_clients[cid]
                
                # Check for orphaned state
                if len(self.active_clients) == 0:
                    # If we had clients before but they all died, check grace period against last active time
                    if now - self.last_active_time > self.grace_period_seconds:
                        logger.warning("💔 Heartbeat grace period expired! No active UI clients left.")
                        self.state = AppState.SHUTDOWN_REQUESTED
                        return True
        return False
