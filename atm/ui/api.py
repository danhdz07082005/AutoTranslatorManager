import os
import uuid
import threading
import webview
from atm.storage.repositories.profile_repository import ProfileRepository
from atm.storage.repositories.settings_repository import SettingsRepository
from atm.config.schema import GameProfile
from atm.core.detectors.game_detector import GameDetector
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

# Danh sách ngôn ngữ hỗ trợ
SUPPORTED_LANGUAGES = {
    "auto": "Auto Detect",
    "ja": "Japanese",
    "en": "English",
    "zh": "Chinese (Simplified)",
    "zh-TW": "Chinese (Traditional)",
    "ko": "Korean",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
    "hi": "Hindi",
}


class BackendApi:
    def __init__(self):
        self.profile_repo = ProfileRepository()
        self.settings_repo = SettingsRepository()
        self.window = None
        self.active_deployers = {}  # game_id -> deployer
        self.translation_status = {}  # game_id -> {"progress": int, "total": int, "message": str, "done": bool}
        self.cancel_flags = {}  # game_id -> bool
        self._lock = threading.Lock()

    def set_window(self, window):
        self.window = window

    def get_languages(self):
        """Trả về danh sách ngôn ngữ cho dropdown"""
        return SUPPORTED_LANGUAGES

    def get_settings(self):
        """Trả về cấu hình hiện tại"""
        settings = self.settings_repo.load()
        return settings.model_dump()

    def update_settings(self, dark_mode, deepl_api_key):
        """Cập nhật cấu hình"""
        settings = self.settings_repo.load()
        settings.dark_mode = dark_mode
        settings.deepl_api_key = deepl_api_key
        self.settings_repo.save(settings)
        return {"status": "success"}

    def get_games(self):
        """Trả về danh sách game profile cho JS"""
        profiles = self.profile_repo.get_all()
        return [p.model_dump() for p in profiles]

    def add_game(self):
        """Mở hộp thoại file bằng tkinter, tạo profile và trả kết quả"""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            file_path = filedialog.askopenfilename(
                title="Chọn file chạy của game (.exe)",
                filetypes=[("Executable Files", "*.exe"), ("All files", "*.*")]
            )
            root.destroy()
        except Exception as e:
            logger.error(f"File dialog error: {e}")
            return {"error": str(e)}

        if file_path:
            game_name = os.path.basename(os.path.dirname(file_path))
            if not game_name:
                game_name = os.path.splitext(os.path.basename(file_path))[0]

            engine = GameDetector.detect_engine(file_path)

            profile = GameProfile(
                id=str(uuid.uuid4()),
                game_name=game_name,
                exe_path=file_path,
                engine=engine,
                translator="google",
                input_lang="auto",
                output_lang="vi"
            )

            self.profile_repo.save(profile)
            logger.info(f"Added game profile: {profile.game_name} [{profile.id}]")
            return {"status": "success", "game": profile.model_dump()}

        return None  # User cancelled

    def update_game_settings(self, game_id, input_lang=None, output_lang=None, translator=None, glossary=None):
        """Cập nhật ngôn ngữ, bộ dịch, và từ điển cá nhân cho game"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}

        if input_lang is not None:
            profile.input_lang = input_lang
        if output_lang is not None:
            profile.output_lang = output_lang
        if translator is not None:
            profile.translator = translator
        if glossary is not None:
            profile.glossary = glossary
        self.profile_repo.save(profile)
        logger.info(f"Updated settings for {profile.game_name}: {input_lang} -> {output_lang}, engine: {translator}")
        return {"status": "success"}

    def start_game(self, game_id):
        """Khởi chạy game với bộ dịch"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game profile not found"}

        from atm.core.deployment.game_deployer import GameDeployer
        from atm.core.translation import RPGMakerTranslator
        from atm.core.translation.renpy_translator import RenPyTranslator

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if profile.engine == "RPG Maker":
            # Dịch Offline
            self.translation_status[game_id] = {"progress": 0, "total": 100, "message": f"Đang chuẩn bị dịch {profile.engine}...", "done": False}
            self.cancel_flags[game_id] = False
            
            def run_offline_translate():
                if profile.engine == "RPG Maker":
                    translator = RPGMakerTranslator()
                else:
                    translator = RenPyTranslator()
                
                def progress_cb(current, total, msg):
                    self.translation_status[game_id] = {"progress": current, "total": total, "message": msg, "done": current >= total}
                
                def is_cancelled():
                    return self.cancel_flags.get(game_id, False)

                try:
                    success = translator.translate_game(profile, progress_callback=progress_cb, is_cancelled=is_cancelled)
                    if self.cancel_flags.get(game_id, False):
                        self.translation_status[game_id] = {"progress": 0, "total": 1, "message": "Đã huỷ dịch ngang chừng.", "done": True, "error": True}
                        return

                    if success:
                        self.translation_status[game_id]["done"] = True
                        self.translation_status[game_id]["message"] = "Dịch xong! Bắt đầu chạy game..."
                        # Chạy game sau khi dịch xong
                        deployer = GameDeployer()
                        self.active_deployers[game_id] = deployer
                        deployer.deploy_and_launch(profile, None)
                    else:
                        self.translation_status[game_id] = {"progress": 0, "total": 1, "message": "Lỗi: Quá trình dịch thất bại.", "done": True, "error": True}
                except Exception as e:
                    logger.error(f"{profile.engine} translate error: {e}")
                    self.translation_status[game_id] = {"progress": 0, "total": 1, "message": f"Lỗi: {e}", "done": True, "error": True}

            t = threading.Thread(target=run_offline_translate, daemon=True)
            t.start()
            return {"status": "translating"}
            
        if profile.engine == "Unity Mono":
            payload_dir = os.path.join(base_dir, "data", "payloads", "bepinex_mono")
            engine_req = "Unity Mono"
        elif profile.engine == "Unity IL2CPP":
            payload_dir = os.path.join(base_dir, "data", "payloads", "bepinex_il2cpp")
            engine_req = "Unity IL2CPP"
        elif profile.engine == "RenPy":
            payload_dir = os.path.join(base_dir, "data", "payloads", "renpy_realtime")
            engine_req = "RenPy"
        else:
            return {"status": "error", "error": f"Engine {profile.engine} is not supported for real-time launch."}

        # Khởi tạo Deployer
        deployer = GameDeployer()
        self.active_deployers[game_id] = deployer
        
        # Deploy và Launch (chạy background)
        t = threading.Thread(target=deployer.deploy_and_launch, args=(profile, payload_dir), daemon=True)
        t.start()
        return {"status": "success"}

    def get_translation_status(self, game_id):
        """Trả về tiến độ dịch offline"""
        status = self.translation_status.get(game_id, {"progress": 0, "total": 0, "message": "", "done": True})
        return status

    def stop_game(self, game_id):
        """Dừng game đang chạy hoặc dừng tiến trình dịch"""
        # Nếu đang dịch, báo cờ cancel
        if game_id in self.translation_status and not self.translation_status[game_id].get("done"):
            self.cancel_flags[game_id] = True
            logger.info(f"Cancelled translation for: {game_id}")
            return {"status": "success"}

        if game_id in self.active_deployers:
            deployer = self.active_deployers[game_id]
            deployer.monitor.stop()
            del self.active_deployers[game_id]
            logger.info(f"Stopped game: {game_id}")
        return {"status": "success"}

    def delete_game(self, game_id):
        """Xóa game profile (cả file JSON)"""
        try:
            # Xóa bằng ID (tên file mới)
            deleted = self.profile_repo.delete(game_id)

            # Dọn cả file profile cũ (tên theo game_name) nếu còn sót
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            profiles_dir = os.path.join(base_dir, "data", "profiles")
            if os.path.isdir(profiles_dir):
                for f in os.listdir(profiles_dir):
                    if f.endswith(".json"):
                        fpath = os.path.join(profiles_dir, f)
                        try:
                            import json
                            with open(fpath, "r", encoding="utf-8") as fp:
                                data = json.load(fp)
                            if data.get("id") == game_id:
                                os.remove(fpath)
                                logger.info(f"Cleaned old profile file: {f}")
                        except Exception:
                            pass

            logger.info(f"Deleted game: {game_id}")
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return {"status": "error", "error": str(e)}

    def get_cache_entries(self):
        """Lấy danh sách cache để hiển thị lên Grid Editor"""
        from atm.core.translation.cache_manager import TranslationCache
        cache = TranslationCache()
        data = {}
        for src_lang, target_dict in cache.cache.items():
            for tgt_lang, texts in target_dict.items():
                for original, translated in texts.items():
                    data[original] = translated
        return {"status": "success", "data": data}

    def update_cache_entry(self, game_id, key, value):
        """Cập nhật một mục trong Cache từ Grid Editor"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile: 
            return {"status": "error", "error": "Game not found"}
            
        source_lang = profile.input_lang
        target_lang = profile.output_lang
        if source_lang == "auto":
            # Nếu là auto, trong cache_manager nó vẫn lưu theo key "auto" hoặc tuỳ translator
            # Tạm thời lưu chung cho auto
            pass
            
        from atm.core.translation.cache_manager import TranslationCache
        cache = TranslationCache()
        cache.set(source_lang, target_lang, key, value)
        cache.save_to_disk()
        logger.info(f"Updated cache manually: {key} -> {value}")
        return {"status": "success"}
