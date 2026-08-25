import urllib.request
import urllib.parse
import json
import concurrent.futures
import time
import random
import re
import threading
from collections import defaultdict
from typing import Iterable, List, Optional, Tuple
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class RateLimitError(Exception):
    """Exception raised when an API rate limit is hit and retries are exhausted."""
    pass

class BaseTranslator:
    def __init__(self):
        pass

    def translate_batch(
        self,
        texts: List[str],
        target_lang: str = "vi",
        source_lang: str = "auto",
        category: str = "unknown",
        is_cancelled = None,
        progress_callback = None,
    ) -> List[str]:
        if not texts:
            return []

        try:
            results = self._do_translate_batch(texts, target_lang, source_lang, category=category, is_cancelled=is_cancelled, progress_callback=progress_callback)
            if results and len(results) == len(texts):
                return results
            else:
                logger.warning(f"Batch translate returned mismatch results count. Expected {len(texts)}, got {len(results) if results else 0}.")
                return [None] * len(texts)
        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Error in _do_translate_batch (type: {type(e)}): {e}")
            return [None] * len(texts)

    def translate_categorized(
        self,
        entries: Iterable[Tuple[str, str]],
        target_lang: str = "vi",
        source_lang: str = "auto",
        is_cancelled = None,
        progress_callback = None,
    ) -> List[str]:
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
                is_cancelled=is_cancelled,
                progress_callback=progress_callback
            )
            for (index, original), translated_text in zip(group, translated):
                results[index] = translated_text
        return results

    def _do_translate_batch(self, texts: List[str], target_lang: str, source_lang: str, is_cancelled=None, progress_callback=None, **kwargs) -> List[str]:
        raise NotImplementedError

class GoogleTranslator(BaseTranslator):
    MAX_CHARS_PER_CHUNK = 3500
    MAX_TEXTS_PER_CHUNK = 50
    MAX_WORKERS = 1
    MIN_DELAY = 3.0
    MAX_DELAY = 15.0
    MAX_RETRIES = 5

    gtx_blocked_until = 0

    def _do_translate_batch(self, texts: List[str], target_lang: str = "vi", source_lang: str = "auto", is_cancelled=None, progress_callback=None, **kwargs) -> List[Optional[str]]:
        translated_texts = [None] * len(texts)
        error_event = threading.Event()

        def translate_chunk_with_retry(chunk_texts):
            if (is_cancelled and is_cancelled()) or error_event.is_set():
                return [None] * len(chunk_texts)

            separator = "\n<br>\n"
            combined_text = separator.join(chunk_texts)

            for attempt in range(self.MAX_RETRIES):
                try:
                    use_rpc = time.time() < GoogleTranslator.gtx_blocked_until
                    
                    if use_rpc:
                        rpc_data = json.dumps([[[
                            'MkEWBc',
                            json.dumps([[combined_text, source_lang, target_lang, True], [None]], separators=(',', ':')),
                            None,
                            'generic'
                        ]]], separators=(',', ':'))
                        url = "https://translate.google.com/_/TranslateWebserverUi/data/batchexecute"
                        data = urllib.parse.urlencode({'f.req': rpc_data}).encode('utf-8')
                        req = urllib.request.Request(url, data=data, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
                        })
                    else:
                        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t"
                        data = f"q={urllib.parse.quote(combined_text)}".encode('utf-8')
                        req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0'})
                    
                    with urllib.request.urlopen(req, timeout=30.0) as response:
                        res_text = response.read().decode('utf-8')
                        if use_rpc:
                            idx = res_text.find('\n')
                            if idx != -1: res_text = res_text[idx:]
                            parsed = json.loads(res_text)
                            translated = ""
                            for item in parsed:
                                if item[0] == 'wrb.fr' and item[1] == 'MkEWBc':
                                    inner = json.loads(item[2])
                                    trans_arr = inner[1][0][0][5]
                                    translated = "".join([part[0] for part in trans_arr if part[0]])
                                    break
                        else:
                            res_data = json.loads(res_text)
                            translated = "".join([sentence[0] for sentence in res_data[0] if sentence[0]])
                                
                        parts = [p.strip() for p in re.split(r'(?i)<\s*br\s*>', translated)]

                        if len(parts) == len(chunk_texts):
                            return parts
                        else:
                            logger.warning(f"Batch split mismatch: expected {len(chunk_texts)}, got {len(parts)}. Fallback.")
                            return [None] * len(chunk_texts)
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        if not use_rpc:
                            logger.warning("GTX blocked. Switching to RPC for 5 minutes.")
                            GoogleTranslator.gtx_blocked_until = time.time() + 300
                            continue
                        
                        wait = (10 * (2 ** attempt)) + random.uniform(0, 3)
                        logger.warning(f"HTTP 429 (Too Many Requests). Retry {attempt+1}/{self.MAX_RETRIES} in {wait:.1f}s...")
                        elapsed = 0
                        while elapsed < wait:
                            if (is_cancelled and is_cancelled()) or error_event.is_set():
                                logger.info("Translation cancelled or errored during wait.")
                                return [None] * len(chunk_texts)
                            time.sleep(min(1.0, wait - elapsed))
                            elapsed += 1.0
                    else:
                        logger.error(f"Google translate HTTP error {e.code}: {e}")
                        time.sleep(2.0)
                        continue # retry on other HTTP errors
                except Exception as e:
                    logger.error(f"Google translate batch error (Attempt {attempt+1}/{self.MAX_RETRIES}): {e}")
                    time.sleep(2.0)
                    continue # retry on network drop or JSON parsing errors

            logger.error(f"Google translate: exhausted {self.MAX_RETRIES} retries for chunk of {len(chunk_texts)} texts.")
            error_event.set()
            raise RateLimitError("Google Translation API rate limit exceeded (HTTP 429).")

        chunks: list[list[tuple[int, str]]] = []
        current_chunk: list[tuple[int, str]] = []
        current_len = 0

        for i, text in enumerate(texts):
            if not text.strip():
                continue

            text_len = len(text)
            separator_len = 6 if current_chunk else 0

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

        for chunk in chunks:
            if (is_cancelled and is_cancelled()) or error_event.is_set():
                break
            
            chunk_texts = [text for _, text in chunk]
            res_parts = translate_chunk_with_retry(chunk_texts)
            
            if res_parts and None not in res_parts:
                if progress_callback:
                    progress_callback(len(chunk))
            
            for (target_idx, _source_text), res_text in zip(chunk, res_parts):
                translated_texts[target_idx] = res_text
            
            elapsed = 0
            sleep_time = random.uniform(self.MIN_DELAY, self.MAX_DELAY)
            while elapsed < sleep_time:
                if (is_cancelled and is_cancelled()) or error_event.is_set():
                    break
                time.sleep(min(0.5, sleep_time - elapsed))
                elapsed += 0.5

        return translated_texts

class DeepLTranslator(BaseTranslator):
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.api_url = "https://api.deepl.com/v2/translate"
        if api_key.endswith(":fx"):
            self.api_url = "https://api-free.deepl.com/v2/translate"

    def _do_translate_batch(self, texts: List[str], target_lang: str = "VI", source_lang: Optional[str] = None, **kwargs) -> List[str]:
        if not self.api_key:
            logger.warning("DeepL API Key is empty. Falling back to None.")
            return [None] * len(texts)

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
            with urllib.request.urlopen(req, timeout=30.0) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                return [item["text"] for item in res_data.get("translations", [])]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                logger.error("DeepL HTTP 429 Rate Limit Exceeded.")
                raise RateLimitError("DeepL API rate limit exceeded (HTTP 429).")
            logger.error(f"DeepL translate HTTP error {e.code}: {e}")
            return [None] * len(texts)
        except Exception as e:
            logger.error(f"DeepL translate batch error: {e}")
            return [None] * len(texts)
