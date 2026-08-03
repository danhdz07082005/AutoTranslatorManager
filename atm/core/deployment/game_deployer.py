import os
from typing import List, Any
from atm.core.events.event_bus import EventBus, SystemEvents
from atm.core.deployment.process_monitor import ProcessMonitor
from atm.storage.repositories.settings_repository import SettingsRepository
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
            
        # Đối với RenPy, payload (file .rpy) phải nằm trong thư mục con 'game'
        dest_dir = game_dir
        if profile.engine == "RenPy":
            dest_dir = os.path.join(game_dir, "game")
            os.makedirs(dest_dir, exist_ok=True)

        self._deployed_items = copy_payload(payload_dir, dest_dir)
        
        # Tạo file thông báo cho user
        info_file = os.path.join(game_dir, "ATM_IS_RUNNING.txt")
        try:
            with open(info_file, "w", encoding="utf-8") as f:
                f.write("==== AUTO TRANSLATOR MANAGER ====\n")
                f.write("Launcher đang chạy và đã tự động copy các file dịch thuật tạm thời vào đây.\n")
                f.write("Khi bạn tắt game, toàn bộ các file này (bao gồm cả thư mục BepInEx) sẽ TỰ ĐỘNG BỊ XÓA sạch sẽ.\n")
                f.write("Nếu bạn lỡ tắt đột ngột Launcher, bạn có thể tự tay xóa thư mục BepInEx và winhttp.dll mà không ảnh hưởng gì tới game gốc.\n")
            self._deployed_items.append(info_file)
        except Exception:
            pass

        # Ghi đè cấu hình ngôn ngữ (Tạo file AutoTranslatorConfig.ini)
        config_dir = os.path.join(game_dir, "BepInEx", "config")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "AutoTranslatorConfig.ini")
        try:
            from_lang = profile.input_lang if profile.input_lang and profile.input_lang != "auto" else "ja"
            to_lang = profile.output_lang if profile.output_lang else "vi"
            
            # Load API Key if needed
            settings = SettingsRepository().load()
            
            # Ghi file AutoTranslatorConfig.ini cho BepInEx (Unity)
            if profile.engine != "RenPy":
                is_deepl = getattr(profile, "translator", "google") == "deepl"
                endpoint = "DeepLTranslateLegitimate" if is_deepl else "GoogleTranslateV2"
                
                with open(config_file, "w", encoding="utf-8") as f:
                    f.write("[Service]\n")
                    f.write(f"Endpoint={endpoint}\n\n")
                    f.write("[General]\n")
                    f.write(f"Language={to_lang}\n")
                    f.write(f"FromLanguage={from_lang}\n\n")
                    f.write("[Behaviour]\n")
                    f.write("MaxCharactersPerTranslation=1000\n")
                    f.write("IgnoreWhitespaceInDialogue=False\n")
                    
                    if is_deepl:
                        f.write("\n[DeepLLegitimate]\n")
                        f.write("ExecutableLocation=\n")
                        f.write(f"ApiKey={settings.deepl_api_key}\n")
                        f.write("Free=True\n")
                
                # Thêm thư mục config vào danh sách để xóa (nếu trước đó không có config)
                if config_dir not in self._deployed_items:
                    self._deployed_items.append(config_dir)
                    
            else:
                # Ghi cấu hình cho RenPy Real-time hook
                renpy_config_file = os.path.join(dest_dir, "transconfig.rpy")
                if os.path.exists(renpy_config_file):
                    with open(renpy_config_file, "r", encoding="utf-8") as f:
                        rpy_content = f.read()
                    
                    # Update target_language in config
                    rpy_content = rpy_content.replace('default persistent.target_languages = {"google" : "vi", "bing" : "vi", "freellm" : "vi", "yandex" : "vi"}',
                                                      f'default persistent.target_languages = {{"google" : "{to_lang}", "bing" : "{to_lang}", "freellm" : "{to_lang}", "yandex" : "{to_lang}"}}')
                                                      
                    with open(renpy_config_file, "w", encoding="utf-8") as f:
                        f.write(rpy_content)
        except Exception as e:
            logger.error(f"Failed to create config file: {e}")

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
        
        logger.info("Starting cleanup and log sync process...")
        
        # Đồng bộ log dịch thuật trước khi xóa (nếu có)
        for item in self._deployed_items:
            if os.path.isdir(item) and "BepInEx" in item:
                trans_file = os.path.join(item, "Translation", "vi", "Text", "_AutoGeneratedTranslations.txt")
                if os.path.exists(trans_file):
                    # Copy về data/translations
                    from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
                    import shutil
                    safe_dest = os.path.join(TRANSLATIONS_DIR, "synced_logs")
                    os.makedirs(safe_dest, exist_ok=True)
                    try:
                        shutil.copy2(trans_file, os.path.join(safe_dest, "_AutoGeneratedTranslations.txt"))
                        logger.info("Successfully synced translation log.")
                    except Exception as e:
                        logger.error(f"Failed to sync log: {e}")

        cleanup_items(self._deployed_items)
        self._deployed_items.clear()
        
        EventBus.publish(SystemEvents.CLEANUP_FINISHED)
        logger.info("Cleanup complete. Game directory is pristine.")
