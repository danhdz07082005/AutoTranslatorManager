import os
from typing import List, Any
from atm.core.events.event_bus import EventBus, SystemEvents
from atm.core.deployment.process_monitor import ProcessMonitor
from atm.utils.file_system import copy_payload, cleanup_items
from atm.utils.logger import get_logger
from atm.config.schema import GameProfile

logger = get_logger(__name__, "deploy.log")

class GameDeployer:
    """Quản lý việc Copy -> Launch -> Cleanup."""
    
    def __init__(self) -> None:
        self.monitor = ProcessMonitor()
        # Chứa danh sách các file/folder đã copy vào game để dọn dẹp sau này
        self._deployed_items: List[str] = []

    def deploy_and_launch(self, profile: GameProfile, payload_dir: str) -> None:
        """
        1. Copy payload vào thư mục game.
        2. Khởi động game.
        3. Cài đặt callback để dọn rác khi game tắt.
        """
        game_dir = os.path.dirname(profile.exe_path)
        logger.info(f"Preparing deployment for {profile.game_name} at {game_dir}")
        
        EventBus.publish(SystemEvents.GAME_STARTING, profile)

        # 1. Copy (Deploy)
        if not os.path.exists(payload_dir):
            logger.error(f"Payload directory not found: {payload_dir}")
            EventBus.publish(SystemEvents.ERROR_OCCURRED, "Payload not found!")
            return

        self._deployed_items = copy_payload(payload_dir, game_dir)
        EventBus.publish(SystemEvents.DEPLOYMENT_FINISHED, self._deployed_items)

        # 2. Launch
        success = self.monitor.start_and_monitor(
            exe_path=profile.exe_path,
            cwd=game_dir,
            on_exit_callback=self._on_game_exited
        )
        
        if success:
            logger.info("Game launched successfully. Monitoring...")
        else:
            logger.error("Failed to launch game. Cleanup triggered early.")

    def _on_game_exited(self) -> None:
        """Callback chạy ngầm khi tiến trình game tắt."""
        EventBus.publish(SystemEvents.GAME_EXITED)
        
        logger.info("Starting cleanup process...")
        cleanup_items(self._deployed_items)
        self._deployed_items.clear()
        
        EventBus.publish(SystemEvents.CLEANUP_FINISHED)
        logger.info("Cleanup complete. Game directory is pristine.")
