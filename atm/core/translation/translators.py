import urllib.request
import urllib.parse
import json
import concurrent.futures
import time
import random
from collections import defaultdict
import urllib.request
import urllib.parse
import json
import concurrent.futures
import time
import random
from collections import defaultdict
from typing import Iterable, List, Optional, Tuple
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class BaseTranslator:
    def __init__(self):
        pass

    def translate_batch(
        self,
        texts: List[str],
        target_lang: str = "vi",
        source_lang: str = "auto",
        category: str = "unknown",
    ) -> List[str]:
        """Translate a batch of texts directly via network."""
        if not texts:
            return []

        try:
            results = self._do_translate_batch(texts, target_lang, source_lang)
            if results and len(results) == len(texts):
                return results
            else:
                logger.warning(f"Batch translate returned mismatch results count. Expected {len(texts)}, got {len(results) if results else 0}.")
                return [None] * len(texts)
        except Exception as e:
            logger.error(f"Error in _do_translate_batch: {e}")
            return [None] * len(texts)

    def translate_categorized(
        self,
        entries: Iterable[Tuple[str, str]],
        target_lang: str = "vi",
        source_lang: str = "auto",
    ) -> List[str]:
        """Translate ``(text, category)`` entries without mixing categories.

        Results preserve the supplied order.  The pipeline uses this boundary to
        keep short UI labels out of dialogue batches while retaining cache hits.
        """
        ordered_entries = list(entries)
        grouped: dict[str, list[tuple[int, str]]] = defaultdict(list)
        for index, (text, category) in enumerate(ordered_entries):
            grouped[category or "unknown"].append((index, text))

        results = ["" for _ in ordered_entries]
        for category, group in grouped.items():
            translated = self.translate_batch(
                [text for _, text in group],
                target_lang=target_lang,
                source_lang=source_lang,
                category=category,
            )
            for (index, original), translated_text in zip(group, translated):
                results[index] = translated_text if translated_text is not None else original
        return results

    def _do_translate_batch(self, texts: List[str], target_lang: str, source_lang: str) -> List[str]:
        raise NotImplementedError

class GoogleTranslator(BaseTranslator):
    # Giới hạn an toàn của Google Translate API (POST body)
    MAX_CHARS_PER_CHUNK = 4500
    MAX_TEXTS_PER_CHUNK = 25
    MAX_WORKERS = 1
    SLEEP_BETWEEN_CHUNKS = 2.0
    MAX_RETRIES = 4

    def _do_translate_batch(self, texts: List[str], target_lang: str = "vi", source_lang: str = "auto") -> List[Optional[str]]:
        """Dịch bằng cách gộp (join) nhiều câu thành chuỗi lớn, gửi 1 lần lên API."""
        translated_texts = list(texts)

        def translate_chunk_with_retry(chunk_texts):
            """Dịch 1 chunk với cơ chế retry khi bị 429 (exponential backoff)."""
            separator = "\n<br>\n"
            combined_text = separator.join(chunk_texts)

            for attempt in range(self.MAX_RETRIES):
                try:
                    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t"
                    data = f"q={urllib.parse.quote(combined_text)}".encode('utf-8')
                    req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        res_data = json.loads(response.read().decode('utf-8'))
                        translated = "".join([sentence[0] for sentence in res_data[0] if sentence[0]])
                        parts = [p.strip() for p in translated.split("<br>")]

                        if len(parts) == len(chunk_texts):
                            return parts
                        else:
                            logger.warning(f"Batch split mismatch: expected {len(chunk_texts)}, got {len(parts)}. Fallback.")
                            return [None] * len(chunk_texts)
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        wait = (10 * (2 ** attempt)) + random.uniform(0, 3)
                        logger.warning(f"HTTP 429 (Too Many Requests). Retry {attempt+1}/{self.MAX_RETRIES} in {wait:.1f}s...")
                        time.sleep(wait)
                    else:
                        logger.error(f"Google translate HTTP error {e.code}: {e}")
                        return [None] * len(chunk_texts)
                except Exception as e:
                    logger.error(f"Google translate batch error: {e}")
                    return [None] * len(chunk_texts)

            # Hết retry → trả nguyên gốc
            logger.error(f"Google translate: exhausted {self.MAX_RETRIES} retries for chunk of {len(chunk_texts)} texts.")
            return [None] * len(chunk_texts)

        # Tách mảng texts thành các chunk, mỗi chunk tối đa 4500 ký tự (bao gồm separator)
        chunks: list[list[tuple[int, str]]] = []
        current_chunk: list[tuple[int, str]] = []
        current_len = 0

        for i, text in enumerate(texts):
            if not text.strip():
                continue

            text_len = len(text)
            separator_len = 6 if current_chunk else 0  # "\n<br>\n" = 6 chars

            exceeds_char_limit = (
                current_len + text_len + separator_len > self.MAX_CHARS_PER_CHUNK
            )
            exceeds_count_limit = len(current_chunk) >= self.MAX_TEXTS_PER_CHUNK
            if (exceeds_char_limit or exceeds_count_limit) and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_len = 0

            current_chunk.append((i, text))
            current_len += text_len + separator_len

        if current_chunk:
            chunks.append(current_chunk)

        logger.info(
            "Packed %s texts into %s chunks (max %s chars / %s texts each).",
            len(texts),
            len(chunks),
            self.MAX_CHARS_PER_CHUNK,
            self.MAX_TEXTS_PER_CHUNK,
        )

        # Dịch từng chunk với ThreadPool
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = []
            for chunk in chunks:
                chunk_texts = [text for _, text in chunk]
                futures.append((chunk, executor.submit(translate_chunk_with_retry, chunk_texts)))
                time.sleep(self.SLEEP_BETWEEN_CHUNKS)

            for chunk, future in futures:
                res_parts = future.result()
                for (target_idx, _source_text), res_text in zip(chunk, res_parts):
                    translated_texts[target_idx] = res_text

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
