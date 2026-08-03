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

    def update_game_settings(self, game_id, input_lang, output_lang, translator):
        """Cập nhật ngôn ngữ và bộ dịch cho game"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}

        profile.input_lang = input_lang
        profile.output_lang = output_lang
        if translator:
            profile.translator = translator
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

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if profile.engine == "RPG Maker":
            # Dịch Offline cho RPG Maker
            self.translation_status[game_id] = {"progress": 0, "total": 100, "message": "Đang chuẩn bị dịch RPG Maker...", "done": False}
            
            def run_offline_translate():
                translator = RPGMakerTranslator()
                
                def progress_cb(current, total, msg):
                    self.translation_status[game_id] = {"progress": current, "total": total, "message": msg, "done": current >= total}
                
                try:
                    success = translator.translate_game(profile, progress_callback=progress_cb)
                    if success:
                        self.translation_status[game_id]["done"] = True
                        self.translation_status[game_id]["message"] = "Dịch xong! Bắt đầu chạy game..."
                        # Chạy game sau khi dịch xong
                        deployer = GameDeployer()
                        self.active_deployers[game_id] = deployer
                        deployer.deploy_and_launch(profile, None) # Không cần payload dir cho RPG Maker
                    else:
                        self.translation_status[game_id] = {"progress": 0, "total": 1, "message": "Lỗi: Không tìm thấy data game.", "done": True, "error": True}
                except Exception as e:
                    logger.error(f"RPG Maker translate error: {e}")
                    self.translation_status[game_id] = {"progress": 0, "total": 1, "message": f"Lỗi: {e}", "done": True, "error": True}

            t = threading.Thread(target=run_offline_translate, daemon=True)
            t.start()
            return {"status": "translating"}
            
        if profile.engine == "RenPy":
            return {
                "status": "error",
                "error": "Engine RenPy đang được phát triển bộ dịch Offline. Vui lòng chờ bản cập nhật sau!"
            }
            
        if profile.engine == "Unity Mono":
            payload_dir = os.path.join(base_dir, "data", "payloads", "bepinex_mono")
            engine_req = "Unity Mono"
        elif profile.engine == "Unity IL2CPP":
            payload_dir = os.path.join(base_dir, "data", "payloads", "bepinex_il2cpp")
            engine_req = "Unity IL2CPP"
        else:
            return {
                "status": "error",
                "error": f"Engine {profile.engine} chưa được hỗ trợ auto-deploy."
            }

        if not os.path.exists(payload_dir) or len(os.listdir(payload_dir)) == 0:
            os.makedirs(payload_dir, exist_ok=True)
            return {
                "status": "error",
                "error": f"Thiếu Payload BepInEx cho {engine_req}!\nLỗi hệ thống: Thư mục payload trống."
            }

        deployer = GameDeployer()
        self.active_deployers[game_id] = deployer

        # Chạy deploy trên thread riêng để không block UI
        def run_deploy():
            try:
                deployer.deploy_and_launch(profile, payload_dir)
            except Exception as e:
                logger.error(f"Deploy error: {e}")

        t = threading.Thread(target=run_deploy, daemon=True)
        t.start()
        return {"status": "success"}

    def get_translation_status(self, game_id):
        """Trả về tiến độ dịch offline"""
        status = self.translation_status.get(game_id, {"progress": 0, "total": 0, "message": "", "done": True})
        return status

    def stop_game(self, game_id):
        """Dừng game đang chạy"""
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
