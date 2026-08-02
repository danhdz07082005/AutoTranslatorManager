import json
import os
from pydantic import ValidationError
from atm.config.schema import AppSettings
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "config.json")

class SettingsRepository:
    """Quản lý việc lưu trữ và nạp cấu hình Launcher an toàn."""
    
    def load(self) -> AppSettings:
        if not os.path.exists(CONFIG_PATH):
            logger.info("Config file not found. Creating default settings.")
            return self._create_default()
            
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppSettings(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Config is corrupted: {e}. Recovering default settings.")
            self._backup_corrupted_config()
            return self._create_default()

    def save(self, settings: AppSettings) -> None:
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(settings.model_dump_json(indent=4))
            logger.info("Settings saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def _create_default(self) -> AppSettings:
        default_settings = AppSettings()
        self.save(default_settings)
        return default_settings

    def _backup_corrupted_config(self) -> None:
        if os.path.exists(CONFIG_PATH):
            backup_path = CONFIG_PATH + ".bak"
            os.replace(CONFIG_PATH, backup_path)
            logger.info(f"Corrupted config backed up to {backup_path}")
