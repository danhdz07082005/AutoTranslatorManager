import requests
from atm.plugins.translators.base_translator import BaseTranslator
from atm.utils.logger import get_logger

logger = get_logger(__name__, "translation.log")

class GooglePlugin(BaseTranslator):
    """
    Sử dụng Google Translate API (không chính thức) qua HTTP Request.
    Không cần tải thư viện nặng, chạy cực nhẹ và nhanh.
    """
    
    @property
    def plugin_id(self) -> str:
        return "google"
        
    def check_connection(self) -> bool:
        try:
            # Check ping tới Google
            response = requests.get("https://translate.googleapis.com/translate_a/single", timeout=3)
            return True
        except Exception:
            return False
            
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if source_lang == "auto":
            source_lang = "auto"
            
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
            "dt": "t",
            "q": text
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            # Google trả về một array phức tạp, phần dịch nằm ở [0][i][0]
            data = response.json()
            if not data or not isinstance(data, list):
                return text
                
            translated = "".join([sentence[0] for sentence in data[0] if sentence[0]])
            return translated
        except Exception as e:
            logger.error(f"Google Translate failed for text '{text}': {e}")
            return text
