import urllib.request
import urllib.parse
import json
import concurrent.futures
import time
import random
from typing import List, Dict, Optional
from atm.utils.logger import get_logger
from atm.core.translation.cache_manager import TranslationCache

logger = get_logger(__name__, "launcher.log")

class BaseTranslator:
    def __init__(self):
        self.cache = TranslationCache()

    def translate_batch(self, texts: List[str], target_lang: str = "vi", source_lang: str = "auto") -> List[str]:
        if not texts:
            return []
            
        final_results = []
        uncached_texts = []
        uncached_indices = []

        # 1. Kiem tra cache
        for i, text in enumerate(texts):
            if not text.strip():
                final_results.append(text)
                continue
                
            cached_val = self.cache.get(source_lang, target_lang, text)
            if cached_val is not None:
                final_results.append(cached_val)
            else:
                final_results.append(None) # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)

        # 2. Goi API cho cac text chua co trong cache
        if uncached_texts:
            logger.info(f"Translating {len(uncached_texts)} uncached texts out of {len(texts)}...")
            try:
                translated_uncached = self._do_translate_batch(uncached_texts, target_lang, source_lang)
                
                # 3. Luu vao cache va ket qua final
                self.cache.set_batch(source_lang, target_lang, uncached_texts, translated_uncached)
                self.cache.save_to_disk()
                
                for i, idx in enumerate(uncached_indices):
                    if i < len(translated_uncached):
                        final_results[idx] = translated_uncached[i]
                    else:
                        final_results[idx] = uncached_texts[i] # Fallback neu API tra thieu
            except Exception as e:
                logger.error(f"Error in _do_translate_batch: {e}")
                for i, idx in enumerate(uncached_indices):
                    final_results[idx] = uncached_texts[i] # Fallback
                    
        return final_results

    def _do_translate_batch(self, texts: List[str], target_lang: str, source_lang: str) -> List[str]:
        raise NotImplementedError

class GoogleTranslator(BaseTranslator):
    def _do_translate_batch(self, texts: List[str], target_lang: str = "vi", source_lang: str = "auto") -> List[str]:
        """Dịch từng đoạn text thông qua Google Translate với Đa Luồng (Multithreading)."""
        translated_texts = list(texts)
        
        def translate_single(index, text):
            if not text.strip():
                return
            try:
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    translated = "".join([sentence[0] for sentence in data[0]])
                    translated_texts[index] = translated
            except Exception as e:
                logger.error(f"Google translate error for text '{text[:20]}...': {e}")
                # Fallback to original
                pass
                
        # Dùng ThreadPoolExecutor với max_workers = 3 để tránh Google chặn IP
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for i, t in enumerate(texts):
                futures.append(executor.submit(translate_single, i, t))
                time.sleep(0.3) # Rate limit cho an toàn
            concurrent.futures.wait(futures)
                
        return translated_texts

class DeepLTranslator(BaseTranslator):
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.api_url = "https://api.deepl.com/v2/translate"
        if api_key.endswith(":fx"):
            self.api_url = "https://api-free.deepl.com/v2/translate"

    def _do_translate_batch(self, texts: List[str], target_lang: str = "VI", source_lang: Optional[str] = None) -> List[str]:
        """Sử dụng DeepL API hỗ trợ mảng văn bản để tối ưu."""
        if not self.api_key:
            logger.warning("DeepL API Key is empty. Falling back to original texts.")
            return texts
            
        target_lang = target_lang.upper()
        if target_lang == "VI":
            # DeepL chưa hỗ trợ tiếng Việt chính thức, nhưng nếu hỗ trợ sau này thì code sẽ tự mở khóa
            pass
            
        data = {
            "text": texts,
            "target_lang": target_lang
        }
        if source_lang and source_lang != "auto":
            data["source_lang"] = source_lang.upper()

        try:
            req = urllib.request.Request(self.api_url, data=json.dumps(data).encode('utf-8'), headers={
                'Authorization': f'DeepL-Auth-Key {self.api_key}',
                'Content-Type': 'application/json'
            })
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                return [item["text"] for item in res_data.get("translations", [])]
        except Exception as e:
            logger.error(f"DeepL translate batch error: {e}")
            return texts
