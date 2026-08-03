import os
import json
import threading
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class TranslationCache:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TranslationCache, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.cache_file = os.path.join(base_dir, "data", "translation_cache.json")
        self.cache = {}
        self._cache_lock = threading.Lock()
        self._load()

    def _load(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
                self.cache = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def get(self, source_lang: str, target_lang: str, text: str) -> str:
        with self._cache_lock:
            return self.cache.get(source_lang, {}).get(target_lang, {}).get(text)

    def _enforce_limit(self, source_lang: str, target_lang: str, max_size: int = 50000):
        target_dict = self.cache.get(source_lang, {}).get(target_lang, {})
        if len(target_dict) > max_size:
            keys_to_delete = list(target_dict.keys())[:5000]
            for k in keys_to_delete:
                del target_dict[k]

    def set(self, source_lang: str, target_lang: str, text: str, translated: str):
        with self._cache_lock:
            if source_lang not in self.cache:
                self.cache[source_lang] = {}
            if target_lang not in self.cache[source_lang]:
                self.cache[source_lang][target_lang] = {}
            
            self.cache[source_lang][target_lang][text] = translated
            self._enforce_limit(source_lang, target_lang)

    def set_batch(self, source_lang: str, target_lang: str, texts: list, translated_texts: list):
        with self._cache_lock:
            if source_lang not in self.cache:
                self.cache[source_lang] = {}
            if target_lang not in self.cache[source_lang]:
                self.cache[source_lang][target_lang] = {}
                
            for i, text in enumerate(texts):
                if i < len(translated_texts):
                    self.cache[source_lang][target_lang][text] = translated_texts[i]
            
            self._enforce_limit(source_lang, target_lang)

    def save_to_disk(self):
        with self._cache_lock:
            self._save()