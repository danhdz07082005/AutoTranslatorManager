import os
import json
from typing import Dict
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class GameDetector:
    """Xác định cấu trúc của game để chọn Payload (BepInEx) phù hợp."""
    
    @staticmethod
    def detect_engine(exe_path: str) -> str:
        if not os.path.exists(exe_path):
            return "Unknown"
            
        game_dir = os.path.dirname(exe_path)
        exe_name = os.path.basename(exe_path)
        data_dir_name = exe_name.replace(".exe", "_Data")
        data_dir_path = os.path.join(game_dir, data_dir_name)
        
        # 1. Kiểm tra Unity
        if os.path.exists(data_dir_path):
            il2cpp_path = os.path.join(data_dir_path, "il2cpp_data")
            if os.path.exists(il2cpp_path) or os.path.exists(os.path.join(game_dir, "GameAssembly.dll")):
                logger.info(f"Detected Unity IL2CPP game: {exe_name}")
                return "Unity IL2CPP"
            else:
                logger.info(f"Detected Unity Mono game: {exe_name}")
                return "Unity Mono"
                
        # 2. Kiểm tra RenPy (Case insensitive check)
        if os.path.exists(os.path.join(game_dir, "renpy")):
            logger.info(f"Detected RenPy game: {exe_name}")
            return "RenPy"
            
        game_folder = os.path.join(game_dir, "game")
        if os.path.isdir(game_folder):
            try:
                for f in os.listdir(game_folder):
                    fl = f.lower()
                    if fl.endswith('.rpa') or fl.endswith('.rpyc'):
                        logger.info(f"Detected RenPy game: {exe_name}")
                        return "RenPy"
            except Exception:
                pass
            
        # 3. Kiểm tra RPG Maker MV/MZ
        # Robust check: either www/data exists, or data/System.json exists, or package.json exists.
        if os.path.exists(os.path.join(game_dir, "www", "data")):
            logger.info(f"Detected RPG Maker game: {exe_name}")
            return "RPG Maker"
            
        if os.path.exists(os.path.join(game_dir, "data", "System.json")):
            logger.info(f"Detected RPG Maker game: {exe_name}")
            return "RPG Maker"
            
        if os.path.exists(os.path.join(game_dir, "package.json")):
            logger.info(f"Detected RPG Maker game (via package.json): {exe_name}")
            return "RPG Maker"
            
        # 4. Kiểm tra RPG Developer Bakin
        if (os.path.exists(os.path.join(game_dir, "data", "data.rbpack")) or
            os.path.exists(os.path.join(game_dir, "bakinplayer.exe")) or
            os.path.exists(os.path.join(game_dir, "bakinengine.dll"))):
            logger.info(f"Detected RPG Developer Bakin game: {exe_name}")
            return "Bakin"
            
        return "Unknown"
