import json
import os
from typing import Dict, Any, List
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

from atm.utils.paths import get_translations_dir

TRANSLATIONS_DIR = get_translations_dir()

class TranslationRepository:
    """Quản lý Lịch sử Dịch (TXT files) và Metadata."""
    
    def __init__(self) -> None:
        if not os.path.exists(TRANSLATIONS_DIR):
            os.makedirs(TRANSLATIONS_DIR, exist_ok=True)
            
    def get_game_translation_dir(self, game_name: str) -> str:
        safe_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
        game_dir = os.path.join(TRANSLATIONS_DIR, safe_name)
        if not os.path.exists(game_dir):
            os.makedirs(game_dir, exist_ok=True)
            os.makedirs(os.path.join(game_dir, "history"), exist_ok=True)
        return game_dir
        
    def load_metadata(self, game_name: str) -> Dict[str, Any]:
        game_dir = self.get_game_translation_dir(game_name)
        meta_path = os.path.join(game_dir, "metadata.json")
        if not os.path.exists(meta_path):
            return {}
            
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load metadata for {game_name}: {e}")
            return {}
            
    def save_metadata(self, game_name: str, metadata: Dict[str, Any]) -> None:
        game_dir = self.get_game_translation_dir(game_name)
        meta_path = os.path.join(game_dir, "metadata.json")
        
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save metadata for {game_name}: {e}")
            
    def list_history_files(self, game_name: str) -> List[str]:
        game_dir = self.get_game_translation_dir(game_name)
        history_dir = os.path.join(game_dir, "history")
        if not os.path.exists(history_dir):
            return []
        return [f for f in os.listdir(history_dir) if f.endswith(".txt")]
