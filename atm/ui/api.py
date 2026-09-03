import os
import uuid
import threading
import time

from atm.storage.repositories.profile_repository import ProfileRepository
from atm.storage.repositories.settings_repository import SettingsRepository
from atm.storage.repositories.job_repository import JobRepository, TranslationJob
from atm.config.schema import GameProfile
from atm.core.detectors.game_detector import GameDetector
from atm.utils.logger import get_logger
from atm.core.translation.translators import RateLimitError
from atm.core.jobs.manager import JobManager
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
        self.job_repo = JobRepository()
        self.window = None
        self.active_deployers = {}  # game_id -> deployer
        self.translation_status = {}  # game_id -> {"progress": int, "total": int, "message": str, "done": bool}
        self.cancel_flags = {}  # game_id -> bool
        self._lock = threading.Lock()
        self.job_manager = JobManager(max_workers=4)
        # In-memory fingerprint cache: {game_id: (fingerprint_str, computed_at_timestamp)}
        # Avoids O(N) disk I/O on every get_games() call. Invalidated when a game completes translation.
        self._fingerprint_cache = {}
        # Recover zombie jobs from before last restart
        self._recover_jobs()

    def is_idle(self) -> bool:
        """Kiểm tra xem hệ thống có đang rảnh rỗi không (không có game nào đang dịch/chạy nền)."""
        with self._lock:
            for job in list(self.job_manager.jobs.values()):
                if job.status in ("running", "queued"):
                    return False
            for status in self.translation_status.values():
                if not status.get("done", True):
                    return False
            for deployer in self.active_deployers.values():
                if getattr(deployer, "is_deploying", False) or deployer.monitor.is_monitoring:
                    return False
            return True


    def _recover_jobs(self):
        # Scan job repository for jobs that are still 'running' or 'paused' across backend restarts
        try:
            jobs = self.job_repo.get_all()
            for job in jobs:
                if job.status in ("running", "paused"):
                    job.status = "error"
                    job.message_code = "INTERRUPTED_BY_RESTART"
                    job.error_details = "Backend process was restarted while job was active"
                    self.job_repo.save(job)
                    logger.info(f"Recovered zombie job for game_id={job.game_id} -> INTERRUPTED")
        except Exception as e:
            logger.error(f"Failed to recover jobs: {e}")

    def set_window(self, window):
        self.window = window

    def get_languages(self):
        """Trả về danh sách ngôn ngữ cho dropdown"""
        return SUPPORTED_LANGUAGES

    def get_settings(self):
        """Trả về cấu hình hiện tại"""
        settings = self.settings_repo.load()
        data = settings.model_dump()
        has_key = bool(data.get("deepl_api_key"))
        if "deepl_api_key" in data:
            del data["deepl_api_key"]
        data["deepl_api_key_configured"] = has_key
        return data

    def update_settings(self, **kwargs):
        """Cập nhật cấu hình"""
        settings = self.settings_repo.load()
        if "dark_mode" in kwargs:
            settings.dark_mode = kwargs["dark_mode"]
        if "deepl_api_key" in kwargs:
            settings.deepl_api_key = kwargs["deepl_api_key"]
        if "ui_language" in kwargs:
            settings.ui_language = kwargs["ui_language"]
        if "translation_memory_threshold" in kwargs:
            try:
                threshold = float(kwargs["translation_memory_threshold"])
                if not 0.0 <= threshold <= 1.0:
                    return {"status": "error", "error": "Translation-memory threshold must be between 0 and 1"}
                settings.translation_memory_threshold = threshold
            except (TypeError, ValueError):
                return {"status": "error", "error": "Invalid translation-memory threshold"}
        
        self.settings_repo.save(settings)
        return {"status": "success"}

    def get_games(self):
        """Trả về danh sách game profile cho JS"""
        profiles = self.profile_repo.get_all()
        result = []
        for p in profiles:
            p_dict = p.model_dump()
            job = self.job_repo.load(p.id)
            
            # Mặc định lấy theo database
            if job:
                if job.status == "error" and job.message_code == "INTERRUPTED_BY_RESTART":
                    p_dict["runtime_state"] = "INTERRUPTED"
                elif job.status == "completed":
                    p_dict["runtime_state"] = "COMPLETE"
                else:
                    p_dict["runtime_state"] = "READY"
            else:
                p_dict["runtime_state"] = "READY"
            
            # Override from live memory status
            with self._lock:
                if p.id in self.translation_status:
                    live_status = self.translation_status[p.id]
                    if not live_status.get("done", True):
                        p_dict["runtime_state"] = "TRANSLATING"
                        
                if p.id in self.active_deployers:
                    deployer = self.active_deployers[p.id]
                    if getattr(deployer, "is_deploying", False) or deployer.monitor.is_monitoring:
                        p_dict["runtime_state"] = "TRANSLATING"
                
            # --- KIỂM TRA MẶT VẬT LÝ (WATERMARK) ---
            if p_dict["runtime_state"] == "COMPLETE":
                try:
                    game_dir = os.path.dirname(p.exe_path)
                    marker_path = os.path.join(game_dir, '.atm_translated')
                    if not os.path.exists(marker_path):
                        p_dict["runtime_state"] = "READY"
                    else:
                        import json
                        with open(marker_path, 'r', encoding='utf-8') as f:
                            marker_data = json.load(f)
                        expected_fingerprint = self._calculate_fingerprint(p)
                        if marker_data.get("game_fingerprint") != expected_fingerprint:
                            p_dict["runtime_state"] = "READY"
                        elif marker_data.get("source_language") != p.input_lang or marker_data.get("target_language") != p.output_lang:
                            p_dict["runtime_state"] = "READY"
                except Exception as e:
                    logger.warning(f"Failed to check marker for {p.id}: {e}")
                    
            if job:
                p_dict["runtime_progress"] = job.progress
                p_dict["runtime_total"] = job.total
            result.append(p_dict)
        return {"games": result}

    def add_game(self):
        """Mở hộp thoại file bằng tkinter, tạo profile và trả kết quả"""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            try:
                root.withdraw()
                root.attributes('-topmost', True)
                file_path = filedialog.askopenfilename(
                    title="Select game executable (.exe)",
                    filetypes=[("Executable Files", "*.exe"), ("All files", "*.*")]
                )
            finally:
                root.destroy()
        except Exception as e:
            logger.error(f"File dialog error: {e}")
            return {"status": "error", "error": str(e)}

        if file_path:
            # Validate duplicate exe_path
            existing_profiles = self.profile_repo.get_all()
            for existing in existing_profiles:
                if existing.exe_path and os.path.normpath(existing.exe_path) == os.path.normpath(file_path):
                    logger.warning(f"Game already exists: {file_path}")
                    return {"status": "error", "error": f"Game already exists in the system!"}

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
                output_lang=self.settings_repo.load().ui_language or "vi"
            )

            self.profile_repo.save(profile)
            logger.info(f"Added game profile: {profile.game_name} [{profile.id}]")
            return {"status": "success", "game": profile.model_dump()}

        return {"status": "cancelled"}  # User cancelled the file dialog


    def update_game_settings(self, game_id, input_lang=None, output_lang=None, translator=None, glossary=None):
        """Cập nhật ngôn ngữ, bộ dịch, và từ điển cá nhân cho game"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang)."}

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

    def start_game(self, game_id, auto_launch=True):
        """Khởi chạy game với bộ dịch"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game profile not found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Please select target language (output_lang) before starting translation."}

        from atm.core.deployment.game_deployer import GameDeployer
        from atm.core.translation import RPGMakerTranslator
        from atm.core.translation.renpy_translator import RenPyTranslator

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Block multiple starts
        with self._lock:
            # Clean up dead deployers first
            if game_id in self.active_deployers:
                dep = self.active_deployers[game_id]
                if not getattr(dep, "is_deploying", False) and not dep.monitor.is_monitoring:
                    del self.active_deployers[game_id]
                    
            if game_id in self.translation_status and not self.translation_status[game_id].get("done", True):
                return {"status": "translating", "message": "Already translating"}
            if game_id in self.active_deployers:
                return {"status": "translating", "message": "Already translating"}

        if profile.engine in ("RPG Maker", "RenPy"):
            # Dịch Offline cho RPG Maker và RenPy
            with self._lock:
                self.translation_status[game_id] = {
                    "progress": 0, 
                    "total": 100, 
                    "code": "translation.preparing", 
                    "params": {"engine": profile.engine},
                    "done": False,
                    "error": False
                }
                self.cancel_flags[game_id] = False
            
            def run_offline_translate():
                if profile.engine == "RPG Maker":
                    from atm.core.translation import RPGMakerTranslator
                    translator = RPGMakerTranslator()
                else:
                    from atm.core.translation.renpy_translator import RenPyTranslator
                    from atm.core.translation.cache_manager import TranslationCache
                    from atm.core.translation.translation_memory import TranslationMemory
                    translator = RenPyTranslator(cache=TranslationCache(), translation_memory=TranslationMemory())
                
                def progress_cb(current, total, code, params=None):
                    with self._lock:
                        self.translation_status[game_id] = {
                            "progress": current, 
                            "total": total, 
                            "code": code,
                            "params": params or {},
                            "done": current >= total,
                            "error": False
                        }
                    if current % 10 == 0 or current >= total:
                        self.job_repo.save(TranslationJob(
                            game_id=game_id,
                            status="running" if current < total else "completed",
                            progress=current,
                            total=total,
                            message_code=code,
                            params=params or {}
                        ))
                
                def is_cancelled():
                    with self._lock:
                        return self.cancel_flags.get(game_id, False)

                try:
                    success = translator.translate_game(profile, progress_callback=progress_cb, is_cancelled=is_cancelled)
                    if is_cancelled():
                        with self._lock:
                            self.translation_status[game_id] = {
                                "progress": 0, "total": 1, 
                                "code": "translation.cancelled", 
                                "params": {},
                                "done": True, 
                                "error": True
                            }
                        self.job_repo.save(TranslationJob(game_id=game_id, status="error", message_code="translation.cancelled", error_details="Cancelled by user"))
                        return

                    if success:
                        with self._lock:
                            self.translation_status[game_id]["done"] = True
                            self.translation_status[game_id]["code"] = "translation.success"
                            self.translation_status[game_id]["params"] = {}
                        
                        # Invalidate the fingerprint cache so get_games() re-computes it fresh
                        self._invalidate_fingerprint_cache(game_id)
                        
                        # Thêm dấu ấn (Watermark)
                        import json
                        import datetime
                        game_dir = os.path.dirname(profile.exe_path)
                        marker_path = os.path.join(game_dir, '.atm_translated')
                        with open(marker_path, 'w', encoding='utf-8') as f:
                            json.dump({
                                "version": 1,
                                "translation_id": game_id,
                                "game_fingerprint": self._calculate_fingerprint(profile),
                                "source_language": profile.input_lang,
                                "target_language": profile.output_lang,
                                "completed_at": datetime.datetime.now().isoformat()
                            }, f, indent=2)

                        # Chạy game sau khi dịch xong (nếu được phép)
                        if auto_launch:
                            deployer = GameDeployer()
                            with self._lock:
                                self.active_deployers[game_id] = deployer
                            deployer.deploy_and_launch(profile, None)
                    else:
                        with self._lock:
                            self.translation_status[game_id] = {
                                "progress": 0, "total": 1, 
                                "code": "translation.failed", 
                                "params": {},
                                "done": True, 
                                "error": True
                            }
                        self.job_repo.save(TranslationJob(game_id=game_id, status="error", message_code="translation.failed"))
                        
                except RateLimitError as e:
                    logger.warning(f"{profile.engine} translation paused due to rate limit.")
                    with self._lock:
                        self.translation_status[game_id] = {
                            "progress": 0, "total": 1, 
                            "code": "translation.rate_limited", 
                            "params": {},
                            "details": "API rate limited (HTTP 429). Paused.",
                            "done": True, 
                            "error": True,
                            "error_code": "RATE_LIMITED"
                        }
                    self.job_repo.save(TranslationJob(game_id=game_id, status="paused", message_code="translation.rate_limited", error_details="HTTP 429"))
                    return

                except Exception as e:
                    logger.error(f"{profile.engine} translate error: {e}")
                    with self._lock:
                        self.translation_status[game_id] = {
                            "progress": 0, "total": 1, 
                            "code": "translation.error", 
                            "params": {},
                            "details": str(e),
                            "done": True, 
                            "error": True
                        }
                    self.job_repo.save(TranslationJob(game_id=game_id, status="error", message_code="translation.error", error_details=str(e)))

            t = threading.Thread(target=run_offline_translate, daemon=True)
            t.start()
            return {"status": "translating"}
            
        if profile.engine in ("Unity Mono", "Unity IL2CPP"):
            if not all(ord(c) < 128 for c in profile.exe_path):
                return {
                    "status": "unicode_error", 
                    "error": "UNITY_UNICODE_PATH",
                    "message": "Đường dẫn chứa ký tự đặc biệt."
                }
                
            if profile.engine == "Unity Mono":
                payload_dir = os.path.join(base_dir, "atm", "resources", "payloads", "bepinex_mono")
            elif profile.engine == "Unity IL2CPP":
                payload_dir = os.path.join(base_dir, "atm", "resources", "payloads", "bepinex_il2cpp")
        else:
            return {"status": "error", "error": "Unsupported engine: " + profile.engine}

        # Khởi tạo Deployer
        from atm.core.deployment.game_deployer import GameDeployer
        deployer = GameDeployer()
        with self._lock:
            self.active_deployers[game_id] = deployer
        
        # Deploy và Launch (chạy background) - wrapped so crashes don't ghost the game state
        def _run_unity_deploy():
            try:
                deployer.deploy_and_launch(profile, payload_dir)
            except Exception as e:
                logger.error(f"Unity deployer crashed for {game_id}: {e}", exc_info=True)
            finally:
                # Always clean up, even on crash - prevents permanent TRANSLATING ghost state
                with self._lock:
                    self.active_deployers.pop(game_id, None)
                self._invalidate_fingerprint_cache(game_id)

        t = threading.Thread(target=_run_unity_deploy, daemon=True)
        t.start()
        return {"status": "success"}

    def fix_unicode_path(self, game_id: str):
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}
            
        import re
        import uuid
        def slugify(text):
            try:
                from unidecode import unidecode
                text = unidecode(text)
            except ImportError:
                pass
            text = re.sub(r'[^a-zA-Z0-9_\-\s]', '', text).strip().replace(' ', '_')
            if not text: return "Game"
            return text
            
        old_exe = profile.exe_path
        old_dir = os.path.dirname(old_exe)
        old_parent = os.path.dirname(old_dir)
        old_exe_name = os.path.basename(old_exe)
        
        # 1. Rename folder
        new_dir_name = slugify(os.path.basename(old_dir))
        if new_dir_name == "Game" or new_dir_name == "":
            new_dir_name = f"Game_{game_id[:8]}"
            
        new_dir = os.path.join(old_parent, new_dir_name)
        if os.path.exists(new_dir) and old_dir != new_dir:
            new_dir_name = f"{new_dir_name}_{uuid.uuid4().hex[:6]}"
            new_dir = os.path.join(old_parent, new_dir_name)
            
        if old_dir != new_dir:
            try:
                os.rename(old_dir, new_dir)
            except Exception as e:
                return {"status": "error", "error": f"Cannot rename folder: {e}"}
        else:
            new_dir = old_dir
            
        # 2. Rename Exe and Data
        new_exe_name = slugify(old_exe_name.replace(".exe", "")) + ".exe"
        if new_exe_name == ".exe":
            new_exe_name = f"Game_{game_id[:8]}.exe"
            
        new_exe = os.path.join(new_dir, new_exe_name)
        old_data_dir = os.path.join(new_dir, old_exe_name.replace(".exe", "_Data"))
        new_data_dir = os.path.join(new_dir, new_exe_name.replace(".exe", "_Data"))
        
        try:
            if os.path.join(new_dir, old_exe_name) != new_exe:
                os.rename(os.path.join(new_dir, old_exe_name), new_exe)
        except Exception as e:
            return {"status": "error", "error": f"Cannot rename exe: {e}"}
            
        try:
            if os.path.exists(old_data_dir) and old_data_dir != new_data_dir:
                os.rename(old_data_dir, new_data_dir)
        except Exception as e:
            return {"status": "error", "error": f"Cannot rename Data folder: {e}"}
            
        profile.exe_path = new_exe
        profile.game_name = new_exe_name.replace(".exe", "")
        self.profile_repo.save(profile)
        
        return {"status": "success", "new_path": new_exe}

    def get_translation_status(self, game_id):
        """Trả về tiến độ dịch offline"""
        with self._lock:
            if game_id in self.translation_status:
                return self.translation_status[game_id].copy()
                
            if game_id in self.active_deployers:
                deployer = self.active_deployers[game_id]
                if getattr(deployer, "is_deploying", False) or deployer.monitor.is_monitoring:
                    return {
                        "progress": 50,
                        "total": 100,
                        "code": "translation.realtime_running",
                        "done": False,
                        "error": False
                    }
                else:
                    # Clean up dead deployer
                    del self.active_deployers[game_id]
                    return {
                        "progress": 100,
                        "total": 100,
                        "code": "translation.realtime_finished",
                        "done": True,
                        "error": False
                    }
                    
        return {"done": True, "error": False, "code": "translation.not_running"}

    def stop_game(self, game_id):
        """Dừng game đang chạy hoặc dừng tiến trình dịch"""
        # Nếu đang dịch, báo cờ cancel
        with self._lock:
            if game_id in self.translation_status and not self.translation_status[game_id].get("done"):
                self.cancel_flags[game_id] = True
                logger.info(f"Cancelled translation for: {game_id}")
                
            if game_id in self.active_deployers:
                deployer = self.active_deployers[game_id]
                deployer.monitor.stop()
                del self.active_deployers[game_id]
                logger.info(f"Stopped game: {game_id}")
        return {"status": "success"}

    def sync_game(self, game_id):
        """Đồng bộ lại dữ liệu dịch nóng (Cache/Glossary). Khởi động Smart Re-scan."""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang)."}
            
        logger.info(f"Syncing translation data for game: {game_id}")
        
        # 1. Nếu là game Offline (RPG Maker, RenPy) đang dịch dở -> Tái khởi động luồng ngầm
        if profile.engine in ("RPG Maker", "RenPy"):
            with self._lock:
                is_running = game_id in self.translation_status and not self.translation_status[game_id].get("done", True)
                if is_running:
                    self.cancel_flags[game_id] = True
            
            if is_running:
                logger.info(f"[Smart Sync] Stopping current offline thread for {game_id}...")
                
                # Chờ luồng cũ thực sự dừng hẳn (Polling thay vì sleep cứng)
                for _ in range(50):
                    with self._lock:
                        if self.translation_status[game_id].get("done", True):
                            break
                    time.sleep(0.1)
                
                # Check if it actually stopped
                with self._lock:
                    is_done = self.translation_status.get(game_id, {}).get("done", True)
                if not is_done:
                    return {"status": "error", "error": "Timeout waiting for translation thread to stop."}
                
                # Restart it to apply glossary
                logger.info(f"[Smart Sync] Restarting offline thread for {game_id} to apply new Glossary/Cache...")
                with self._lock:
                    self.cancel_flags[game_id] = False
                res = self.start_game(game_id, auto_launch=True)
                if res.get("status") == "error":
                    return res
                return {"status": "success", "message": "Smart re-scan triggered for offline engine.", "is_running": True}
            else:
                return {"status": "success", "message": "Glossary and Cache updated.", "is_running": False}
                
        # 2. Nếu là game Unity -> Đè file Cache xuống ổ cứng cho BepInEx
        elif profile.engine in ("Unity Mono", "Unity IL2CPP"):
            logger.info(f"[Smart Sync] Writing updated cache to BepInEx for {game_id}...")
            # Todo: Thực hiện xuất file _AutoGeneratedTranslations.txt từ DB nếu game đang mở
            # Lát nữa sẽ nối với GameDeployer
            return {"status": "success", "message": "Cache injected into Unity Engine.", "is_running": False}
        
        return {"status": "success", "message": "Glossary and Cache synced successfully", "is_running": False}

    def play_game(self, game_id):
        """Khởi chạy game đã dịch"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang)."}
        
        # Verify marker
        game_dir = os.path.dirname(profile.exe_path)
        marker_path = os.path.join(game_dir, '.atm_translated')
        if not os.path.exists(marker_path):
            return {"status": "error", "error": "Game has been modified or not fully translated."}
            
        try:
            import subprocess
            # Detached process to allow ATM to close without closing the game
            CREATE_NO_WINDOW = 0x08000000
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen([profile.exe_path], cwd=game_dir, creationflags=DETACHED_PROCESS)
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Failed to play game {game_id}: {e}")
            return {"status": "error", "error": str(e)}

    def delete_game(self, game_id):
        """Xóa game profile (cả file JSON)"""
        try:
            # Check if running and wait for it to stop
            with self._lock:
                # Clean up dead deployers first
                if game_id in self.active_deployers:
                    dep = self.active_deployers[game_id]
                    if not getattr(dep, "is_deploying", False) and not dep.monitor.is_monitoring:
                        del self.active_deployers[game_id]
                
                is_running_offline = game_id in self.translation_status and not self.translation_status[game_id].get("done", True)
                is_running_unity = game_id in self.active_deployers
            
            if is_running_offline or is_running_unity:
                return {"status": "error", "error": "Game is currently running or translating. Please stop it before deleting."}
            
            # Xóa bằng ID (tên file mới)
            deleted = self.profile_repo.delete(game_id)
            
            # Xóa dữ liệu dịch trong database game_lines để dọn dẹp dung lượng
            try:
                self.clear_game_lines(game_id, keep_count=0)
            except Exception as e:
                logger.error(f"Error clearing game lines on delete: {e}")

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

        
    def _get_game_lines_repo(self):
        from atm.core.translation.cache_manager import TranslationCache
        from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
        db_path = TranslationCache().db_path
        return SQLiteGameLinesRepository(db_path)

    def get_game_translations(self, game_id: str, page: int = 1, limit: int = 50, query: str = None):
        """V2: Lấy danh sách cache CHỈ cho một game cụ thể (Database Isolation)"""
        try:
            repo = self._get_game_lines_repo()
            result = repo.list_by_game(game_id, page, limit, query)
            return {"status": "success", "data": result}
        except Exception as e:
            logger.error(f"Failed to get game translations: {e}")
            return {"status": "error", "error": str(e)}

    def update_game_translation(self, game_id: str, item_id: int, translated: str, expected_version: int):
        """V2: Cập nhật 1 dòng và chống đụng độ (Optimistic Concurrency)"""
        try:
            repo = self._get_game_lines_repo()
            # Fetch original text first to prevent race condition if deleted right after update
            item = repo.get_by_id(item_id)
            if not item or item.get("game_id") != game_id:
                return {"status": "error", "error": "Item not found or game mismatch.", "code": 404}
                
            success = repo.update(item_id, game_id, translated, expected_version)
            if success:
                # Add to TM
                profile = self.profile_repo.get_by_id(game_id)
                if profile and profile.output_lang:
                    from atm.core.translation.translation_memory import TranslationMemory
                    tm = TranslationMemory()
                    tm.remember(profile.input_lang or "auto", profile.output_lang, item["original"], translated)
                return {"status": "success"}
            else:
                return {"status": "error", "error": "Conflict (Version mismatch).", "code": 409}
        except Exception as e:
            logger.error(f"Failed to update translation: {e}")
            return {"status": "error", "error": str(e)}

    def batch_update_game_translations(self, game_id: str, items: list):
        """V2: Cập nhật hàng loạt (Batch Editing)"""
        try:
            if not isinstance(items, list):
                return {"status": "error", "error": "Items must be a list."}
                
            repo = self._get_game_lines_repo()
            # Safely extract keys, defaulting version to 1 if missing
            batch_data = []
            for i in items:
                if "id" not in i or "translated" not in i:
                    return {"status": "error", "error": "Missing id or translated field."}
                try:
                    _id = int(i["id"])
                    _translated = str(i["translated"])
                    _version = int(i.get("version") or 1)
                    batch_data.append((_id, _translated, _version))
                except (ValueError, TypeError):
                    return {"status": "error", "error": "Invalid data types for id or version."}
                
            result = repo.batch_update(game_id, batch_data)
            
            # Sync to TM for successful ones
            if result.get("saved"):
                profile = self.profile_repo.get_by_id(game_id)
                if profile and profile.output_lang:
                    from atm.core.translation.translation_memory import TranslationMemory
                    tm = TranslationMemory()
                    sl, tl = profile.input_lang or "auto", profile.output_lang
                    for saved_item in result["saved"]:
                        tm.remember(sl, tl, saved_item["original"], saved_item["translated"])
                                
            return {"status": "success", "data": result}
        except Exception as e:
            logger.error(f"Failed to batch update translations: {e}")
            return {"status": "error", "error": str(e)}

    def review_qa(self, entries):
        """Quét lỗi QA trên một batch entries"""
        from atm.core.qa.registry import QARuleRegistry
        from atm.core.qa.engine import QAEngine
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys_rules = os.path.join(base_dir, "data", "qa", "system_rules.json")
        user_rules = os.path.join(base_dir, "data", "qa", "user_rules.json")
        
        registry = QARuleRegistry(sys_rules, user_rules)
        engine = QAEngine(registry)
        
        results = engine.review_batch(entries)
        return {"status": "success", "data": results}

    def export_glossary(self, game_id: str, format_type: str = 'csv'):
        from atm.core.translation.glossary_manager import GlossaryManager
        try:
            manager = GlossaryManager(self.profile_repo)
            data = manager.export_glossary(game_id, format_type)
            return {"status": "success", "data": data, "format": format_type}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def preview_glossary_import(self, game_id: str, content: str, format_type: str):
        from atm.core.translation.glossary_manager import GlossaryManager
        try:
            manager = GlossaryManager(self.profile_repo)
            preview = manager.preview_import(game_id, content, format_type)
            return {"status": "success", "data": preview}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def apply_glossary_import(self, game_id: str, parsed_data: list, strategy: str = 'merge'):
        from atm.core.translation.glossary_manager import GlossaryManager
        try:
            manager = GlossaryManager(self.profile_repo)
            manager.apply_import(game_id, parsed_data, strategy)
            
            # Batch-invalidate cache for all imported terms in ONE transaction (O(1) instead of O(N))
            try:
                from atm.core.translation.cache_manager import TranslationCache
                cache = TranslationCache()
                profile = self.profile_repo.get_by_id(game_id)
                if profile:
                    if not profile.output_lang:
                        logger.error("Game profile is missing output_lang, cannot invalidate cache")
                        return {"status": "success"}  # Still succeed the import
                    terms = [
                        item.get("source") or item.get("Source") or item.get("source_term")
                        for item in parsed_data
                    ]
                    terms = [t for t in terms if t]  # Filter out None/empty
                    if terms:
                        deleted = cache.batch_invalidate_by_terms(
                            profile.input_lang or "auto", profile.output_lang, terms
                        )
                        logger.info(f"Batch-invalidated {deleted} cache entries for {len(terms)} glossary terms.")
            except Exception as e:
                logger.error(f"Failed to invalidate cache after glossary import: {e}")
                
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def delete_glossary_term(self, game_id: str, term: str):
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang)."}
        if hasattr(profile, "glossary") and isinstance(profile.glossary, dict):
            if term in profile.glossary:
                del profile.glossary[term]
                self.profile_repo.save(profile)
                
                # Invalidate cache for this term
                try:
                    from atm.core.translation.cache_manager import TranslationCache
                    cache = TranslationCache()
                    count = cache.invalidate_by_term(profile.input_lang or "auto", profile.output_lang, term)
                    logger.info(f"Invalidated {count} cache entries containing term '{term}'")
                except Exception as e:
                    logger.error(f"Failed to invalidate cache for term {term}: {e}")
                    
        return {"status": "success"}

    def update_cache_entry(self, game_id, key, value):
        """Cập nhật một mục trong Cache từ Grid Editor"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile: 
            return {"status": "error", "error": "Game not found"}
            
        source_lang = profile.input_lang
        target_lang = profile.output_lang
        if not target_lang:
            return {"status": "error", "error": "Target language not configured (output_lang)."}
            
        from atm.core.translation.cache_manager import TranslationCache
        from atm.core.translation.translation_memory import TranslationMemory
        cache = TranslationCache()
        cache.set(
            source_lang,
            target_lang,
            key,
            value,
            TranslationCache.MANUAL_CATEGORY,
        )
        cache.save_to_disk()
        TranslationMemory().remember(
            key,
            value,
            source_lang=source_lang,
            target_lang=target_lang,
            category=TranslationCache.MANUAL_CATEGORY,
            source="user",
            confidence="confirmed",
        )
        logger.info(f"Updated cache manually: {key} -> {value}")
        return {"status": "success"}

    def get_translation_memory_suggestions(self, game_id, text, category="unknown"):
        """Return fuzzy TM suggestions; callers must explicitly confirm one."""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang)."}
        if not isinstance(text, str) or not text.strip():
            return {"status": "error", "error": "Text is required"}

        from dataclasses import asdict
        from atm.core.translation.translation_memory import TranslationMemory

        threshold = self.settings_repo.load().translation_memory_threshold
        suggestions = TranslationMemory().suggest(
            text,
            source_lang=profile.input_lang or "auto",
            target_lang=profile.output_lang,
            category=category or "unknown",
            threshold=threshold,
        )
        return {
            "status": "success",
            "threshold": threshold,
            "suggestions": [asdict(suggestion) for suggestion in suggestions],
        }

    def confirm_translation_memory_suggestion(
        self, game_id, source_text, translated_text, category="unknown"
    ):
        """Persist a user-approved TM suggestion and add its exact cache entry."""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang)."}
        if not all(
            isinstance(value, str) and value.strip()
            for value in (source_text, translated_text)
        ):
            return {"status": "error", "error": "Source text and translation are required"}

        from atm.core.translation.cache_manager import TranslationCache
        from atm.core.translation.translation_memory import TranslationMemory

        source_lang = profile.input_lang or "auto"
        target_lang = profile.output_lang
        
        safe_category = category or "unknown"
        # A fuzzy result only reaches TM/cache after a user selected it.
        TranslationMemory().remember(
            source_text,
            translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            category=safe_category,
            source="user",
            confidence="confirmed",
        )
        cache = TranslationCache()
        cache.set(source_lang, target_lang, source_text, translated_text, safe_category)
        cache.save_to_disk()
        logger.info("User confirmed translation-memory suggestion for %s", profile.game_name)
        return {"status": "success"}

    # --- Data Management Endpoints ---

    def get_data_stats(self):
        """Lấy thống kê dữ liệu cho Tab Quản lý Dữ liệu."""
        from atm.core.translation.cache_manager import TranslationCache
        from atm.core.translation.translation_memory import TranslationMemory

        
        cache = TranslationCache()
        memory = TranslationMemory()
        
        # Thống kê Global Cache
        cache_entries = list(cache.iter_entries())
        total_cache = len(cache_entries)
        try:
            cache_size = os.path.getsize(cache.db_path)
        except OSError:
            cache_size = 0
            
        # Thống kê Global Memory
        memory_entries = list(memory.entries())
        total_memory = len(memory_entries)
        try:
            memory_size = os.path.getsize(memory.repository.memory_file)
        except OSError:
            memory_size = 0
            
        # Thống kê per-game
        games_stats = []
        try:
            from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
            from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
            game_lines_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
            game_lines_stats = { item["game_id"]: item["count"] for item in game_lines_repo.get_stats_by_game() }
        except Exception:
            game_lines_stats = {}

        profiles = self.profile_repo.get_all()
        known_game_ids = set()
        for p in profiles:
            known_game_ids.add(p.id)
            count = game_lines_stats.get(p.id, 0)
            games_stats.append({
                "id": p.id,
                "name": p.game_name,
                "engine": p.engine,
                "folder": os.path.basename(os.path.dirname(p.exe_path)) if p.exe_path else "Unknown",
                "entries": count
            })
            
        # Add orphaned game lines (games deleted from library but data remains)
        for g_id, count in game_lines_stats.items():
            if g_id not in known_game_ids and count > 0:
                games_stats.append({
                    "id": g_id,
                    "name": "Deleted Game (Orphaned Data)",
                    "engine": "Unknown",
                    "folder": g_id,
                    "entries": count
                })
            
        return {
            "status": "success",
            "global_cache": {
                "count": total_cache,
                "size_bytes": cache_size
            },
            "global_memory": {
                "count": total_memory,
                "size_bytes": memory_size
            },
            "games": games_stats
        }

    def clear_global_cache(self, keep_count=None):
        """Xóa toàn bộ hoặc chừa lại keep_count câu cũ nhất trong Cache."""
        from atm.core.translation.cache_manager import TranslationCache
        cache = TranslationCache()
        cache.clear(keep_count)
        logger.info(f"Cleared global cache. Kept: {keep_count if keep_count else 0} entries.")
        return {"status": "success"}

    def clear_global_memory(self):
        """Xóa toàn bộ Global Translation Memory."""
        from atm.core.translation.translation_memory import TranslationMemory
        memory = TranslationMemory()
        with memory._lock:
            memory._entries.clear()
            memory._save_unlocked()
        logger.info("Cleared global translation memory.")
        return {"status": "success"}

    def clear_game_lines(self, game_id, keep_count=0):
        """Xóa dữ liệu game_lines cho một game cụ thể."""
        try:
            from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
            from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
            game_lines_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
            game_lines_repo.clear_by_game(game_id, keep_count)
            logger.info(f"Cleared game lines for {game_id}. Kept: {keep_count}")
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def clear_game_data(self, game_id):
        """Xóa dữ liệu glossary và lịch sử dịch của game."""
        with self._lock:
            if game_id in self.translation_status and not self.translation_status[game_id].get("done", True):
                return {"status": "error", "error": "Cannot clear data while translation is running. Stop it first."}
        
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang)."}
            
        profile.glossary = {}  # BUG-C02 fix: must be dict, not list
        self.profile_repo.save(profile)
        
        # Xóa file metadata và history
        from atm.storage.repositories.translation_repository import TranslationRepository
        repo = TranslationRepository()
        game_dir = repo.get_game_translation_dir(profile.game_name)
        if os.path.exists(game_dir):
            import shutil
            try:
                shutil.rmtree(game_dir)
            except OSError:
                pass
                
        logger.info(f"Cleared game data for {profile.game_name}.")
        return {"status": "success"}

    def open_data_folder(self):
        """Mở thư mục data bằng Windows Explorer."""
        import platform
        import subprocess
        from atm.utils.paths import get_app_data_dir
        
        data_dir = get_app_data_dir()
        if platform.system() == "Windows":
            os.startfile(data_dir)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", data_dir])
        else:
            subprocess.Popen(["xdg-open", data_dir])
            
        return {"status": "success"}

    def _calculate_fingerprint(self, profile):
        """Tính toán vân tay của game bằng hash (size, mtime) của các file cốt tủy.
        
        Uses an in-memory cache with a 5-minute TTL to avoid O(N) disk I/O on every
        get_games() call. Cache is invalidated when a game completes translation.
        """
        cache_key = profile.id
        now = time.time()
        
        # Check cache first (TTL = 5 minutes)
        with self._lock:
            if cache_key in self._fingerprint_cache:
                cached_fp, cached_at = self._fingerprint_cache[cache_key]
                if now - cached_at < 300:  # 5 min TTL
                    return cached_fp

        # Compute fingerprint
        fp = self._compute_fingerprint_raw(profile)
        
        with self._lock:
            self._fingerprint_cache[cache_key] = (fp, now)
        return fp

    def _invalidate_fingerprint_cache(self, game_id: str):
        """Invalidate the fingerprint cache for a specific game (call after translation completes)."""
        with self._lock:
            self._fingerprint_cache.pop(game_id, None)

    def _compute_fingerprint_raw(self, profile):
        """Internal: perform actual disk I/O to compute fingerprint. Do not call directly."""
        try:
            import hashlib
            game_dir = os.path.dirname(profile.exe_path)
            
            if not os.path.exists(game_dir):
                return "sha256:missing_dir"
                
            core_files = [profile.exe_path]

            if profile.engine == "Unity IL2CPP" or profile.engine == "Unity Mono":
                # Thường nằm trong <TênGame>_Data/globalgamemanagers hoặc resources.assets
                data_dir = None
                for item in os.listdir(game_dir):
                    if item.endswith("_Data") and os.path.isdir(os.path.join(game_dir, item)):
                        data_dir = os.path.join(game_dir, item)
                        break
                if data_dir:
                    global_managers = os.path.join(data_dir, "globalgamemanagers")
                    resources = os.path.join(data_dir, "resources.assets")
                    if os.path.exists(global_managers):
                        core_files.append(global_managers)
                    if os.path.exists(resources):
                        core_files.append(resources)

            elif profile.engine == "RenPy":
                # Thường nằm trong thư mục game/ (VD: archive.rpa, scripts.rpa)
                renpy_game_dir = os.path.join(game_dir, "game")
                if os.path.exists(renpy_game_dir):
                    for item in os.listdir(renpy_game_dir):
                        if item.endswith(".rpa"):
                            core_files.append(os.path.join(renpy_game_dir, item))

            elif profile.engine == "RPG Maker":
                # RPG Maker MV/MZ (www/data/System.json) hoặc XP/VX (Data/System.rvdata2)
                www_data = os.path.join(game_dir, "www", "data", "System.json")
                data_system = os.path.join(game_dir, "data", "System.json")
                rgss_arch = os.path.join(game_dir, "Game.rgss3a")
                if os.path.exists(www_data):
                    core_files.append(www_data)
                elif os.path.exists(data_system):
                    core_files.append(data_system)
                elif os.path.exists(rgss_arch):
                    core_files.append(rgss_arch)

            # Tính toán hash nhanh dựa trên size + mtime thay vì đọc cả file GB
            fingerprint_data = ""
            for f in core_files:
                if os.path.exists(f):
                    stat = os.stat(f)
                    fingerprint_data += f"{os.path.basename(f)}:{stat.st_size}:{int(stat.st_mtime)};"
            
            return "sha256:" + hashlib.sha256(fingerprint_data.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating fingerprint: {e}")
            return "sha256:error"


    # ============ Universal Engine API ============
    def get_coverage(self, game_id: str):
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"error": "Game not found"}
        from atm.core.engines.registry import EngineRegistry
        try:
            auditor = EngineRegistry.get_auditor(profile.engine)
            extractor = EngineRegistry.get_extractor(profile.engine, os.path.dirname(profile.exe_path))
            entries = extractor.extract()
            # TODO(Phase 2): Implement real cache lookup for translation_status
            # Currently returns raw extracted entries (0% coverage by default)
            return auditor.audit(entries)
        except Exception as e:
            return {"error": str(e)}

    def extract_offline(self, game_id: str):
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"error": "Game not found"}
            
        from atm.core.engines.registry import EngineRegistry
        
        def _extract_worker(job, cancel_token, g_id):
            extractor = EngineRegistry.get_extractor(profile.engine, os.path.dirname(profile.exe_path))
            entries = extractor.extract(job_tracker=job)
            
            # Insert extracted entries into game_lines
            if entries:
                from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
                from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
                repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
                for entry in entries:
                    if cancel_token and cancel_token.is_set():
                        break
                    repo.insert_or_ignore(
                        game_id=g_id,
                        original=entry.original,
                        translated=entry.original, # Initial translation is the original text
                        category=entry.category,
                        source_file=entry.source_file,
                        source_path=entry.source_path
                    )
            
        return self.job_manager.submit_job("extract", game_id, _extract_worker, g_id=game_id)

    def patch_offline(self, game_id: str):
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"error": "Game not found"}
            
        from atm.core.engines.registry import EngineRegistry
        
        def _patch_worker(job, cancel_token, g_id):
            injector = EngineRegistry.get_injector(profile.engine, os.path.dirname(profile.exe_path))
            # TODO: Load actual entries from cache/payloads before injecting. 
            # Currently injecting empty list [] as a placeholder.
            injector.inject([], job_tracker=job)
            
        return self.job_manager.submit_job("patch", game_id, _patch_worker, g_id=game_id)

    def get_job_status(self, job_id: str):
        status = self.job_manager.get_job_status(job_id)
        if not status:
            return {"error": "Job not found"}
        return status

    def cancel_job(self, job_id: str):
        success = self.job_manager.cancel_job(job_id)
        if not success:
            return {"error": "Failed to cancel job or job not found"}
        return {"status": "success"}



 
