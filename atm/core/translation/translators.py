import urllib.request
import urllib.parse
import json
from typing import List, Dict, Optional
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class BaseTranslator:
    def translate_batch(self, texts: List[str], target_lang: str = "vi", source_lang: str = "auto") -> List[str]:
        raise NotImplementedError

class GoogleTranslator(BaseTranslator):
    def translate_batch(self, texts: List[str], target_lang: str = "vi", source_lang: str = "auto") -> List[str]:
        """Dịch từng đoạn text thông qua Google Translate (miễn phí, có thể bị rate limit)."""
        translated_texts = []
        for text in texts:
            if not text.strip():
                translated_texts.append(text)
                continue
                
            try:
                # Sử dụng API nội bộ hoặc thư viện nếu cần, tạm dùng fallback đơn giản
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    translated = "".join([sentence[0] for sentence in data[0]])
                    translated_texts.append(translated)
            except Exception as e:
                logger.error(f"Google translate error for text '{text[:20]}...': {e}")
                translated_texts.append(text) # Fallback to original
                
        return translated_texts

class DeepLTranslator(BaseTranslator):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.deepl.com/v2/translate"
        if api_key.endswith(":fx"):
            self.api_url = "https://api-free.deepl.com/v2/translate"

    def translate_batch(self, texts: List[str], target_lang: str = "VI", source_lang: Optional[str] = None) -> List[str]:
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
