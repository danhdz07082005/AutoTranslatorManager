import os
from typing import Optional
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class GameDetector:
    """Xác định cấu trúc của game để chọn Payload (BepInEx) phù hợp."""
    
    @staticmethod
    def detect_engine(exe_path: str) -> str:
        """
        Phân tích thư mục game để nhận diện Engine (Unity Mono, Unity IL2CPP, RenPy).
        """
        if not os.path.exists(exe_path):
            return "Unknown"
            
        game_dir = os.path.dirname(exe_path)
        exe_name = os.path.basename(exe_path)
        data_dir_name = exe_name.replace(".exe", "_Data")
        data_dir_path = os.path.join(game_dir, data_dir_name)
        
        if os.path.exists(data_dir_path):
            # Là game Unity
            il2cpp_path = os.path.join(data_dir_path, "il2cpp_data")
            if os.path.exists(il2cpp_path) or os.path.exists(os.path.join(game_dir, "GameAssembly.dll")):
                logger.info(f"Detected Unity IL2CPP game: {exe_name}")
                return "Unity IL2CPP"
            else:
                logger.info(f"Detected Unity Mono game: {exe_name}")
                return "Unity Mono"
                
        # Kiểm tra RenPy (thường có folder 'renpy' hoặc 'game')
        if os.path.exists(os.path.join(game_dir, "renpy")) or os.path.exists(os.path.join(game_dir, "game", "script.rpyc")) or os.path.exists(os.path.join(game_dir, "game", "archive.rpa")):
            logger.info(f"Detected RenPy game: {exe_name}")
            return "RenPy"
            
        # Kiểm tra RPG Maker MV/MZ
        if os.path.exists(os.path.join(game_dir, "www", "data")) or os.path.exists(os.path.join(game_dir, "package.json")):
            logger.info(f"Detected RPG Maker game: {exe_name}")
            return "RPG Maker"
            
        return "Unknown"
