import os
import uuid
import threading

from atm.storage.repositories.profile_repository import ProfileRepository
from atm.storage.repositories.settings_repository import SettingsRepository
from atm.storage.repositories.job_repository import JobRepository, TranslationJob
from atm.config.schema import GameProfile
from atm.core.detectors.game_detector import GameDetector
from atm.utils.logger import get_logger
from atm.core.translation.translators import RateLimitError

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
        
        # Recover paused jobs
        self._recover_jobs()

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
        return settings.model_dump()

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
                            logger.info(f"Fingerprint mismatch for {p.game_name}. Dropping to READY.")
                            p_dict["runtime_state"] = "READY"
                except Exception as e:
                    logger.error(f"Error checking watermark for {p.game_name}: {e}")
                    p_dict["runtime_state"] = "READY"

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
                    title="Chọn file chạy của game (.exe)",
                    filetypes=[("Executable Files", "*.exe"), ("All files", "*.*")]
                )
            finally:
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
        
        # Block multiple starts
        if game_id in self.translation_status and not self.translation_status[game_id].get("done", True):
            return {"status": "translating", "message": "Already translating"}

        if profile.engine in ("RPG Maker", "RenPy"):
            # Dịch Offline cho RPG Maker và RenPy
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
                    translator = RPGMakerTranslator()
                else:
                    translator = RenPyTranslator()
                
                def progress_cb(current, total, code, params=None):
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
                    return self.cancel_flags.get(game_id, False)

                try:
                    success = translator.translate_game(profile, progress_callback=progress_cb, is_cancelled=is_cancelled)
                    if self.cancel_flags.get(game_id, False):
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
                        self.translation_status[game_id]["done"] = True
                        self.translation_status[game_id]["code"] = "translation.success"
                        self.translation_status[game_id]["params"] = {}
                        
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

                        # Chạy game sau khi dịch xong (không cần payload cho offline)
                        deployer = GameDeployer()
                        self.active_deployers[game_id] = deployer
                        deployer.deploy_and_launch(profile, None)
                    else:
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
                    self.translation_status[game_id] = {
                        "progress": 0, "total": 1, 
                        "code": "translation.rate_limited", 
                        "params": {},
                        "details": "API bị giới hạn (HTTP 429). Đã tạm dừng.",
                        "done": True, 
                        "error": True,
                        "error_code": "RATE_LIMITED"
                    }
                    self.job_repo.save(TranslationJob(game_id=game_id, status="paused", message_code="translation.rate_limited", error_details="HTTP 429"))
                    return

                except Exception as e:
                    logger.error(f"{profile.engine} translate error: {e}")
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
            
        if profile.engine == "Unity Mono":
            payload_dir = os.path.join(base_dir, "data", "payloads", "bepinex_mono")
            engine_req = "Unity Mono"
        elif profile.engine == "Unity IL2CPP":
            payload_dir = os.path.join(base_dir, "data", "payloads", "bepinex_il2cpp")
            engine_req = "Unity IL2CPP"
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
        if game_id in self.translation_status:
            return self.translation_status[game_id]
            
        # Try loading from saved job
        job = self.job_repo.load(game_id)
        if job:
            return {
                "progress": job.progress,
                "total": job.total,
                "code": job.message_code,
                "params": job.params,
                "done": job.status in ("completed", "error", "paused"),
                "error": job.status == "error",
                "details": job.error_details,
                "status_str": job.status
            }

        return {
            "progress": 0, 
            "total": 0, 
            "code": "translation.idle", 
            "params": {},
            "done": True,
            "error": False
        }

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

    def play_game(self, game_id):
        """Khởi chạy game đã dịch"""
        profile = self.profile_repo.load(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}
        
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
        # The editor currently displays one value per source string. Core
        # storage still retains the context category for every entry.
        for _source, _target, _category, original, translated in cache.iter_entries():
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
        if not isinstance(text, str) or not text.strip():
            return {"status": "error", "error": "Text is required"}

        from dataclasses import asdict
        from atm.core.translation.translation_memory import TranslationMemory

        threshold = self.settings_repo.load().translation_memory_threshold
        suggestions = TranslationMemory().suggest(
            text,
            source_lang=profile.input_lang or "auto",
            target_lang=profile.output_lang or "vi",
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
        if not all(
            isinstance(value, str) and value.strip()
            for value in (source_text, translated_text)
        ):
            return {"status": "error", "error": "Source text and translation are required"}

        from atm.core.translation.cache_manager import TranslationCache
        from atm.core.translation.translation_memory import TranslationMemory

        source_lang = profile.input_lang or "auto"
        target_lang = profile.output_lang or "vi"
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
            cache_size = os.path.getsize(cache.cache_file)
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
        profiles = self.profile_repo.get_all()
        for p in profiles:
            games_stats.append({
                "id": p.id,
                "name": p.game_name,
                "engine": p.engine,
                "cache_hits": 0,  # Có thể tính sau
                "tm_entries": 0,
                "glossary_terms": len(p.glossary) if p.glossary else 0
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
        if keep_count is None or keep_count <= 0:
            cache.cache.clear()
        else:
            # Xóa các entry cũ nhất (giả định Python dict insertion order)
            keys_to_remove = list(cache.cache.keys())[:-keep_count]
            for k in keys_to_remove:
                del cache.cache[k]
        
        cache.save_to_disk()
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

    def clear_game_data(self, game_id):
        """Xóa dữ liệu glossary và lịch sử dịch của game."""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}
            
        profile.glossary = []
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
        """Tính toán vân tay của game bằng hash (size, mtime) của các file cốt tủy"""
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
