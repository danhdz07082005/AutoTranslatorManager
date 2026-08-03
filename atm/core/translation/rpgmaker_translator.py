import os
import json
import shutil
from typing import List, Dict, Any, Callable
from atm.config.schema import GameProfile
from atm.core.translation.translators import GoogleTranslator, DeepLTranslator
from atm.storage.repositories.settings_repository import SettingsRepository
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class RPGMakerTranslator:
    """Xử lý dịch thuật Offline cho RPG Maker MV/MZ."""
    
    def __init__(self):
        self.settings = SettingsRepository().load()
        
    def _extract_texts_from_json(self, data: Any) -> List[str]:
        """Đệ quy lấy tất cả text từ file JSON của RPG Maker."""
        texts = []
        if isinstance(data, dict):
            # Các code phổ biến trong RPG Maker: 
            # 401: Show Text, 102: Show Choices
            if "code" in data and data["code"] in [401, 102] and "parameters" in data:
                for param in data["parameters"]:
                    if isinstance(param, str) and param.strip():
                        texts.append(param)
                    elif isinstance(param, list):
                        for p in param:
                            if isinstance(p, str) and p.strip():
                                texts.append(p)
            for key, value in data.items():
                texts.extend(self._extract_texts_from_json(value))
        elif isinstance(data, list):
            for item in data:
                texts.extend(self._extract_texts_from_json(item))
        return texts

    def _replace_texts_in_json(self, data: Any, translated_map: Dict[str, str]) -> Any:
        """Đệ quy thay thế text đã dịch vào file JSON."""
        if isinstance(data, dict):
            if "code" in data and data["code"] in [401, 102] and "parameters" in data:
                new_params = []
                for param in data["parameters"]:
                    if isinstance(param, str) and param.strip() in translated_map:
                        new_params.append(translated_map[param.strip()])
                    elif isinstance(param, list):
                        new_list = []
                        for p in param:
                            if isinstance(p, str) and p.strip() in translated_map:
                                new_list.append(translated_map[p.strip()])
                            else:
                                new_list.append(p)
                        new_params.append(new_list)
                    else:
                        new_params.append(param)
                data["parameters"] = new_params
                
            for key, value in data.items():
                data[key] = self._replace_texts_in_json(value, translated_map)
        elif isinstance(data, list):
            for i in range(len(data)):
                data[i] = self._replace_texts_in_json(data[i], translated_map)
        return data

    def translate_game(self, profile: GameProfile, progress_callback: Callable[[int, int, str], None] = None) -> bool:
        """
        Dịch toàn bộ file JSON trong thư mục www/data.
        """
        game_dir = os.path.dirname(profile.exe_path)
        data_dir = os.path.join(game_dir, "www", "data")
        backup_dir = os.path.join(game_dir, "www", "data_backup")
        
        if not os.path.exists(data_dir):
            logger.error(f"Cannot find www/data in {game_dir}")
            return False
            
        # Tạo backup nếu chưa có
        if not os.path.exists(backup_dir):
            logger.info("Creating backup for RPG Maker data...")
            shutil.copytree(data_dir, backup_dir)
            
        json_files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
        total_files = len(json_files)
        
        translator_id = getattr(profile, "translator", "google")
        if translator_id == "deepl" and self.settings and self.settings.deepl_api_key:
            translator = DeepLTranslator(self.settings.deepl_api_key)
        else:
            translator = GoogleTranslator()
        
        for idx, filename in enumerate(json_files):
            file_path = os.path.join(data_dir, filename)
            if progress_callback:
                progress_callback(idx, total_files, f"Đang dịch {filename}...")
                
            try:
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    content = f.read()
                    if not content:
                        continue
                    data = json.loads(content)
                    
                # Trích xuất text
                texts = self._extract_texts_from_json(data)
                # Loại bỏ trùng lặp
                unique_texts = list(set(texts))
                
                if unique_texts:
                    # Dịch batch
                    # Hạn chế số lượng mỗi batch (VD: 50 câu / 1 lần gọi API)
                    batch_size = 50
                    translated_texts = []
                    for i in range(0, len(unique_texts), batch_size):
                        batch = unique_texts[i:i+batch_size]
                        res = translator.translate_batch(batch, target_lang=profile.output_lang, source_lang=profile.input_lang)
                        translated_texts.extend(res)
                        
                    translated_map = dict(zip(unique_texts, translated_texts))
                    
                    # Thay thế text
                    new_data = self._replace_texts_in_json(data, translated_map)
                    
                    # Ghi đè lại file
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(new_data, f, ensure_ascii=False)
                        
            except Exception as e:
                logger.error(f"Failed to translate {filename}: {e}")
                
        if progress_callback:
            progress_callback(total_files, total_files, "Hoàn tất dịch!")
            
        return True
