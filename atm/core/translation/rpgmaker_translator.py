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

    def translate_game(self, profile: GameProfile, progress_callback: Callable[[int, int, str], None] = None, is_cancelled: Callable[[], bool] = None) -> bool:
        """
        Dịch toàn bộ file JSON trong thư mục data của RPG Maker.
        """
        game_dir = os.path.dirname(profile.exe_path)
        
        # MV thường có `www/data`, MZ thường có `data` ở ngay thư mục gốc
        if os.path.exists(os.path.join(game_dir, "www", "data")):
            data_dir = os.path.join(game_dir, "www", "data")
            backup_dir = os.path.join(game_dir, "www", "data_backup")
        elif os.path.exists(os.path.join(game_dir, "data")):
            data_dir = os.path.join(game_dir, "data")
            backup_dir = os.path.join(game_dir, "data_backup")
        else:
            logger.error(f"Cannot find data folder in {game_dir} or {game_dir}/www")
            return False
            
        # Tạo backup nếu chưa có
        if not os.path.exists(backup_dir):
            logger.info("Creating backup for RPG Maker data...")
            shutil.copytree(data_dir, backup_dir)
            
        json_files = [f for f in os.listdir(backup_dir) if f.endswith(".json")]
        
        translator_id = getattr(profile, "translator", "google")
        if translator_id == "deepl" and self.settings and self.settings.deepl_api_key:
            translator = DeepLTranslator(self.settings.deepl_api_key)
        else:
            translator = GoogleTranslator()
            
        # Pass 1: Quét toàn bộ để lấy tổng số câu
        file_datas = []
        total_batches = 0
        batch_size = 50
        
        if progress_callback:
            progress_callback(0, 100, "Đang quét dữ liệu game...")
            
        for filename in json_files:
            source_file_path = os.path.join(backup_dir, filename)
            try:
                with open(source_file_path, "r", encoding="utf-8-sig") as f:
                    content = f.read()
                    if not content:
                        continue
                    data = json.loads(content)
                texts = self._extract_texts_from_json(data)
                unique_texts = list(set(texts))
                if unique_texts:
                    file_datas.append({
                        "filename": filename,
                        "data": data,
                        "unique_texts": unique_texts
                    })
                    total_batches += (len(unique_texts) + batch_size - 1) // batch_size
            except Exception as e:
                logger.error(f"Error scanning {filename}: {e}")
                
        # Pass 2: Dịch thực tế và update progress theo batch
        current_batch = 0
        
        for file_info in file_datas:
            if is_cancelled and is_cancelled():
                logger.info("Translation cancelled by user.")
                return False

            filename = file_info["filename"]
            data = file_info["data"]
            unique_texts = file_info["unique_texts"]
            dest_file_path = os.path.join(data_dir, filename)
            
            translated_texts = []
            
            for i in range(0, len(unique_texts), batch_size):
                if is_cancelled and is_cancelled():
                    logger.info("Translation cancelled by user midway during batch.")
                    return False
                    
                if progress_callback:
                    percent = int((current_batch / max(1, total_batches)) * 100)
                    progress_callback(percent, 100, f"Đang dịch {filename} ({percent}%)")
                    
                batch = unique_texts[i:i+batch_size]
                
                # Apply Custom Glossary (Từ điển cá nhân)
                processed_batch = []
                glossary = getattr(profile, "glossary", {})
                for text in batch:
                    processed_text = text
                    if glossary:
                        for k, v in glossary.items():
                            processed_text = processed_text.replace(k, v)
                    processed_batch.append(processed_text)
                    
                res = translator.translate_batch(processed_batch, target_lang=profile.output_lang, source_lang=profile.input_lang)
                translated_texts.extend(res)
                
                current_batch += 1
                
            translated_map = dict(zip(unique_texts, translated_texts))
            
            # Thay thế text
            new_data = self._replace_texts_in_json(data, translated_map)
            
            # Ghi đè lại file
            try:
                with open(dest_file_path, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Failed to write translated {filename}: {e}")
                
        if progress_callback:
            progress_callback(100, 100, "Hoàn tất dịch!")
            
        return True
