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
from atm.core.deployment.game_deployer import GameDeployer

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


def detect_key_mismatch(provider: str, api_key: str):
    """Phát hiện nếu người dùng dán nhầm API key của hãng khác."""
    if not api_key:
        return None
    key = api_key.strip()
    provider = (provider or "").lower()

    if key.startswith("AIzaSy"):
        if provider != "gemini":
            return {
                "detected_provider": "gemini",
                "detected_name": "Google Gemini",
                "warning": f"API Key bắt đầu bằng 'AIzaSy' có vẻ là của Google Gemini, không phải của {provider.upper()}."
            }
    elif key.startswith("sk-ant-"):
        if provider != "claude":
            return {
                "detected_provider": "claude",
                "detected_name": "Anthropic Claude",
                "warning": f"API Key bắt đầu bằng 'sk-ant-' có vẻ là của Anthropic Claude, không phải của {provider.upper()}."
            }
    elif key.endswith(":fx"):
        if provider != "deepl":
            return {
                "detected_provider": "deepl",
                "detected_name": "DeepL (Free Tier)",
                "warning": f"API Key kết thúc bằng ':fx' có vẻ là của DeepL Free, không phải của {provider.upper()}."
            }
    return None


def detect_model_mismatch(provider: str, model: str):
    """Phát hiện nếu người dùng nhập model thuộc hãng khác."""
    if not model:
        return None
    m = model.strip().lower()
    prov = (provider or "").lower()
    if prov == "custom_llm":
        return None

    detected_prov = None
    detected_name = None

    if m.startswith("gemini-") or m.startswith("models/gemini"):
        detected_prov = "gemini"
        detected_name = "Google Gemini"
    elif m.startswith("claude-"):
        detected_prov = "claude"
        detected_name = "Anthropic Claude"
    elif m.startswith("deepseek-"):
        detected_prov = "deepseek"
        detected_name = "DeepSeek"
    elif m.startswith("moonshot-") or m.startswith("kimi-"):
        detected_prov = "kimi"
        detected_name = "Moonshot Kimi"
    elif m.startswith("gpt-") or m.startswith("o1-") or m.startswith("o3-") or m.startswith("o4-") or m.startswith("chatgpt-"):
        detected_prov = "openai"
        detected_name = "OpenAI"

    if detected_prov and detected_prov != prov:
        prov_names = {
            "gemini": "Google Gemini",
            "claude": "Anthropic Claude",
            "openai": "OpenAI",
            "deepseek": "DeepSeek",
            "kimi": "Moonshot Kimi",
        }
        prov_display = prov_names.get(prov, prov.upper())
        return {
            "detected_provider": detected_prov,
            "detected_name": detected_name,
            "warning": f"Mô hình '{model.strip()}' có vẻ là của {detected_name}, không phải của {prov_display}."
        }
    return None


def validate_api_key(provider: str, api_key: str):
    """Kiểm tra tính hợp lệ của API key theo từng hãng (định dạng, độ dài tối thiểu).
    Trả về (is_valid, error_message).
    """
    if not api_key:
        return True, ""
    key = api_key.strip()
    if not key:
        return True, ""

    prov = (provider or "").lower()

    # Kiểm tra dán nhầm key của hãng khác (Soft Warning - không chặn)
    mismatch = detect_key_mismatch(prov, key)
    if mismatch:
        return True, mismatch["warning"]

    if prov == "gemini":
        if not key.startswith("AIzaSy"):
            return False, "Khóa Google Gemini không hợp lệ (phải bắt đầu bằng 'AIzaSy')."
        if len(key) < 30:
            return False, "Khóa Google Gemini quá ngắn (độ dài tối thiểu 30 ký tự)."
    elif prov == "claude":
        if not key.startswith("sk-ant-"):
            return False, "Khóa Anthropic Claude không hợp lệ (phải bắt đầu bằng 'sk-ant-')."
        if len(key) < 30:
            return False, "Khóa Anthropic Claude quá ngắn (độ dài tối thiểu 30 ký tự)."
    elif prov in ("openai", "deepseek", "kimi"):
        if not key.startswith("sk-"):
            return False, f"Khóa {prov.upper()} không hợp lệ (phải bắt đầu bằng 'sk-')."
        if len(key) < 20:
            return False, f"Khóa {prov.upper()} quá ngắn (độ dài tối thiểu 20 ký tự)."
    elif prov == "deepl":
        if len(key) < 20:
            return False, "Khóa DeepL API quá ngắn (độ dài tối thiểu 20 ký tự)."
    elif prov == "custom_llm":
        if len(key) < 3:
            return False, "Khóa Custom LLM quá ngắn (tối thiểu 3 ký tự nếu nhập)."
    else:
        if len(key) < 10:
            return False, "Khóa API không hợp lệ (độ dài quá ngắn)."

    return True, ""


class BackendApi:
    def __init__(self):
        self.profile_repo = ProfileRepository()
        self.settings_repo = SettingsRepository()
        self.job_repo = JobRepository()
        self.window = None
        self.active_deployers = {}  # game_id -> deployer
        self.translation_status = {}  # game_id -> {"progress": int, "total": int, "message": str, "done": bool}
        self.translation_threads = {}  # game_id -> threading.Thread
        self.cancel_flags = {}  # game_id -> bool
        self._lock = threading.RLock()
        self.job_manager = JobManager(max_workers=4)
        # In-memory fingerprint cache: {game_id: (fingerprint_str, computed_at_timestamp)}
        # Avoids O(N) disk I/O on every get_games() call. Invalidated when a game completes translation.
        self._fingerprint_cache = {}
        # Recover zombie jobs from before last restart
        self._recover_jobs()
        
        try:
            from atm.container import container
            from atm.core.events.event_bus import SystemEvents
            bus = container.get("EventBus")
            if bus:
                def on_error(data):
                    if data and isinstance(data, dict) and "game_id" in data:
                        g_id = data["game_id"]
                        err_code = data.get("error_code", "translation.failed")
                        err_details = data.get("error_details", data.get("error", "Unknown error"))
                        with self._lock:
                            if g_id not in self.translation_status:
                                self.translation_status[g_id] = {}
                            self.translation_status[g_id].update({
                                "done": True,
                                "error": True,
                                "code": err_code,
                                "params": {"details": err_details}
                            })
                bus.subscribe(SystemEvents.ERROR_OCCURRED, on_error)
        except Exception:
            pass

    def _get_game_dir(self, profile) -> str:
        """Safely resolve game folder directory from profile path or exe_path."""
        if not profile:
            return ""
        if getattr(profile, "path", None) and os.path.isdir(profile.path):
            return profile.path
        if getattr(profile, "exe_path", None):
            return os.path.dirname(profile.exe_path)
        return ""

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
            for t in self.translation_threads.values():
                if t and t.is_alive():
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
        for key_field in [
            "deepl_api_key",
            "gemini_api_key",
            "deepseek_api_key",
            "openai_api_key",
            "claude_api_key",
            "kimi_api_key",
            "custom_llm_api_key",
        ]:
            data[f"{key_field}_configured"] = bool(data.get(key_field))
            data.pop(key_field, None)
        data["custom_llm_configured"] = bool(data.get("custom_llm_model") and data.get("custom_llm_base_url"))
        return data

    def update_settings(self, **kwargs):
        """Cập nhật cấu hình"""
        # Validate API key formats if provided
        key_warnings = []
        for prov in ["gemini", "deepseek", "openai", "claude", "kimi", "deepl", "custom_llm"]:
            key_name = f"{prov}_api_key"
            if key_name in kwargs and kwargs[key_name]:
                val = str(kwargs[key_name]).strip()
                is_valid, msg = validate_api_key(prov, val)
                if not is_valid:
                    return {
                        "status": "error",
                        "error": msg,
                        "code": "error.invalid_api_key_format",
                        "params": {"provider": prov}
                    }
                elif msg:
                    key_warnings.append(msg)

        # Validate Model mismatch and normalize casing if provided
        for prov in ["gemini", "deepseek", "openai", "claude", "kimi"]:
            m_name = f"{prov}_model"
            if m_name in kwargs and kwargs[m_name]:
                m_val = str(kwargs[m_name]).strip().lower()
                kwargs[m_name] = m_val
                mismatch = detect_model_mismatch(prov, m_val)
                if mismatch:
                    return {
                        "status": "error",
                        "error": mismatch["warning"],
                        "code": "error.invalid_model_format",
                        "params": {"provider": prov, "model": m_val}
                    }

        settings = self.settings_repo.load()
        for key in [
            "dark_mode",
            "ui_language",
            "deepl_api_key",
            "gemini_api_key",
            "gemini_model",
            "gemini_base_url",
            "deepseek_api_key",
            "deepseek_model",
            "deepseek_base_url",
            "openai_api_key",
            "openai_model",
            "openai_base_url",
            "claude_api_key",
            "claude_model",
            "claude_base_url",
            "kimi_api_key",
            "kimi_model",
            "kimi_base_url",
            "custom_llm_api_key",
            "custom_llm_base_url",
            "custom_llm_model",
        ]:
            if key in kwargs:
                val = kwargs[key]
                if val is not None:
                    setattr(settings, key, val)

        if "translation_memory_threshold" in kwargs:
            try:
                threshold = float(kwargs["translation_memory_threshold"])
                if not 0.0 <= threshold <= 1.0:
                    return {"status": "error", "error": "Translation-memory threshold must be between 0 and 1", "code": "error.invalid_threshold"}
                settings.translation_memory_threshold = threshold
            except (TypeError, ValueError):
                return {"status": "error", "error": "Invalid translation-memory threshold", "code": "error.invalid_threshold"}
        
        self.settings_repo.save(settings)
        res = {"status": "success"}
        if key_warnings:
            res["warning"] = " | ".join(key_warnings)
        return res

    def detect_key_mismatch(self, provider: str, api_key: str):
        return detect_key_mismatch(provider, api_key)

    def detect_model_mismatch(self, provider: str, model: str):
        return detect_model_mismatch(provider, model)

    def validate_api_key(self, provider: str, api_key: str):
        return validate_api_key(provider, api_key)

    def test_ai_connection(self, provider: str, api_key: str = None, model: str = None, base_url: str = None):
        """Kiểm tra kết nối tới nhà cung cấp AI."""
        import time
        from atm.core.translation.translators import LLMTranslator
        
        settings = self.settings_repo.load()
        provider = (provider or "gemini").lower()
        
        # Nếu không truyền key, lấy key đã lưu trong settings
        if not api_key:
            api_key = getattr(settings, f"{provider}_api_key", "")
            
        if not model:
            model = getattr(settings, f"{provider}_model", None)
            
        if not base_url:
            base_url = getattr(settings, f"{provider}_base_url", "")
        if not base_url and provider == "custom_llm":
            base_url = "http://localhost:11434/v1"

        if not api_key and provider != "custom_llm":
            return {"status": "error", "error": "API Key is required", "code": "error.api_key_missing"}

        # Kiểm tra tính hợp lệ của key
        if api_key:
            is_valid, val_err = validate_api_key(provider, api_key)
            if not is_valid:
                return {
                    "status": "error",
                    "error": val_err,
                    "code": "error.invalid_api_key_format"
                }

        # Kiểm tra dán nhầm key
        mismatch = self.detect_key_mismatch(provider, api_key)

        # Kiểm tra nhập nhầm model và chuẩn hóa chữ thường
        if model:
            if provider in ("gemini", "openai", "deepseek", "claude", "kimi"):
                model = model.strip().lower()
            else:
                model = model.strip()
            model_mismatch = detect_model_mismatch(provider, model)
            if model_mismatch:
                return {
                    "status": "error",
                    "error": model_mismatch["warning"],
                    "code": "error.invalid_model_format"
                }

        if provider == "deepl":
            if not api_key:
                return {"status": "error", "error": "DeepL API Key is required", "code": "error.api_key_missing"}
            from atm.core.translation.translators import DeepLTranslator
            translator = DeepLTranslator(api_key=api_key)
            start_time = time.time()
            try:
                res = translator.translate_batch(["Hello world"], target_lang="VI", source_lang="EN")
                latency_ms = int((time.time() - start_time) * 1000)
                if res and res[0] and res[0].strip():
                    return {
                        "status": "success",
                        "provider": "deepl",
                        "model": "DeepL API",
                        "latency_ms": latency_ms,
                        "result": res[0]
                    }
                else:
                    return {"status": "error", "error": "Empty response received from DeepL", "code": "error.api_empty_response", "latency_ms": latency_ms}
            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                return {"status": "error", "error": str(e), "code": "error.api_connection_failed", "latency_ms": latency_ms}

        translator = LLMTranslator(
            provider=provider,
            api_key=api_key or "",
            model=model,
            base_url=base_url,
            timeout=8.0,
        )

        start_time = time.time()
        try:
            res = translator._do_translate_batch(
                ["Hello world"], 
                target_lang="vi", 
                source_lang="en",
                disable_fallback=True
            )
            latency_ms = int((time.time() - start_time) * 1000)
            if res and res[0] and res[0].strip():
                ret = {
                    "status": "success",
                    "provider": provider,
                    "model": translator.model,
                    "latency_ms": latency_ms,
                    "result": res[0]
                }
                if mismatch:
                    ret["warning"] = mismatch["warning"]
                return ret
            else:
                return {
                    "status": "error",
                    "error": "Empty response received from AI model",
                    "code": "error.api_empty_response",
                    "latency_ms": latency_ms
                }
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Test AI connection failed for {provider}: {e}")
            err_msg = str(e)
            if "10061" in err_msg or "actively refused" in err_msg:
                target_host = base_url or "http://localhost:11434/v1"
                err_msg = f"Connection refused at {target_host}. Please make sure your local LLM server (e.g. Ollama/LM Studio) is running."
            if mismatch:
                err_msg += f" ({mismatch['warning']})"
            return {
                "status": "error",
                "error": err_msg,
                "code": "error.api_connection_failed",
                "latency_ms": latency_ms
            }

    def fetch_available_models(self, provider: str, api_key: str = None, base_url: str = None):
        """Lấy danh sách các model khả dụng từ máy chủ API của nhà cung cấp."""
        import json
        import urllib.request
        import urllib.error

        settings = self.settings_repo.load()
        provider = (provider or "gemini").lower()
        if not api_key:
            api_key = getattr(settings, f"{provider}_api_key", "")
        if not base_url:
            base_url = getattr(settings, f"{provider}_base_url", "")

        if not api_key and provider != "custom_llm":
            return {
                "status": "error",
                "error": "API Key is required to fetch models",
                "code": "error.api_key_missing"
            }

        try:
            if provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                req = urllib.request.Request(url, headers={"User-Agent": "ATM-Client/2.0"})
                with urllib.request.urlopen(req, timeout=12.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models_list = []
                    for item in data.get("models", []):
                        methods = item.get("supportedGenerationMethods", [])
                        if "generateContent" in methods:
                            name = item.get("name", "")
                            if name.startswith("models/"):
                                name = name[7:]
                            if not any(x in name for x in ("embedding", "aqa", "imagen", "tts", "whisper")):
                                models_list.append(name)
                    models_list.sort(reverse=True)
                    return {"status": "success", "provider": provider, "models": models_list}

            elif provider == "claude":
                endpoint = (base_url or "https://api.anthropic.com/v1").rstrip("/") + "/models"
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "User-Agent": "ATM-Client/2.0"
                }
                req = urllib.request.Request(endpoint, headers=headers)
                with urllib.request.urlopen(req, timeout=12.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    raw = data.get("data", [])
                    models_list = [m.get("id") for m in raw if isinstance(m, dict) and m.get("id")]
                    return {"status": "success", "provider": provider, "models": models_list}

            else:
                default_urls = {
                    "openai": "https://api.openai.com/v1",
                    "deepseek": "https://api.deepseek.com",
                    "kimi": "https://api.moonshot.cn/v1",
                    "custom_llm": "http://localhost:11434/v1",
                }
                url_root = (base_url or default_urls.get(provider, "https://api.openai.com/v1")).rstrip("/")
                endpoint = f"{url_root}/models"
                headers = {"User-Agent": "ATM-Client/2.0"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                req = urllib.request.Request(endpoint, headers=headers)
                with urllib.request.urlopen(req, timeout=12.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    raw_items = data.get("data", []) if isinstance(data, dict) else data
                    models_list = []
                    if isinstance(raw_items, list):
                        for m in raw_items:
                            if isinstance(m, dict) and "id" in m:
                                mid = m["id"]
                                if not any(x in mid.lower() for x in ("whisper", "tts", "dall-e", "embedding", "text-embedding", "babbage", "davinci", "moderation")):
                                    models_list.append(mid)
                            elif isinstance(m, str):
                                models_list.append(m)
                    models_list.sort(reverse=True)
                    return {"status": "success", "provider": provider, "models": models_list}

        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                raw = e.read().decode("utf-8", errors="ignore")
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    err_obj = parsed.get("error") or parsed.get("message")
                    if isinstance(err_obj, dict):
                        err_body = err_obj.get("message") or str(err_obj)
                    else:
                        err_body = str(err_obj)
            except Exception:
                pass
            detail = f": {err_body}" if err_body else ""
            if e.code in (401, 403):
                return {"status": "error", "error": f"Invalid API Key or unauthorized account{detail}", "code": "error.api_unauthorized"}
            return {"status": "error", "error": f"Failed to fetch models from provider{detail}", "code": "error.api_connection_failed"}
        except Exception as e:
            return {"status": "error", "error": str(e), "code": "error.api_connection_failed"}


    def get_games(self):
        """Trả về danh sách game profile cho JS"""
        profiles = self.profile_repo.get_all()
        result = []
        for p in profiles:
            if getattr(p, 'is_deleted', False):
                continue
            p_dict = p.model_dump()
            p_dict.pop('glossary', None)
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
                        try:
                            from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
                            from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
                            gl_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
                            p_dict["runtime_lines"] = gl_repo.count_by_game(p.id)
                        except Exception:
                            p_dict["runtime_lines"] = 0
                
            # --- KIỂM TRA MẶT VẬT LÝ (WATERMARK) ---
            if p_dict["runtime_state"] == "COMPLETE":
                if p.engine in ("Unity Mono", "Unity IL2CPP", "Bakin"):
                    p_dict["runtime_state"] = "READY"
                else:
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
                    if getattr(existing, 'is_deleted', False):
                        existing.is_deleted = False
                        self.profile_repo.save(existing)
                        return {"status": "success", "profile": existing.model_dump()}
                    logger.warning(f"Game already exists: {file_path}")
                    return {"status": "error", "error": "Game already exists in the system!", "code": "toast.duplicate_game"}

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
            return {"status": "error", "error": "Game not found", "code": "error.game_not_found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang).", "code": "error.target_lang_missing"}

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
            return {"status": "error", "error": "Game profile not found", "code": "error.game_not_found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Please select target language (output_lang) before starting translation.", "code": "error.target_lang_missing"}

        # Validate AI / DeepL API Key configuration
        translator_id = (getattr(profile, "translator", "google") or "google").lower()
        if translator_id in ("gemini", "deepseek", "openai", "claude", "kimi", "deepl"):
            settings = self.settings_repo.load()
            key_attr = f"{translator_id}_api_key"
            api_key = getattr(settings, key_attr, "")
            if not api_key:
                provider_display = {
                    "gemini": "Google Gemini",
                    "deepseek": "DeepSeek",
                    "openai": "OpenAI",
                    "claude": "Anthropic Claude",
                    "kimi": "Kimi Moonshot",
                    "deepl": "DeepL",
                }.get(translator_id, translator_id.upper())
                return {
                    "status": "error",
                    "error": f"API Key for {provider_display} is not configured. Please configure it in AI Hub (Settings) before starting.",
                    "code": "toast.no_ai_key",
                    "params": {"provider": provider_display}
                }

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Nạp glossary của game vào TranslationMemory khi chính thức khởi chạy/dịch
        if getattr(profile, "glossary", None):
            try:
                from atm.core.translation.translation_memory import TranslationMemory
                items = [{"source_text": k, "translated_text": v} for k, v in profile.glossary.items() if k and v]
                if items:
                    TranslationMemory().batch_remember(
                        items,
                        source_lang=profile.input_lang or "auto",
                        target_lang=profile.output_lang or "vi",
                        category="glossary",
                        source="user",
                        confidence="confirmed",
                    )
            except Exception as e:
                logger.warning(f"Failed to sync glossary to TranslationMemory on start_game: {e}")
        
        # For offline engines (RPG Maker, RenPy):
        # If user stopped translation earlier and quickly clicked Start/Resume,
        # the previous thread may still be running its graceful teardown (saving partial progress).
        # We safely wait for it to finish before starting a new translation thread.
        if profile.engine in ("RPG Maker", "RenPy"):
            old_thread = None
            is_cancelled_old = False
            with self._lock:
                old_thread = self.translation_threads.get(game_id)
                is_cancelled_old = self.cancel_flags.get(game_id, False)

            if old_thread and old_thread.is_alive():
                if is_cancelled_old:
                    logger.info(f"Waiting for previously cancelled translation thread of {game_id} to terminate...")
                    old_thread.join(timeout=5.0)
                    if old_thread.is_alive():
                        logger.warning(f"Previous translation thread for {game_id} did not terminate within timeout.")
                        return {"status": "busy", "message": "Previous translation is still shutting down, please wait a moment.", "code": "toast.game_busy"}
                else:
                    return {"status": "translating", "message": "Already translating"}

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
                    is_err = code in ("translation.failed", "translation.rate_limited")
                    is_done = (current >= total) or is_err
                    with self._lock:
                        self.translation_status[game_id] = {
                            "progress": current, 
                            "total": total, 
                            "code": code,
                            "params": params or {},
                            "done": is_done,
                            "error": is_err
                        }
                    if current % 10 == 0 or is_done:
                        self.job_repo.save(TranslationJob(
                            game_id=game_id,
                            status="failed" if is_err else ("completed" if is_done else "running"),
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
                        game_dir = self._get_game_dir(profile)
                        marker_path = os.path.join(game_dir, '.atm_translated') if game_dir else ""
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
                            try:
                                deployer.deploy_and_launch(profile, None)
                            except Exception as e:
                                logger.error(f"Failed to auto-launch {game_id}: {e}")
                                with self._lock:
                                    self.translation_status[game_id] = {
                                        "progress": 0, "total": 1, 
                                        "code": "translation.failed", 
                                        "params": {"error": str(e)},
                                        "done": True, 
                                        "error": True
                                    }
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
                finally:
                    with self._lock:
                        if self.translation_threads.get(game_id) == threading.current_thread():
                            self.translation_threads.pop(game_id, None)

            t = threading.Thread(target=run_offline_translate, daemon=True)
            with self._lock:
                self.translation_threads[game_id] = t
            t.start()
            return {"status": "translating"}
            
        if profile.engine in ("Unity Mono", "Unity IL2CPP"):
            folder_path = self._get_game_dir(profile)
            if not all(ord(c) < 128 for c in folder_path):
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
            return {"status": "error", "error": "Unsupported engine: " + profile.engine, "code": "error.engine_not_supported"}

        deployer = GameDeployer()
        with self._lock:
            self.active_deployers[game_id] = deployer
        
        # Deploy và Launch (chạy background) - wrapped so crashes don't ghost the game state
        def _run_unity_deploy():
            try:
                deployer.deploy_and_launch(profile, payload_dir)
                if deployer.monitor and deployer.monitor.monitor_thread:
                    deployer.monitor.monitor_thread.join()
            except Exception as e:
                logger.error(f"Unity deployer crashed for {game_id}: {e}", exc_info=True)
                with self._lock:
                    self.translation_status[game_id] = {
                        "progress": 0, "total": 1,
                        "code": "translation.failed",
                        "params": {"error": str(e)},
                        "done": True, "error": True
                    }
            finally:
                # Always clean up, even on crash - prevents permanent TRANSLATING ghost state
                with self._lock:
                    if self.active_deployers.get(game_id) == deployer:
                        self.active_deployers.pop(game_id, None)
                self._invalidate_fingerprint_cache(game_id)

        t = threading.Thread(target=_run_unity_deploy, daemon=True)
        t.start()
        return {"status": "success"}

    def translate_unity_text(self, text: str, from_lang: str = "auto", to_lang: str = "vi", game_id: str = None) -> str:
        """Local Gateway endpoint xử lý yêu cầu dịch thời gian thực từ XUnity CustomTranslate."""
        if not text or not text.strip():
            return text

        # 1. Tìm profile của game đang chạy (ưu tiên theo game_id định danh)
        active_profile = None
        with self._lock:
            if game_id:
                active_profile = self.profile_repo.get_by_id(game_id)
            if not active_profile:
                for g_id, dep in self.active_deployers.items():
                    target_id = getattr(dep, "current_game_id", None) or g_id
                    active_profile = self.profile_repo.get_by_id(target_id)
                    if active_profile:
                        break

        source_lang = from_lang or (active_profile.input_lang if active_profile else "auto") or "auto"
        target_lang = to_lang or (active_profile.output_lang if active_profile else "vi") or "vi"

        # 2. Kiểm tra Glossary riêng của game TRƯỚC TIÊN (Game Glossary Priority)
        if active_profile and hasattr(active_profile, "glossary") and isinstance(active_profile.glossary, dict):
            glossary_val = active_profile.glossary.get(text)
            
            if not glossary_val:
                cache_valid = (
                    hasattr(active_profile, "_lower_glossary") and 
                    getattr(active_profile, "_last_glossary_id", None) == id(active_profile.glossary) and
                    getattr(active_profile, "_last_glossary_len", -1) == len(active_profile.glossary)
                )
                if not cache_valid:
                    try:
                        active_profile._lower_glossary = {k.lower(): v for k, v in active_profile.glossary.items() if isinstance(k, str)}
                        active_profile._last_glossary_id = id(active_profile.glossary)
                        active_profile._last_glossary_len = len(active_profile.glossary)
                    except RuntimeError:
                        pass # Concurrently modified (e.g., term deleted by UI). Skip rebuild this frame.
                
                if hasattr(active_profile, "_lower_glossary"):
                    glossary_val = active_profile._lower_glossary.get(text.lower())
                        
            if glossary_val and isinstance(glossary_val, str) and glossary_val.strip():
                try:
                    from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
                    from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
                    gl_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
                    gl_repo.insert_or_ignore(
                        game_id=active_profile.id,
                        original=text,
                        translated=glossary_val,
                        category="glossary",
                        source_file="Unity_Runtime [Glossary]"
                    )
                except Exception as ge:
                    logger.debug(f"Failed to record unity runtime glossary line in game_lines: {ge}")
                return glossary_val

        # 3. Kiểm tra Cache toàn cục (O(1))
        from atm.core.translation.cache_manager import TranslationCache
        cache = TranslationCache()
        cached = cache.get(source_lang, target_lang, text, category="dialogue")
        if not cached:
            cached = cache.get(source_lang, target_lang, text, category="default")
        if cached:
            return cached

        # 4. Xác định Translator phù hợp
        translator_id = (getattr(active_profile, "translator", "google") if active_profile else "google") or "google"
        translator = None
        settings = self.settings_repo.load()

        if translator_id in ("gemini", "deepseek", "openai", "claude", "kimi", "custom_llm"):
            from atm.core.translation.translators import LLMTranslator
            api_key = getattr(settings, f"{translator_id}_api_key", "")
            base_url = getattr(settings, f"{translator_id}_base_url", "")
            model = getattr(settings, f"{translator_id}_model", "")
            glossary = getattr(active_profile, "glossary", {}) if active_profile else {}
            translator = LLMTranslator(
                provider=translator_id,
                api_key=api_key,
                base_url=base_url,
                model=model,
                glossary=glossary
            )
        elif translator_id == "deepl":
            from atm.core.translation.translators import DeepLTranslator
            translator = DeepLTranslator(api_key=settings.deepl_api_key)
        else:
            from atm.core.translation.translators import GoogleTranslator
            translator = GoogleTranslator()

        # 5. Dịch câu
        glossary_maps = {}
        if translator_id not in ("gemini", "deepseek", "openai", "claude", "kimi", "custom_llm") and active_profile and getattr(active_profile, "glossary", None):
            try:
                from atm.core.translation.pipeline import protect_glossary_terms, restore_glossary_terms
                text, glossary_maps = protect_glossary_terms(text, active_profile.glossary)
            except Exception as e:
                logger.debug(f"Failed to protect glossary terms: {e}")

        try:
            results = translator.translate_batch([text], target_lang, source_lang, category="dialogue", is_realtime=True)
            if results and results[0]:
                translated = results[0]
                if glossary_maps:
                    try:
                        from atm.core.translation.pipeline import restore_glossary_terms
                        translated = restore_glossary_terms(translated, glossary_maps)
                    except Exception as e:
                        logger.debug(f"Failed to restore glossary terms: {e}")
                        
                cache.set(source_lang, target_lang, text, translated, category="dialogue")
                if active_profile:
                    try:
                        from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
                        from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
                        gl_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
                        gl_repo.insert_or_ignore(
                            game_id=active_profile.id,
                            original=text,
                            translated=translated,
                            category="dialogue",
                            source_file=f"Unity_Runtime [{translator_id}]"
                        )
                    except Exception as ge:
                        logger.debug(f"Failed to record unity runtime line in game_lines: {ge}")
                return translated
        except Exception as e:
            logger.error(f"Error translating unity text '{text[:30]}...': {e}")

        # 6. Fallback sang Google Translator nếu LLM thất bại (có ghi provenance)
        try:
            from atm.core.translation.translators import GoogleTranslator
            fb = GoogleTranslator()
            fb_res = fb.translate_batch([text], target_lang, source_lang, category="dialogue", is_realtime=True)
            if fb_res and fb_res[0]:
                cache.set(source_lang, target_lang, text, fb_res[0], category="dialogue")
                if active_profile:
                    try:
                        from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
                        from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
                        gl_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
                        gl_repo.insert_or_ignore(
                            game_id=active_profile.id,
                            original=text,
                            translated=fb_res[0],
                            category="dialogue",
                            source_file=f"Unity_Runtime [{translator_id}_fallback_to_google]"
                        )
                    except Exception as ge:
                        logger.debug(f"Failed to record unity runtime fallback line in game_lines: {ge}")
                return fb_res[0]
        except Exception:
            pass

        return text


    def fix_unicode_path(self, game_id: str):
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found", "code": "error.game_not_found"}
            
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
        safe_game_name = slugify(profile.game_name)
        new_dir_name = safe_game_name if safe_game_name and safe_game_name != "Game" else f"Game_{game_id[:8]}"
            
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
        new_exe_name = new_dir_name + ".exe"
            
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
                    count = 0
                    try:
                        from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
                        from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
                        gl_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
                        count = gl_repo.count_by_game(game_id)
                    except Exception:
                        pass
                    return {
                        "progress": 50,
                        "total": 100,
                        "code": "translation.realtime_running",
                        "translated_lines": count,
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
            return {"status": "error", "error": "Game not found", "code": "error.game_not_found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang).", "code": "error.target_lang_missing"}
            
        logger.info(f"Syncing translation data for game: {game_id}")
        
        # Xác nhận nạp glossary của game vào TranslationMemory khi người dùng bấm Đồng bộ
        if getattr(profile, "glossary", None):
            try:
                from atm.core.translation.translation_memory import TranslationMemory
                items = [{"source_text": k, "translated_text": v} for k, v in profile.glossary.items() if k and v]
                if items:
                    TranslationMemory().batch_remember(
                        items,
                        source_lang=profile.input_lang or "auto",
                        target_lang=profile.output_lang or "vi",
                        category="glossary",
                        source="user",
                        confidence="confirmed",
                    )
                    logger.info(f"Committed {len(items)} glossary terms to TranslationMemory on sync for {profile.game_name}")
            except Exception as e:
                logger.warning(f"Failed to sync glossary to TranslationMemory on sync_game: {e}")
        
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
                
                # Ensure the thread is completely dead before clearing the cancel flag.
                # If we clear the flag while the thread is still saving teardown data, 
                # it will skip the graceful cancellation block and mark itself as 'failed'.
                old_thread = self.translation_threads.get(game_id)
                if old_thread and old_thread.is_alive():
                    old_thread.join(timeout=5.0)
                
                # Restart it to apply glossary
                logger.info(f"[Smart Sync] Restarting offline thread for {game_id} to apply new Glossary/Cache...")
                with self._lock:
                    self.cancel_flags[game_id] = False
                res = self.start_game(game_id, auto_launch=True)
                if res.get("status") == "error":
                    return res
                return {"status": "success", "message": "Smart re-scan triggered for offline engine.", "is_running": True}
            else:
                logger.info(f"[Smart Sync] Triggering re-scan for completed offline game {game_id}...")
                with self._lock:
                    self.cancel_flags[game_id] = False
                res = self.start_game(game_id, auto_launch=False)
                if res.get("status") == "error":
                    return res
                return {"status": "success", "message": "Applying new translations to game files...", "is_running": True}
                
        # 2. Nếu là game Unity -> Đổ file Cache xuống ổ cứng cho BepInEx
        elif profile.engine in ("Unity Mono", "Unity IL2CPP"):
            logger.info(f"[Smart Sync] Writing updated cache to BepInEx for {game_id}...")
            try:
                game_dir = self._get_game_dir(profile)
                lang = profile.output_lang or "vi"
                trans_dir = os.path.join(game_dir, "BepInEx", "Translation", lang, "Text")
                os.makedirs(trans_dir, exist_ok=True)
                trans_file = os.path.join(trans_dir, "_AutoGeneratedTranslations.txt")
                subs_file = os.path.join(trans_dir, "_Substitutions.txt")
                
                # Fetch dictionary and translations
                glossary = profile.glossary or {}
                repo = self._get_game_lines_repo()
                lines = repo.get_all_by_game(game_id)
                
                # Combine them (Glossary takes precedence for EXACT match)
                combined = {**lines, **glossary}
                
                with open(trans_file, 'w', encoding='utf-8-sig') as f:
                    for k, v in combined.items():
                        # Basic escaping for BepInEx
                        safe_k = str(k).replace('\n', '\\n').replace('\r', '\\r')
                        safe_v = str(v).replace('\n', '\\n').replace('\r', '\\r')
                        f.write(f"{safe_k}={safe_v}\n")
                        
                with open(subs_file, 'w', encoding='utf-8-sig') as f:
                    for k, v in glossary.items():
                        # Basic escaping for BepInEx
                        safe_k = str(k).replace('\n', '\\n').replace('\r', '\\r')
                        safe_v = str(v).replace('\n', '\\n').replace('\r', '\\r')
                        f.write(f"{safe_k}={safe_v}\n")
                        
                return {"status": "success", "message": "Cache & Glossary injected into Unity Engine. Press Alt+T in game to reload.", "is_running": False}
            except Exception as e:
                logger.error(f"Failed to sync Unity cache: {e}", exc_info=True)
                return {"status": "error", "error": f"Failed to write cache: {e}"}
        
        return {"status": "success", "message": "Glossary and Cache synced successfully", "is_running": False}

    def play_game(self, game_id, vanilla: bool = False):
        """Khởi chạy game đã dịch hoặc bản gốc (detached process)"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game profile not found", "code": "error.game_not_found"}

        with self._lock:
            # Prevent launching if the game is currently translating
            is_running_deployer = (
                game_id in getattr(self, "active_deployers", {})
                and (
                    getattr(self.active_deployers[game_id], "is_deploying", False)
                    or getattr(self.active_deployers[game_id].monitor, "is_monitoring", False)
                )
            )
            is_running_offline = (
                game_id in getattr(self, "translation_status", {})
                and not self.translation_status[game_id].get("done", True)
            )
            is_running_thread = (
                game_id in getattr(self, "translation_threads", {})
                and self.translation_threads[game_id].is_alive()
            )
            if is_running_offline or is_running_thread or is_running_deployer:
                return {
                    "status": "error",
                    "error": "Game is currently translating. Please wait or stop translation before playing.",
                    "code": "toast.game_translating"
                }

        if not profile.exe_path or not os.path.isfile(profile.exe_path):
            return {
                "status": "error",
                "error": f"Executable not found: {profile.exe_path}",
                "code": "error.exe_not_found"
            }

        # Unity games must be deployed with BepInEx when played with translations
        if not vanilla and profile.engine in ("Unity Mono", "Unity IL2CPP"):
            return self.start_game(game_id, auto_launch=True)

        game_dir = self._get_game_dir(profile)
        marker_path = os.path.join(game_dir, '.atm_translated') if game_dir else ""
        if marker_path and not os.path.exists(marker_path):
            logger.info(f"Playing game {game_id} in vanilla/partial state (.atm_translated marker not found)")

        # RPG Maker Safety Guard: ensure missing ATM_Overlay.js doesn't cause game crash
        if profile.engine == "RPG Maker" and game_dir:
            for pjs in [os.path.join(game_dir, "www", "js", "plugins.js"), os.path.join(game_dir, "js", "plugins.js")]:
                if os.path.exists(pjs):
                    plugin_file = os.path.join(os.path.dirname(pjs), "plugins", "ATM_Overlay.js")
                    if not os.path.exists(plugin_file):
                        try:
                            with open(pjs, "r", encoding="utf-8-sig") as pf:
                                p_content = pf.read()
                            if "ATM_Overlay" in p_content:
                                import re, json
                                match = re.search(r'(?s)var\s+\$plugins\s*=\s*(\[.*\])\s*;', p_content)
                                if match:
                                    arr = json.loads(match.group(1))
                                    clean_arr = [x for x in arr if x.get("name") != "ATM_Overlay"]
                                    new_p_content = p_content[:match.start(1)] + json.dumps(clean_arr, indent=0, ensure_ascii=False) + p_content[match.end(1):]
                                    with open(pjs, "w", encoding="utf-8-sig") as pf:
                                        pf.write(new_p_content)
                                    logger.info(f"[Play Game Guard] Cleaned missing ATM_Overlay from {pjs}")
                        except Exception as ge:
                            logger.error(f"[Play Game Guard] Failed to check/clean plugins.js: {ge}")

        try:
            import subprocess
            popen_kwargs = {"cwd": game_dir, "close_fds": True}
            if os.name == 'nt':
                DETACHED_PROCESS = 0x00000008
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                popen_kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            else:
                popen_kwargs["start_new_session"] = True
            subprocess.Popen([profile.exe_path], **popen_kwargs)
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Failed to play game {game_id}: {e}")
            return {"status": "error", "error": str(e)}

    def get_delete_info(self, game_id):
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found"}
            
        size_bytes = 0
        
        # 1. Estimate SQLite DB size for this game
        try:
            from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
            from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
            db_path = os.path.join(TRANSLATIONS_DIR, "translation_cache.db")
            if os.path.exists(db_path):
                repo = SQLiteGameLinesRepository(db_path)
                with repo._get_connection() as conn:
                    cursor = conn.cursor()
                    # Rough estimate: length of original and translated strings + 100 bytes overhead per row
                    cursor.execute("SELECT COUNT(*) FROM game_lines WHERE game_id = ?", (game_id,))
                    game_count = cursor.fetchone()[0] or 0
                    if game_count > 0:
                        cursor.execute("SELECT COUNT(*) FROM game_lines")
                        total_count = cursor.fetchone()[0] or 1
                        total_size = os.path.getsize(db_path)
                        wal_path = db_path + "-wal"
                        if os.path.exists(wal_path):
                            total_size += os.path.getsize(wal_path)
                        # Proportional size based on row count
                        size_bytes += int((game_count / total_count) * total_size)
        except Exception as e:
            logger.debug(f"Error calculating DB size: {e}")
            
        # 2. Metadata folder size
        try:
            from atm.storage.repositories.translation_repository import TranslationRepository
            repo = TranslationRepository()
            game_dir = repo.get_game_translation_dir(profile.game_name)
            if os.path.exists(game_dir):
                for dirpath, _, filenames in os.walk(game_dir):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if not os.path.islink(fp):
                            size_bytes += os.path.getsize(fp)
        except Exception as e:
            logger.debug(f"Error calculating folder size: {e}")
            
        size_mb = size_bytes / (1024 * 1024)
        return {"status": "success", "size_mb": round(size_mb, 2)}

    def delete_game(self, game_id, purge_data=False):
        """Xóa game profile (cả file JSON) và tùy chọn xóa sạch data"""
        try:
            # Check if running and wait for it to stop
            with self._lock:
                if game_id in self.active_deployers:
                    dep = self.active_deployers[game_id]
                    if not getattr(dep, "is_deploying", False) and not dep.monitor.is_monitoring:
                        del self.active_deployers[game_id]
                
                is_running_offline = game_id in self.translation_status and not self.translation_status[game_id].get("done", True)
                is_running_unity = game_id in self.active_deployers
                old_thread = self.translation_threads.get(game_id)
                is_cancelled = self.cancel_flags.get(game_id, False)
            
            if is_running_offline and is_cancelled and old_thread and old_thread.is_alive():
                logger.info(f"[Delete] Waiting for cancelled translation thread of {game_id} to terminate...")
                old_thread.join(timeout=5.0)
                with self._lock:
                    is_running_offline = game_id in self.translation_status and not self.translation_status[game_id].get("done", True)

            if is_running_offline or is_running_unity:
                return {"status": "error", "error": "Game is currently running or translating. Please stop it before deleting.", "code": "toast.delete_running_error"}
            
            profile = self.profile_repo.get_by_id(game_id)
            game_dir = None
            if profile:
                if getattr(profile, "path", None) and os.path.isdir(profile.path):
                    game_dir = profile.path
                elif getattr(profile, "exe_path", None):
                    parent = os.path.dirname(profile.exe_path)
                    if os.path.isdir(parent):
                        game_dir = parent
            
            if game_dir and os.path.isdir(game_dir):
                marker_file = os.path.join(game_dir, ".atm_translated")
                if os.path.exists(marker_file):
                    try: os.remove(marker_file)
                    except Exception: pass
                    
            # 1. Khôi phục thư mục game về nguyên bản (Revert external state)
            try:
                self._revert_game_directory(profile, game_dir)
            except Exception as revert_err:
                logger.error(f"Error reverting game directory for {game_id}: {revert_err}")

            # 2. Xóa toàn bộ dữ liệu của game (Internal State) nếu purge_data = True
            if purge_data:
                try:
                    self._clear_game_full_internal(game_id, profile)
                except Exception as e:
                    logger.error(f"Error clearing full game data on delete: {e}")
            else:
                logger.info(f"Retaining translation data for {game_id} (purge_data=False).")

            # 3. Xóa job repository file nếu có
            try:
                self.job_repo.delete(game_id)
            except Exception: pass

            # 4. Xóa bảng ID profile
            if purge_data:
                deleted = self.profile_repo.delete(game_id)
            else:
                profile.is_deleted = True
                self.profile_repo.save(profile)
                deleted = True

            # Dọn các file profile cũ
            from atm.utils.paths import get_profiles_dir
            profiles_dir = get_profiles_dir()
            if os.path.isdir(profiles_dir):
                for f in os.listdir(profiles_dir):
                    if f.endswith(".json"):
                        fpath = os.path.join(profiles_dir, f)
                        try:
                                logger.info(f"Cleaned old profile file: {f}")
                        except Exception:
                            pass

            logger.info(f"Deleted game: {game_id}")
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return {"status": "error", "error": str(e)}

    def _revert_game_directory(self, profile, game_dir):
        if not profile or not game_dir or not os.path.isdir(game_dir): return
        import shutil
        engine = getattr(profile, "engine", "")
        if engine == "RPG Maker":
            candidates = [
                (os.path.join(game_dir, "www", "data"), os.path.join(game_dir, "www", "data_backup")),
                (os.path.join(game_dir, "data"), os.path.join(game_dir, "data_backup")),
            ]
            for data_dir, backup_dir in candidates:
                if os.path.isdir(backup_dir):
                    try:
                        if os.path.isdir(data_dir): shutil.rmtree(data_dir)
                        shutil.copytree(backup_dir, data_dir)
                        shutil.rmtree(backup_dir)
                    except Exception: pass
            for p in [os.path.join(game_dir, "www", "js", "plugins", "ATM_Overlay.js"), os.path.join(game_dir, "js", "plugins", "ATM_Overlay.js")]:
                if os.path.exists(p):
                    try: os.remove(p)
                    except: pass
            for o in [os.path.join(game_dir, "www", "data", "ATM_Overlay.json"), os.path.join(game_dir, "data", "ATM_Overlay.json")]:
                if os.path.exists(o):
                    try: os.remove(o)
                    except: pass
            # Unpatch plugins.js
            for plugins_js in [os.path.join(game_dir, "www", "js", "plugins.js"), os.path.join(game_dir, "js", "plugins.js")]:
                if os.path.exists(plugins_js):
                    try:
                        with open(plugins_js, "r", encoding="utf-8-sig") as pf:
                            p_content = pf.read()
                        if "ATM_Overlay" in p_content:
                            import re, json
                            match = re.search(r'(?s)var\s+\$plugins\s*=\s*(\[.*\])\s*;', p_content)
                            if match:
                                plugins_arr = json.loads(match.group(1))
                                clean_arr = [x for x in plugins_arr if x.get("name") != "ATM_Overlay"]
                                new_content = p_content[:match.start(1)] + json.dumps(clean_arr, indent=0, ensure_ascii=False) + p_content[match.end(1):]
                                with open(plugins_js, "w", encoding="utf-8-sig") as pf:
                                    pf.write(new_content)
                                logger.info(f"[Revert] Successfully removed ATM_Overlay from {plugins_js}")
                    except Exception as pe:
                        logger.error(f"[Revert] Failed to unpatch {plugins_js}: {pe}")
        elif engine == "RenPy":
            output_lang = getattr(profile, "output_lang", "vi")
            for d in [os.path.join(game_dir, "game", "tl", output_lang), os.path.join(game_dir, "game", "tl", f"atm_{output_lang}")]:
                if os.path.isdir(d):
                    try: shutil.rmtree(d)
                    except: pass

    def _clear_game_full_internal(self, game_id: str, profile):
        try:
            from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
            from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
            from atm.core.translation.cache_manager import TranslationCache
            game_lines_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
            deleted_originals = game_lines_repo.clear_by_game(game_id, keep_count=0)
            if deleted_originals:
                TranslationCache().batch_delete_exact(deleted_originals)
                try:
                    from atm.core.translation.translation_memory import TranslationMemory
                    TranslationMemory().batch_forget(deleted_originals)
                except: pass
        except: pass
        
        glossary_terms = list((profile.glossary or {}).keys())
        if glossary_terms:
            try:
                from atm.core.translation.translation_memory import TranslationMemory
                TranslationMemory().batch_forget(glossary_terms, category="glossary")
            except: pass
                
        from atm.storage.repositories.translation_repository import TranslationRepository
        game_metadata_dir = TranslationRepository().get_game_translation_dir(profile.game_name)
        if os.path.exists(game_metadata_dir):
            import shutil
            try: shutil.rmtree(game_metadata_dir)
            except OSError: pass

    def clear_game_full(self, game_id: str):
        profile = self.profile_repo.get_by_id(game_id)
        if profile:
            self._clear_game_full_internal(game_id, profile)
        return {"status": "success"}

    def _get_game_lines_repo(self):
        from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
        from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
        return SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))

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
                # Add to TM and Cache
                profile = self.profile_repo.get_by_id(game_id)
                if profile and profile.output_lang:
                    from atm.core.translation.translation_memory import TranslationMemory
                    from atm.core.translation.cache_manager import TranslationCache
                    tm = TranslationMemory()
                    cache = TranslationCache()
                    sl, tl = profile.input_lang or "auto", profile.output_lang
                    try:
                        tm.remember(item["original"], translated, sl, tl, category="user")
                        cache.set(sl, tl, item["original"], translated, category=TranslationCache.MANUAL_CATEGORY)
                        cache.save_to_disk()
                    except Exception as e:
                        logger.error(f"Failed to update cache/TM: {e}")
                return {"status": "success", "version": expected_version + 1}
            else:
                current_item = repo.get_by_id(item_id)
                return {"status": "conflict", "server_state": current_item, "code": 409}
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
            
            # Sync to TM and Global Cache for successful ones
            if result.get("saved"):
                profile = self.profile_repo.get_by_id(game_id)
                if profile and profile.output_lang:
                    from atm.core.translation.translation_memory import TranslationMemory
                    from atm.core.translation.cache_manager import TranslationCache
                    tm = TranslationMemory()
                    cache = TranslationCache()
                    sl, tl = profile.input_lang or "auto", profile.output_lang
                    try:
                        tm_items = [
                            {"source_text": s["original"], "translated_text": s["translated"]}
                            for s in result["saved"]
                            if s.get("original") and s.get("translated")
                        ]
                        if tm_items:
                            tm.batch_remember(tm_items, sl, tl, category="user")
                        
                        texts = [s["original"] for s in result["saved"] if s.get("original") and s.get("translated")]
                        translations = [s["translated"] for s in result["saved"] if s.get("original") and s.get("translated")]
                        if texts:
                            cache.set_batch(sl, tl, texts, translations, category=TranslationCache.MANUAL_CATEGORY)
                    except Exception as e:
                        logger.error(f"Failed to batch cache items: {e}")
                                
            return {"status": "success", "data": result}
        except Exception as e:
            logger.error(f"Failed to batch update translations: {e}")
            return {"status": "error", "error": str(e)}

    def review_qa(self, entries):
        """Quét lỗi QA trên một batch entries"""
        try:
            from atm.core.qa.registry import QARuleRegistry
            from atm.core.qa.engine import QAEngine
            from atm.utils.paths import get_qa_dir
            
            if not isinstance(entries, list):
                return {"status": "error", "error": "Entries must be a list", "code": "error.invalid_payload"}

            qa_dir = get_qa_dir()
            sys_rules = os.path.join(qa_dir, "system_rules.json")
            user_rules = os.path.join(qa_dir, "user_rules.json")
            
            registry = QARuleRegistry(sys_rules, user_rules)
            engine = QAEngine(registry)
            
            results = engine.review_batch(entries)
            return {"status": "success", "data": results}
        except Exception as e:
            logger.error(f"Failed to review QA: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

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
            return {"status": "error", "error": "Game not found", "code": "error.game_not_found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang).", "code": "error.target_lang_missing"}
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
                    
                # Xóa thuật ngữ khỏi Global Translation Memory
                try:
                    from atm.core.translation.translation_memory import TranslationMemory
                    TranslationMemory().forget(term, category="glossary")
                except Exception as tme:
                    logger.warning(f"Failed to remove term '{term}' from TranslationMemory: {tme}")
                    
        return {"status": "success"}

    def delete_glossary_terms(self, game_id: str, terms: list):
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found", "code": "error.game_not_found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang).", "code": "error.target_lang_missing"}
        if hasattr(profile, "glossary") and isinstance(profile.glossary, dict):
            deleted_terms = []
            for term in terms:
                if term in profile.glossary:
                    del profile.glossary[term]
                    deleted_terms.append(term)
            
            if deleted_terms:
                self.profile_repo.save(profile)
                
                # Batch invalidate cache for deleted terms
                try:
                    from atm.core.translation.cache_manager import TranslationCache
                    cache = TranslationCache()
                    count = cache.batch_invalidate_by_terms(profile.input_lang or "auto", profile.output_lang, deleted_terms)
                    logger.info(f"Batch invalidated {count} cache entries for {len(deleted_terms)} terms")
                except Exception as e:
                    logger.error(f"Failed to batch invalidate cache: {e}")
                    
                # Forget from Translation Memory
                try:
                    from atm.core.translation.translation_memory import TranslationMemory
                    tm = TranslationMemory()
                    for term in deleted_terms:
                        tm.forget(term, category="glossary")
                except Exception as tme:
                    logger.warning(f"Failed to remove terms from TranslationMemory: {tme}")
                    
        return {"status": "success", "count": len(terms)}

    def update_cache_entry(self, game_id, key, value):
        """Cập nhật một mục trong Cache từ Grid Editor"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile: 
            return {"status": "error", "error": "Game not found", "code": "error.game_not_found"}
            
        source_lang = profile.input_lang
        target_lang = profile.output_lang
        if not target_lang:
            return {"status": "error", "error": "Target language not configured (output_lang).", "code": "error.target_lang_missing"}
            
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
            return {"status": "error", "error": "Game not found", "code": "error.game_not_found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang).", "code": "error.target_lang_missing"}
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
            return {"status": "error", "error": "Game not found", "code": "error.game_not_found"}
        if not profile.output_lang:
            return {"status": "error", "error": "Target language not configured (output_lang).", "code": "error.target_lang_missing"}
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

    def search_cache(self, q: str, page: int, limit: int):
        """Tìm kiếm trong Cache."""
        from atm.core.translation.cache_manager import TranslationCache
        cache = TranslationCache()
        result = cache.search(q, page, limit)
        return {"status": "success", "data": result}

    # --- Data Management Endpoints ---

    def get_data_stats(self):
        """Lấy thống kê dữ liệu cho Tab Quản lý Dữ liệu."""
        from atm.core.translation.cache_manager import TranslationCache
        from atm.core.translation.translation_memory import TranslationMemory

        cache = TranslationCache()
        memory = TranslationMemory()
        
        # Thống kê Global Cache (O(1) via SQL count)
        try:
            total_cache = cache.repo.count()
        except Exception:
            total_cache = 0
            
        # Checkpoint WAL to flush pending logs and keep reported cache size clean and stable
        wal_path = cache.db_path + "-wal"
        if os.path.exists(wal_path) and os.path.getsize(wal_path) > 0:
            try:
                import sqlite3
                conn = sqlite3.connect(cache.db_path, timeout=5.0, isolation_level=None)
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                conn.close()
            except Exception as e:
                logger.debug(f"WAL checkpoint non-critical error: {e}")

        try:
            cache_size = os.path.getsize(cache.db_path)
            if os.path.exists(wal_path):
                cache_size += os.path.getsize(wal_path)
        except OSError:
            cache_size = 0
            
        # Thống kê per-game lines
        try:
            from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
            from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
            game_lines_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
            game_lines_stats = { item["game_id"]: item["count"] for item in game_lines_repo.get_stats_by_game() }
        except Exception:
            game_lines_stats = {}

        profiles = self.profile_repo.get_all()
        known_game_ids = set()
        total_glossary_count = 0
        games_stats = []
        for p in profiles:
            known_game_ids.add(p.id)
            count = game_lines_stats.get(p.id, 0)
            terms = len(p.glossary) if (hasattr(p, "glossary") and isinstance(p.glossary, dict)) else 0
            total_glossary_count += terms
            games_stats.append({
                "id": p.id,
                "name": p.game_name,
                "engine": p.engine,
                "folder": os.path.basename(os.path.dirname(p.exe_path)) if p.exe_path else "Unknown",
                "entries": count,
                "terms": terms
            })
            
        # Add orphaned game lines (games deleted from library but data remains)
        for g_id, count in game_lines_stats.items():
            if g_id not in known_game_ids and count > 0:
                games_stats.append({
                    "id": g_id,
                    "name": "Deleted Game (Orphaned Data)",
                    "engine": "Unknown",
                    "folder": g_id,
                    "entries": count,
                    "terms": 0
                })
            
        # Thống kê Global Memory (chỉ tính các mục đã được xác nhận/đồng bộ nạp vào TM)
        memory_entries = list(memory.entries())
        total_memory = len(memory_entries)
        try:
            memory_size = os.path.getsize(memory.repository.memory_file)
        except OSError:
            memory_size = 0

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
        """Xóa toàn bộ hoặc chừa lại keep_count câu cũ nhất trong Cache. Nếu keep_count <= 0 thì xóa sạch cả game_lines."""
        from atm.core.translation.cache_manager import TranslationCache
        cache = TranslationCache()
        should_clear_lines = (keep_count is None or keep_count <= 0)
        cache.clear(keep_count, clear_game_lines=should_clear_lines)
        logger.info(f"Cleared global cache. Kept: {keep_count if keep_count else 0} entries. (Lines cleared: {should_clear_lines})")
        return {"status": "success"}

    def clear_global_memory(self):
        """Xóa toàn bộ Global Translation Memory và Glossary của tất cả các game."""
        from atm.core.translation.translation_memory import TranslationMemory
        memory = TranslationMemory()
        memory.clear()
        
        # Reset glossary của toàn bộ các game
        profiles = self.profile_repo.get_all()
        for p in profiles:
            if hasattr(p, "glossary") and p.glossary:
                p.glossary = {}
                self.profile_repo.save(p)
                
        logger.info("Cleared global translation memory and all game glossaries.")
        return {"status": "success"}

    def clear_game_lines(self, game_id, keep_count=0, delete_from_cache=True):
        """Xóa dữ liệu game_lines cho một game cụ thể và tùy chọn xóa khỏi Global Cache."""
        try:
            from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
            from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
            from atm.core.translation.cache_manager import TranslationCache
            
            game_lines_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
            deleted_originals = game_lines_repo.clear_by_game(game_id, keep_count)
            
            if deleted_originals and delete_from_cache:
                cache = TranslationCache()
                cache.batch_delete_exact(deleted_originals)
                logger.info(f"Cleared {len(deleted_originals)} global cache entries for game {game_id}.")
                try:
                    from atm.core.translation.translation_memory import TranslationMemory
                    TranslationMemory().batch_forget(deleted_originals)
                except Exception as tme:
                    logger.warning(f"Failed to remove cleared lines from TM for {game_id}: {tme}")
                
            logger.info(f"Cleared game lines for {game_id}. Kept: {keep_count}")
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def clear_game_full(self, game_id: str):
        """Xóa toàn bộ dữ liệu của game: game_lines, glossary, cache và memory liên quan."""
        with self._lock:
            if game_id in self.translation_status and not self.translation_status[game_id].get("done", True):
                return {"status": "error", "error": "Cannot clear data while translation is running. Stop it first.", "code": "toast.clear_running_error"}
        
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game not found", "code": "error.game_not_found"}
            
        # 1. Xóa game lines và xóa khỏi global cache
        try:
            from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
            from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
            from atm.core.translation.cache_manager import TranslationCache
            
            game_lines_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
            deleted_originals = game_lines_repo.clear_by_game(game_id, keep_count=0)
            if deleted_originals:
                cache = TranslationCache()
                cache.batch_delete_exact(deleted_originals)
                try:
                    from atm.core.translation.translation_memory import TranslationMemory
                    TranslationMemory().batch_forget(deleted_originals)
                except Exception as tme:
                    logger.warning(f"Failed to remove game lines from TM for {game_id}: {tme}")
        except Exception as e:
            logger.error(f"Error clearing game lines for {game_id}: {e}")
            
        # 2. Xóa glossary và xóa thuật ngữ khỏi TranslationMemory
        glossary_terms = list((profile.glossary or {}).keys())
        profile.glossary = {}
        self.profile_repo.save(profile)
        
        if glossary_terms:
            try:
                from atm.core.translation.translation_memory import TranslationMemory
                TranslationMemory().batch_forget(glossary_terms, category="glossary")
            except Exception as e:
                logger.error(f"Error removing terms from TM for {game_id}: {e}")
                
        # 3. Xóa file metadata directory
        from atm.storage.repositories.translation_repository import TranslationRepository
        repo = TranslationRepository()
        game_dir = repo.get_game_translation_dir(profile.game_name)
        if os.path.exists(game_dir):
            import shutil
            try:
                shutil.rmtree(game_dir)
            except OSError:
                pass
                
        logger.info(f"Cleared all game data (lines + glossary) for {profile.game_name}.")
        return {"status": "success"}

    def clear_game_data(self, game_id):
        """Backward compatibility alias for clear_game_full."""
        return self.clear_game_full(game_id)

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
            game_dir = self._get_game_dir(profile)
            
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
            extractor = EngineRegistry.get_extractor(profile.engine, self._get_game_dir(profile))
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
            extractor = EngineRegistry.get_extractor(profile.engine, self._get_game_dir(profile))
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
            injector = EngineRegistry.get_injector(profile.engine, self._get_game_dir(profile))
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



 
