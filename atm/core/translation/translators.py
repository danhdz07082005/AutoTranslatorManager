import urllib.request
import urllib.parse
import json
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
    def __init__(self, message, partial_results=None):
        super().__init__(message)
        self.partial_results = partial_results

class BaseTranslator:
    def __init__(self):
        pass

    def translate_batch(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: str,
        category: str = "unknown",
        is_cancelled = None,
        progress_callback = None,
        disable_fallback: bool = False,
        **kwargs,
    ) -> List[Optional[str]]:
        if not texts:
            return []

        try:
            results = self._do_translate_batch(
                texts,
                target_lang,
                source_lang,
                category=category,
                is_cancelled=is_cancelled,
                progress_callback=progress_callback,
                disable_fallback=disable_fallback,
                **kwargs,
            )
            if results and len(results) == len(texts):
                return results
            else:
                logger.warning(f"Batch translate returned mismatch results count. Expected {len(texts)}, got {len(results) if results else 0}.")
                return [None] * len(texts)
        except (RateLimitError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Error in _do_translate_batch (type: {type(e)}): {e}")
            return [None] * len(texts)

    def translate_categorized(
        self,
        entries: Iterable[Tuple[str, str]],
        target_lang: str,
        source_lang: str,
        is_cancelled = None,
        progress_callback = None,
    ) -> List[Optional[str]]:
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

    def _do_translate_batch(self, texts: List[str], target_lang: str, source_lang: str, is_cancelled=None, progress_callback=None, **kwargs) -> List[Optional[str]]:
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

        is_realtime = kwargs.get("is_realtime", False) or len(texts) <= 1

        for chunk_idx, chunk in enumerate(chunks):
            if (is_cancelled and is_cancelled()) or error_event.is_set():
                break
            
            chunk_texts = [text for _, text in chunk]
            try:
                res_parts = translate_chunk_with_retry(chunk_texts)
            except RateLimitError as e:
                e.partial_results = translated_texts
                raise e
            
            if res_parts and None not in res_parts:
                if progress_callback:
                    progress_callback(len(chunk))
            
            for (target_idx, _source_text), res_text in zip(chunk, res_parts):
                translated_texts[target_idx] = res_text
            
            # Rate-limiting delay: ONLY between chunks in offline batch mode (NEVER for realtime and NEVER after the last chunk)
            if not is_realtime and chunk_idx < len(chunks) - 1:
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

    def _do_translate_batch(self, texts: List[str], target_lang: str, source_lang: Optional[str] = None, **kwargs) -> List[str]:
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

        if not self.api_key:
            raise ValueError("DeepL API Key is required")

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
            if e.code in (401, 403):
                logger.error(f"DeepL API Key unauthorized (HTTP {e.code}).")
                raise ValueError(f"DeepL API Key is invalid or unauthorized (HTTP {e.code})")
            logger.error(f"DeepL translate HTTP error {e.code}: {e}")
            return [None] * len(texts)
        except Exception as e:
            logger.error(f"DeepL translate batch error: {e}")
            return [None] * len(texts)


class LLMTranslator(BaseTranslator):
    """Multi-AI / LLM Translation Engine.
    
    Supports:
    - Google Gemini (via OpenAI-compatible endpoint)
    - DeepSeek (deepseek-chat, deepseek-reasoner)
    - OpenAI ChatGPT (gpt-4o-mini, gpt-4o)
    - Anthropic Claude (claude-3-5-haiku, claude-3-5-sonnet via Messages API)
    - Kimi / Moonshot AI (moonshot-v1-8k, moonshot-v1-32k)
    - Custom / Local LLM (Ollama, LM Studio, OpenRouter)
    """

    DEFAULT_MODELS = {
        "gemini": "gemini-2.5-flash",
        "deepseek": "deepseek-chat",
        "openai": "gpt-4o-mini",
        "claude": "claude-3-7-sonnet-20250219",
        "kimi": "moonshot-v1-8k",
        "custom_llm": "qwen2.5:7b",
    }

    ENDPOINTS = {
        "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "deepseek": "https://api.deepseek.com/chat/completions",
        "openai": "https://api.openai.com/v1/chat/completions",
        "claude": "https://api.anthropic.com/v1/messages",
        "kimi": "https://api.moonshot.cn/v1/chat/completions",
    }

    def __init__(
        self,
        provider: str = "gemini",
        api_key: str = "",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        glossary: Optional[dict] = None,
        batch_size: int = 25,
        timeout: float = 45.0,
    ):
        super().__init__()
        self.provider = provider.lower()
        self.api_key = api_key.strip()
        raw_model = (model or self.DEFAULT_MODELS.get(self.provider, "gpt-4o-mini")).strip()
        if self.provider in ("gemini", "deepseek", "openai", "claude", "kimi"):
            self.model = raw_model.lower()
        else:
            self.model = raw_model
        self.base_url = (base_url or "").strip()
        self.glossary = glossary or {}
        self.batch_size = max(5, min(batch_size, 50))
        self.timeout = timeout
        self._fallback_translator = None

    def _get_endpoint(self) -> str:
        if self.base_url:
            url = self.base_url.rstrip("/")
            if ":generateContent" in url or url.endswith("/messages") or url.endswith("/chat/completions"):
                return url
            if self.provider == "claude":
                return f"{url}/messages"
            if self.provider == "gemini" and "googleapis.com" in url and "/openai" not in url:
                return f"{url}/models/{self.model}:generateContent"
            return f"{url}/chat/completions"
        return self.ENDPOINTS.get(self.provider, self.ENDPOINTS["openai"])

    def _build_system_prompt(self, source_lang: str, target_lang: str) -> str:
        s_lang = source_lang if source_lang and source_lang != "auto" else "original game language"
        t_lang = target_lang or "Vietnamese"

        prompt = (
            f"You are a professional video game localizer specializing in Visual Novels and JRPGs.\n"
            f"Translate the provided JSON array of strings from {s_lang} to {t_lang}.\n\n"
            f"STRICT LOCALIZATION RULES:\n"
            f"1. Natural, immersive dialogue that fits character personality, emotion, and context.\n"
            f"2. PRESERVE EXACTLY all game variables, tags, brackets, and escape codes intact "
            f"(e.g. \\n, %s, %d, [name], {{color}}, <tag>, \\c[1], \\v[1]). NEVER modify or delete them.\n"
            f"3. Return ONLY a valid JSON array of translated strings matching the exact count and order of the input.\n"
            f"4. NO conversational text, NO markdown code fences. Strictly output: [\"translated1\", \"translated2\", ...]"
        )

        if self.glossary:
            glossary_entries = [f"- \"{k}\" -> \"{v}\"" for k, v in list(self.glossary.items())[:50] if k and v]
            if glossary_entries:
                prompt += "\n\nGLOSSARY (Strictly enforce these terms):\n" + "\n".join(glossary_entries)

        return prompt

    def _repair_truncated_json(self, text: str) -> str:
        s = text.strip()
        if s.startswith("[") and not s.endswith("]"):
            in_quote = False
            for i, ch in enumerate(s):
                if ch == '"' and (i == 0 or s[i - 1] != '\\'):
                    in_quote = not in_quote
            if in_quote:
                s += '"'
            # Loại bỏ các dấu phẩy thừa trước ngoặc vuông theo chuẩn RFC 8259
            s = s.rstrip()
            while s.endswith(','):
                s = s[:-1].rstrip()
            s += "]"
        return s

    def _parse_llm_json(self, response_text: str, expected_len: int, allow_partial: bool = False) -> Optional[List[Optional[str]]]:
        text = response_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()

        def _validate_or_salvage(obj) -> Optional[List[Optional[str]]]:
            if not isinstance(obj, list):
                return None
            if len(obj) == expected_len:
                return [str(x) if x is not None else "" for x in obj]
            if allow_partial and 0 < len(obj) < expected_len:
                salvaged: List[Optional[str]] = [str(x) if x is not None else "" for x in obj]
                salvaged.extend([None] * (expected_len - len(obj)))
                return salvaged
            return None

        # 1. Thử parse trực tiếp
        try:
            res = json.loads(text)
            validated = _validate_or_salvage(res)
            if validated is not None:
                return validated
        except Exception:
            pass

        # 2. Thử parse qua hàm sửa lỗi cắt cụt
        try:
            repaired = self._repair_truncated_json(text)
            res = json.loads(repaired)
            validated = _validate_or_salvage(res)
            if validated is not None:
                return validated
        except Exception:
            pass

        # 3. Regex tìm mảng đã đóng [...]
        bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
        if bracket_match:
            try:
                res = json.loads(bracket_match.group(0))
                validated = _validate_or_salvage(res)
                if validated is not None:
                    return validated
            except Exception:
                pass

        # 4. Regex tìm mảng chưa đóng [ ... và cứu hộ
        unclosed_match = re.search(r"\[.*", text, re.DOTALL)
        if unclosed_match:
            try:
                repaired = self._repair_truncated_json(unclosed_match.group(0))
                res = json.loads(repaired)
                validated = _validate_or_salvage(res)
                if validated is not None:
                    return validated
            except Exception:
                pass

        return None


    def _call_claude_api(self, endpoint: str, system_prompt: str, user_content: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 8192,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        }
        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content_blocks = data.get("content", [])
            for block in content_blocks:
                if block.get("type") == "text":
                    return block.get("text", "")
            return ""

    def _call_openai_compatible_api(self, endpoint: str, system_prompt: str, user_content: str) -> str:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.3,
        }

        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""

    def _call_gemini_native_api(self, endpoint: str, system_prompt: str, user_content: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "parts": [{"text": user_content}]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
            }
        }
        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            return ""

    def _do_translate_batch(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: Optional[str] = None,
        **kwargs
    ) -> List[Optional[str]]:
        if not texts:
            return []

        if not self.api_key and self.provider != "custom_llm":
            logger.error(f"{self.provider.upper()} API Key is missing.")
            raise ValueError(f"{self.provider.upper()} API Key is required. Please configure it in Settings before starting.")

        is_cancelled = kwargs.get("is_cancelled")
        progress_callback = kwargs.get("progress_callback")

        endpoint = self._get_endpoint()
        system_prompt = self._build_system_prompt(source_lang or "auto", target_lang)

        results: List[Optional[str]] = [None] * len(texts)
        total_items = len(texts)

        disable_fallback = kwargs.get("disable_fallback", False)
        for chunk_start in range(0, total_items, self.batch_size):
            if is_cancelled and is_cancelled():
                break

            chunk_end = min(chunk_start + self.batch_size, total_items)
            chunk_texts = texts[chunk_start:chunk_end]
            expected_count = len(chunk_texts)

            # Skip translation for entirely empty/blank items
            user_content = json.dumps(chunk_texts, ensure_ascii=False)

            parsed_chunk = None
            max_retries = 1 if disable_fallback else 3
            last_http_code = None
            raw_response = ""
            for attempt in range(max_retries):
                if is_cancelled and is_cancelled():
                    break
                try:
                    if self.provider == "claude":
                        raw_response = self._call_claude_api(endpoint, system_prompt, user_content)
                    elif ":generateContent" in endpoint:
                        raw_response = self._call_gemini_native_api(endpoint, system_prompt, user_content)
                    else:
                        raw_response = self._call_openai_compatible_api(endpoint, system_prompt, user_content)

                    parsed_chunk = self._parse_llm_json(raw_response, expected_count)
                    if parsed_chunk and len(parsed_chunk) == expected_count and None not in parsed_chunk:
                        break
                    else:
                        logger.warning(
                            f"{self.provider} response parse mismatch (attempt {attempt + 1}/{max_retries}). "
                            f"Expected {expected_count} items."
                        )
                        if attempt == max_retries - 1:
                            salvaged = self._parse_llm_json(raw_response, expected_count, allow_partial=True)
                            if salvaged and any(x is not None for x in salvaged):
                                parsed_chunk = salvaged
                                logger.info(
                                    f"Salvaged {sum(1 for x in salvaged if x is not None)}/{expected_count} "
                                    f"partial items from {self.provider} truncated response."
                                )
                except urllib.error.HTTPError as e:
                    last_http_code = e.code
                    err_body = ""
                    try:
                        raw_err = e.read().decode("utf-8", errors="ignore")
                        err_json = json.loads(raw_err)
                        if isinstance(err_json, dict):
                            if "error" in err_json:
                                err_obj = err_json["error"]
                                if isinstance(err_obj, dict):
                                    err_body = err_obj.get("message") or str(err_obj)
                                elif isinstance(err_obj, str):
                                    err_body = err_obj
                            elif "message" in err_json:
                                err_body = err_json["message"]
                    except Exception:
                        pass

                    if e.code in (401, 403):
                        logger.error(f"{self.provider.upper()} Authentication failed (HTTP {e.code}). API Key is invalid or expired. Detail: {err_body}")
                        detail = f": {err_body}" if err_body else ""
                        raise ValueError(f"API Key for {self.provider.upper()} is invalid or unauthorized (HTTP {e.code}){detail}")
                    elif e.code == 404:
                        logger.error(f"{self.provider.upper()} endpoint or model not found (HTTP 404): {err_body}")
                        detail = f": {err_body}" if err_body else f": {self.model}"
                        raise ValueError(f"Model or endpoint for {self.provider.upper()} not found (HTTP 404){detail}")
                    elif e.code == 400:
                        logger.error(f"{self.provider.upper()} Bad Request (HTTP 400): {err_body}")
                        detail = f": {err_body}" if err_body else ""
                        raise ValueError(f"{self.provider.upper()} Bad Request (HTTP 400){detail}")
                    elif e.code == 429:
                        logger.error(f"{self.provider} HTTP 429 Rate Limit. Attempt {attempt + 1}/{max_retries}.")
                        if disable_fallback:
                            raise RateLimitError(f"{self.provider} rate limit exceeded (HTTP 429).")
                        if attempt == max_retries - 1:
                            detail = f": {err_body}" if err_body else ""
                            # Thử fallback bằng GoogleTranslator trước khi từ bỏ
                            logger.info(f"{self.provider} rate limited. Attempting GoogleTranslator fallback...")
                            try:
                                fallback = self._get_fallback()
                                fb_res = fallback.translate_batch(
                                    chunk_texts,
                                    target_lang=target_lang,
                                    source_lang=source_lang or "auto",
                                    category=kwargs.get("category", "unknown"),
                                    is_cancelled=is_cancelled
                                )
                                if fb_res and len(fb_res) == expected_count and None not in fb_res:
                                    parsed_chunk = fb_res
                                    logger.info(f"Fallback to GoogleTranslator succeeded for chunk {chunk_start}:{chunk_end}.")
                                    break
                            except Exception as fb_err:
                                logger.error(f"Fallback translation failed: {fb_err}")

                            err = RateLimitError(
                                f"{self.provider} rate limit exceeded (HTTP 429){detail}.",
                                partial_results=results
                            )
                            raise err
                        time.sleep(2.0 * (attempt + 1))
                    elif e.code in (500, 502, 503, 504):
                        logger.warning(f"{self.provider} server error {e.code}. Retrying...")
                        if disable_fallback:
                            raise RuntimeError(f"{self.provider} server error (HTTP {e.code})")
                        time.sleep(1.5 * (attempt + 1))
                    else:
                        logger.error(f"{self.provider} HTTP error {e.code}: {e} - {err_body}")
                        if disable_fallback:
                            raise RuntimeError(f"{self.provider} HTTP error {e.code}: {err_body or e}")
                        break
                except Exception as e:
                    logger.error(f"{self.provider} request error on attempt {attempt + 1}: {e}")
                    if disable_fallback:
                        raise e
                    time.sleep(1.0)

            if is_cancelled and is_cancelled():
                break

            # Nếu LLM thất bại sau retries hoặc có câu chưa hoàn thiện (partial) -> Fallback Google bù vào các câu thiếu
            if not parsed_chunk or len(parsed_chunk) != expected_count or None in parsed_chunk:
                if disable_fallback:
                    raise RuntimeError(f"Connection test failed: {self.provider.upper()} did not return a valid translation response.")
                missing_indices = [idx for idx, val in enumerate(parsed_chunk or []) if val is None] if (parsed_chunk and len(parsed_chunk) == expected_count) else list(range(expected_count))
                missing_texts = [chunk_texts[idx] for idx in missing_indices]

                logger.warning(
                    f"{self.provider.upper()} incomplete for chunk {chunk_start}:{chunk_end} ({len(missing_texts)}/{expected_count} missing). "
                    f"Falling back to GoogleTranslator."
                )
                try:
                    fallback = self._get_fallback()
                    fb_res = fallback.translate_batch(
                        missing_texts,
                        target_lang=target_lang,
                        source_lang=source_lang or "auto",
                        category=kwargs.get("category", "unknown"),
                        is_cancelled=is_cancelled
                    )
                    if fb_res and len(fb_res) == len(missing_texts) and None not in fb_res:
                        if not parsed_chunk or len(parsed_chunk) != expected_count:
                            parsed_chunk = [None] * expected_count
                        for m_idx, fb_val in zip(missing_indices, fb_res):
                            parsed_chunk[m_idx] = fb_val
                        logger.info(f"Fallback to GoogleTranslator succeeded for missing {len(missing_texts)} items in chunk {chunk_start}:{chunk_end}.")
                except Exception as fb_err:
                    logger.error(f"Fallback translation failed: {fb_err}")

            # Ghi nhận kết quả vào results
            if parsed_chunk and len(parsed_chunk) == expected_count and None not in parsed_chunk:
                for i, trans in enumerate(parsed_chunk):
                    results[chunk_start + i] = trans
            else:
                # Bảo toàn tối đa các câu partial đã dịch được
                if parsed_chunk:
                    for i, trans in enumerate(parsed_chunk):
                        if trans is not None and (chunk_start + i) < len(results):
                            results[chunk_start + i] = trans

                logger.error(f"Translation failed for chunk {chunk_start}:{chunk_end} using {self.provider} and fallback.")
                if last_http_code == 429:
                    err = RateLimitError(
                        f"Translation rate-limited for {self.provider.upper()} (HTTP 429) after {max_retries} attempts and fallback.",
                        partial_results=results
                    )
                else:
                    err = RuntimeError(
                        f"Translation failed for {self.provider.upper()} after {max_retries} attempts and fallback."
                    )
                raise err

            if progress_callback and parsed_chunk and None not in parsed_chunk:
                progress_callback(len(chunk_texts))

        return results


    def _get_fallback(self) -> BaseTranslator:
        if self._fallback_translator is None:
            self._fallback_translator = GoogleTranslator()
        return self._fallback_translator

