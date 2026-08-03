import os
import re
import sys
from typing import Callable
from atm.config.schema import GameProfile
from atm.core.translation.translators import GoogleTranslator, DeepLTranslator
from atm.storage.repositories.settings_repository import SettingsRepository
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class RenPyTranslator:
    """Xử lý dịch thuật Offline cho game RenPy."""

    def __init__(self):
        self.settings = SettingsRepository().load()
        
    def _decompile_rpyc(self, game_dir: str, progress_callback: Callable = None):
        """Sử dụng unrpyc để dịch ngược file .rpyc sang .rpy (Nếu chưa có)"""
        unren_dir = os.path.join(os.path.dirname(__file__), "unren_tools")
        if unren_dir not in sys.path:
            sys.path.insert(0, unren_dir)
            
        try:
            import unrpyc
            
            rpyc_files = []
            for root, dirs, files in os.walk(game_dir):
                for f in files:
                    if f.endswith(".rpyc"):
                        rpyc_files.append(os.path.join(root, f))
            
            if progress_callback:
                progress_callback(0, len(rpyc_files), "Đang dịch ngược (Decompile) file .rpyc...")
                
            for idx, f in enumerate(rpyc_files):
                rpy_file = f[:-1] # .rpy
                if not os.path.exists(rpy_file):
                    try:
                        # Gọi module giải mã
                        import decompiler
                        unrpyc.decompile_rpyc(f, decompiler.Decompiler())
                    except Exception as e:
                        logger.error(f"Failed to decompile {f}: {e}")
                
                if progress_callback:
                    progress_callback(idx+1, len(rpyc_files), f"Đã giải mã {os.path.basename(f)}")
                    
        except ImportError as e:
            logger.error(f"Cannot load unrpyc module: {e}")
            if progress_callback:
                progress_callback(1, 1, "Lỗi: Không tìm thấy module giải mã RenPy.")

    def translate_game(self, profile: GameProfile, progress_callback: Callable = None, is_cancelled: Callable = None) -> bool:
        """Dịch file .rpy của RenPy."""
        game_dir = os.path.join(os.path.dirname(profile.exe_path), "game")
        if not os.path.exists(game_dir):
            if progress_callback:
                progress_callback(1, 1, "Lỗi: Không tìm thấy thư mục 'game'.")
            return False

        # 1. Giải mã rpyc -> rpy
        self._decompile_rpyc(game_dir, progress_callback)
        
        # 2. Quét các file .rpy
        rpy_files = []
        for root, dirs, files in os.walk(game_dir):
            for f in files:
                if f.endswith(".rpy") and not f.startswith("options") and not f.startswith("gui"):
                    rpy_files.append(os.path.join(root, f))
                    
        total = len(rpy_files)
        if total == 0:
            if progress_callback:
                progress_callback(1, 1, "Lỗi: Không tìm thấy file kịch bản (.rpy).")
            return False

        translator_id = getattr(profile, "translator", "google")
        if translator_id == "deepl" and self.settings and self.settings.deepl_api_key:
            translator = DeepLTranslator(self.settings.deepl_api_key)
        else:
            translator = GoogleTranslator()

        # Regex tìm chuỗi hội thoại: e.g.  e "Hello World"  hoặc just "Hello World"
        # Bắt các dòng kết thúc bằng chuỗi trong ngoặc kép (trừ dòng code thuần)
        dialogue_pattern = re.compile(r'^(\s*(?:[\w\d]+ )?)"([^"\\]*(?:\\.[^"\\]*)*)"$')
        
        for idx, f in enumerate(rpy_files):
            if is_cancelled and is_cancelled():
                return False

            if progress_callback:
                progress_callback(idx, total, f"Đang dịch {os.path.basename(f)}...")
                
            try:
                with open(f, "r", encoding="utf-8") as file:
                    lines = file.readlines()
                    
                modified = False
                texts_to_translate = []
                line_indices = []
                prefixes = []
                
                # Quét text
                for i, line in enumerate(lines):
                    match = dialogue_pattern.match(line.rstrip('\n\r'))
                    if match:
                        prefix = match.group(1)
                        text = match.group(2)
                        
                        # Bỏ qua nếu text chỉ chứa ký tự đặc biệt hoặc quá ngắn
                        if len(text.strip()) > 1 and not text.startswith("{#") and not re.match(r'^[\W_]+$', text):
                            texts_to_translate.append(text)
                            line_indices.append(i)
                            prefixes.append(prefix)
                            
                # Dịch text theo batch
                if texts_to_translate:
                    batch_size = 50
                    glossary = getattr(profile, "glossary", {})
                    
                    for start in range(0, len(texts_to_translate), batch_size):
                        if is_cancelled and is_cancelled():
                            return False
                            
                        batch = texts_to_translate[start:start+batch_size]
                        
                        # Apply Glossary
                        processed_batch = []
                        for t in batch:
                            pt = t
                            if glossary:
                                for k, v in glossary.items():
                                    pt = pt.replace(k, v)
                            processed_batch.append(pt)
                            
                        res = translator.translate_batch(processed_batch, target_lang=profile.output_lang, source_lang=profile.input_lang)
                        
                        # Cập nhật lại vào lines
                        for i, translated in enumerate(res):
                            idx_in_lines = line_indices[start + i]
                            pref = prefixes[start + i]
                            # Escaping quotes
                            safe_trans = translated.replace('"', '\\"')
                            lines[idx_in_lines] = f'{pref}"{safe_trans}"\n'
                            modified = True
                            
                if modified:
                    with open(f, "w", encoding="utf-8") as file:
                        file.writelines(lines)
            except Exception as e:
                logger.error(f"RenPy Translate Error on {f}: {e}")
                
        if progress_callback:
            progress_callback(total, total, "Dịch RenPy hoàn tất! Bạn có thể chạy game.")
        return True
