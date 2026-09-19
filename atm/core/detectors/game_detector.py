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
        base_name = exe_name[:-4] if exe_name.lower().endswith(".exe") else exe_name
        data_dir_name = f"{base_name}_Data"
        data_dir_path = os.path.join(game_dir, data_dir_name)
        
        has_unity_player = os.path.exists(os.path.join(game_dir, "UnityPlayer.dll"))
        has_game_assembly = os.path.exists(os.path.join(game_dir, "GameAssembly.dll"))

        def is_valid_unity_data_dir(path: str) -> bool:
            """Xác minh thư mục _Data có chữ ký đặc trưng của Unity không."""
            if not os.path.isdir(path):
                return False
            unity_signatures = [
                "Managed", "il2cpp_data", "globalgamemanagers",
                "globalgamemanagers.assets", "data.unity3d",
                "boot.config", "resources.assets", "app.info"
            ]
            try:
                for sig in unity_signatures:
                    if os.path.exists(os.path.join(path, sig)):
                        return True
            except Exception:
                pass
            return False

        # 1. Kiểm tra Unity (Hỗ trợ Steam Launcher mismatch mà không gây false-positive)
        unity_data_path = None
        if os.path.exists(data_dir_path) and os.path.isdir(data_dir_path):
            unity_data_path = data_dir_path
        else:
            # Fallback quét tìm thư mục Data của game Steam (loại trừ các thư mục dữ liệu phi-Unity như Save_Data, User_Data)
            ignored_prefixes = ("save", "user", "config", "log", "sound", "voice", "raw")
            try:
                candidates = []
                for item in os.listdir(game_dir):
                    item_lower = item.lower()
                    if item.endswith("_Data") and not any(item_lower.startswith(p) for p in ignored_prefixes):
                        candidate_path = os.path.join(game_dir, item)
                        if os.path.isdir(candidate_path):
                            candidates.append(candidate_path)

                for cand in candidates:
                    if has_unity_player or has_game_assembly or is_valid_unity_data_dir(cand):
                        unity_data_path = cand
                        break
                if not unity_data_path and candidates and (has_unity_player or has_game_assembly):
                    unity_data_path = candidates[0]
            except Exception:
                pass

        # Chỉ phân loại là Unity nếu có anchor (UnityPlayer.dll/GameAssembly.dll) hoặc thư mục data hợp lệ
        is_unity = (
            has_unity_player or
            has_game_assembly or
            (unity_data_path and (unity_data_path == data_dir_path or is_valid_unity_data_dir(unity_data_path)))
        )

        if is_unity:
            il2cpp_path = os.path.join(unity_data_path, "il2cpp_data") if unity_data_path else None
            if (il2cpp_path and os.path.exists(il2cpp_path)) or has_game_assembly:
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
