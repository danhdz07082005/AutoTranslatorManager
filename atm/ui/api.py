import os
import uuid
import threading
import webview
from atm.storage.repositories.profile_repository import ProfileRepository
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
        self.window = None
        self.active_deployers = {}  # game_id -> deployer

    def set_window(self, window):
        self.window = window

    def get_languages(self):
        """Trả về danh sách ngôn ngữ cho dropdown"""
        return SUPPORTED_LANGUAGES

    def get_games(self):
        """Trả về danh sách game profile cho JS"""
        profiles = self.profile_repo.get_all()
        return [p.model_dump() for p in profiles]

    def add_game(self):
        """Mở hộp thoại file bằng pywebview native, tạo profile và trả kết quả"""
        if not self.window:
            return {"error": "Window not initialized"}

        try:
            file_types = ('Executable Files (*.exe)', 'All files (*.*)')
            result = self.window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=file_types
            )
        except Exception:
            # Fallback nếu OPEN_DIALOG bị deprecated
            try:
                result = self.window.create_file_dialog(
                    dialog_type=webview.OPEN_DIALOG,
                    allow_multiple=False,
                    file_types=('Executable Files (*.exe)', 'All files (*.*)')
                )
            except Exception as e:
                logger.error(f"File dialog error: {e}")
                return {"error": str(e)}

        if result and len(result) > 0:
            file_path = result[0]
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

    def update_game_lang(self, game_id, input_lang, output_lang):
        """Cập nhật ngôn ngữ input/output cho game"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}

        profile.input_lang = input_lang
        profile.output_lang = output_lang
        self.profile_repo.save(profile)
        logger.info(f"Updated languages for {profile.game_name}: {input_lang} -> {output_lang}")
        return {"status": "success"}

    def start_game(self, game_id):
        """Khởi chạy game với bộ dịch"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game profile not found"}

        from atm.core.deployment.game_deployer import GameDeployer

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        payload_dir = os.path.join(base_dir, "data", "payloads", "bepinex")

        if not os.path.exists(payload_dir):
            return {
                "status": "error",
                "error": f"Chưa có Payload (BepInEx). Tạo thư mục: {payload_dir}"
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
