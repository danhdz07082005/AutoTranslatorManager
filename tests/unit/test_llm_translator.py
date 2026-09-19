import json
import unittest
from unittest.mock import patch, MagicMock
import urllib.request
import urllib.error

from atm.core.translation.translators import LLMTranslator, GoogleTranslator, DeepLTranslator
from atm.core.translation import get_translator
from atm.config.schema import AppSettings, GameProfile
from atm.ui.api import BackendApi

class TestLLMTranslator(unittest.TestCase):
    def test_initialization_defaults(self):
        t = LLMTranslator(provider="gemini", api_key="test-key")
        self.assertEqual(t.provider, "gemini")
        self.assertEqual(t.model, LLMTranslator.DEFAULT_MODELS["gemini"])
        self.assertEqual(t.api_key, "test-key")

        t_deepseek = LLMTranslator(provider="deepseek")
        self.assertEqual(t_deepseek.model, "deepseek-chat")

        t_openai = LLMTranslator(provider="openai")
        self.assertEqual(t_openai.model, "gpt-4o-mini")

        t_claude = LLMTranslator(provider="claude")
        self.assertEqual(t_claude.model, LLMTranslator.DEFAULT_MODELS["claude"])

        t_kimi = LLMTranslator(provider="kimi")
        self.assertEqual(t_kimi.model, "moonshot-v1-8k")

        t_custom = LLMTranslator(provider="custom_llm", base_url="http://localhost:11434/v1")
        self.assertEqual(t_custom._get_endpoint(), "http://localhost:11434/v1/chat/completions")

    def test_build_system_prompt_with_glossary(self):
        glossary = {"Hero": "Anh Hùng", "Potion": "Bình Máu"}
        t = LLMTranslator(provider="gemini", glossary=glossary)
        prompt = t._build_system_prompt("ja", "vi")
        self.assertIn("ja to vi", prompt)
        self.assertIn("Hero", prompt)
        self.assertIn("Anh Hùng", prompt)
        self.assertIn("Potion", prompt)
        self.assertIn("STRICT LOCALIZATION RULES", prompt)

    def test_parse_llm_json(self):
        t = LLMTranslator()
        # Raw JSON
        res = t._parse_llm_json('["Xin chào", "Thế giới"]', 2)
        self.assertEqual(res, ["Xin chào", "Thế giới"])

        # Markdown fenced JSON
        res = t._parse_llm_json('```json\n["Xin chào", "Thế giới"]\n```', 2)
        self.assertEqual(res, ["Xin chào", "Thế giới"])

        # Markdown without lang tag
        res = t._parse_llm_json('```\n["Xin chào", "Thế giới"]\n```', 2)
        self.assertEqual(res, ["Xin chào", "Thế giới"])

        # Wrapped in conversational text
        res = t._parse_llm_json('Dưới đây là bản dịch:\n["Xin chào", "Thế giới"]\nChúc bạn vui vẻ!', 2)
        self.assertEqual(res, ["Xin chào", "Thế giới"])

        # Length mismatch -> None
        res = t._parse_llm_json('["Xin chào"]', 2)
        self.assertIsNone(res)

        # Invalid JSON -> None
        res = t._parse_llm_json('not a json array', 2)
        self.assertIsNone(res)

    def test_missing_api_key_raises_error(self):
        t = LLMTranslator(provider="gemini", api_key="")
        with self.assertRaises(ValueError) as ctx:
            t._do_translate_batch(["Hello"], target_lang="vi", source_lang="en")
        self.assertIn("API Key is required", str(ctx.exception))

    def test_unauthorized_api_key_raises_error(self):
        t = LLMTranslator(provider="deepseek", api_key="sk-invalid-key")
        err = urllib.error.HTTPError(
            url="https://api.deepseek.com/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=None
        )
        with patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(ValueError) as ctx:
                t._do_translate_batch(["Hello"], target_lang="vi", source_lang="en")
            self.assertIn("invalid or unauthorized", str(ctx.exception))

    def test_mock_openai_compatible_batch_success(self):
        t = LLMTranslator(provider="openai", api_key="sk-test")
        fake_response = {
            "choices": [{
                "message": {
                    "content": '["Xin chào", "Tạm biệt"]'
                }
            }]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = t._do_translate_batch(["Hello", "Goodbye"], target_lang="vi", source_lang="en")
            self.assertEqual(res, ["Xin chào", "Tạm biệt"])

    def test_mock_claude_batch_success(self):
        t = LLMTranslator(provider="claude", api_key="sk-ant-test")
        fake_response = {
            "content": [{
                "type": "text",
                "text": '["Xin chào", "Tạm biệt"]'
            }]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = t._do_translate_batch(["Hello", "Goodbye"], target_lang="vi", source_lang="en")
            self.assertEqual(res, ["Xin chào", "Tạm biệt"])

    def test_get_translator_factory(self):
        settings = AppSettings(
            gemini_api_key="gem-key",
            gemini_model="gemini-2.0-flash",
            deepseek_api_key="ds-key",
            deepseek_model="deepseek-reasoner",
            openai_api_key="o-key",
            claude_api_key="c-key",
            kimi_api_key="k-key",
            custom_llm_base_url="http://127.0.0.1:11434/v1",
            custom_llm_model="llama3.1:8b",
        )
        profile = GameProfile(game_name="TestGame", exe_path="C:/game.exe", glossary={"Sword": "Kiếm"})

        t_gem = get_translator("gemini", settings, profile)
        self.assertIsInstance(t_gem, LLMTranslator)
        self.assertEqual(t_gem.provider, "gemini")
        self.assertEqual(t_gem.model, "gemini-2.0-flash")
        self.assertEqual(t_gem.glossary, {"Sword": "Kiếm"})

        t_ds = get_translator("deepseek", settings, profile)
        self.assertEqual(t_ds.provider, "deepseek")
        self.assertEqual(t_ds.model, "deepseek-reasoner")

        t_custom = get_translator("custom_llm", settings, profile)
        self.assertEqual(t_custom.provider, "custom_llm")
        self.assertEqual(t_custom.model, "llama3.1:8b")
        self.assertEqual(t_custom.base_url, "http://127.0.0.1:11434/v1")

        t_deepl = get_translator("deepl", settings, profile)
        self.assertIsInstance(t_deepl, DeepLTranslator)

        t_goog = get_translator("google", settings, profile)
        self.assertIsInstance(t_goog, GoogleTranslator)

    def test_api_test_ai_connection(self):
        api = BackendApi()
        # Missing key error
        res_err = api.test_ai_connection(provider="gemini", api_key="")
        self.assertEqual(res_err["status"], "error")
        self.assertEqual(res_err["code"], "error.api_key_missing")

        # Mock success
        with patch.object(LLMTranslator, "_do_translate_batch", return_value=["Xin chào"]):
            res_ok = api.test_ai_connection(provider="gemini", api_key="AIzaSy" + "A" * 30)
            self.assertEqual(res_ok["status"], "success")
            self.assertEqual(res_ok["provider"], "gemini")
            self.assertIn("latency_ms", res_ok)

    def test_start_game_validates_missing_ai_key(self):
        api = BackendApi()
        profile = GameProfile(
            game_name="NoKeyGame",
            exe_path="C:/game.exe",
            translator="gemini",
            output_lang="vi"
        )
        api.profile_repo.save(profile)
        api.update_settings(gemini_api_key="")

        res = api.start_game(profile.id)
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "toast.no_ai_key")
        self.assertIn("Google Gemini", res["error"])

    def test_detect_key_mismatch(self):
        from atm.ui.api import detect_key_mismatch
        # Gemini key pasted into OpenAI
        m1 = detect_key_mismatch("openai", "AIzaSyTestKey123")
        self.assertIsNotNone(m1)
        self.assertEqual(m1["detected_provider"], "gemini")

        # Gemini key in Gemini is valid
        self.assertIsNone(detect_key_mismatch("gemini", "AIzaSyTestKey123"))

        # Claude key pasted into Gemini
        m2 = detect_key_mismatch("gemini", "sk-ant-api03-test")
        self.assertIsNotNone(m2)
        self.assertEqual(m2["detected_provider"], "claude")

        # Claude key in Claude is valid
        self.assertIsNone(detect_key_mismatch("claude", "sk-ant-api03-test"))

        # DeepL key pasted into DeepSeek
        m3 = detect_key_mismatch("deepseek", "abcd-1234:fx")
        self.assertIsNotNone(m3)
        self.assertEqual(m3["detected_provider"], "deepl")

        # Empty key
        self.assertIsNone(detect_key_mismatch("openai", ""))

    def test_custom_base_url_settings_and_endpoint(self):
        api = BackendApi()
        res = api.update_settings(
            gemini_base_url="https://my-proxy.com/v1",
            deepseek_base_url="https://my-deepseek-proxy.com/v1",
            openai_base_url="https://my-openai-proxy.com/v1",
            claude_base_url="https://my-claude-proxy.com/v1",
            kimi_base_url="https://my-kimi-proxy.com/v1"
        )
        self.assertEqual(res["status"], "success")

        settings = api.settings_repo.load()
        self.assertEqual(settings.gemini_base_url, "https://my-proxy.com/v1")
        self.assertEqual(settings.deepseek_base_url, "https://my-deepseek-proxy.com/v1")

        # Custom OpenAI endpoint
        t_oai = LLMTranslator(provider="openai", base_url="https://my-openai-proxy.com/v1")
        self.assertEqual(t_oai._get_endpoint(), "https://my-openai-proxy.com/v1/chat/completions")

        # Custom Claude endpoint
        t_claude = LLMTranslator(provider="claude", base_url="https://my-claude-proxy.com/v1")
        self.assertEqual(t_claude._get_endpoint(), "https://my-claude-proxy.com/v1/messages")

    def test_gemini_native_batch_success(self):
        t = LLMTranslator(provider="gemini", api_key="AIzaSyTest", base_url="https://generativelanguage.googleapis.com/v1beta")
        fake_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": '["Xin chào", "Tạm biệt"]'
                    }]
                }
            }]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = t._do_translate_batch(["Hello", "Goodbye"], target_lang="vi", source_lang="en")
            self.assertEqual(res, ["Xin chào", "Tạm biệt"])

    def test_api_test_ai_connection_with_mismatch_warning(self):
        api = BackendApi()
        # Testing OpenAI with a Gemini key -> soft warning allows attempt, fails auth and appends mismatch warning
        res = api.test_ai_connection(provider="openai", api_key="AIzaSyTestKey12345678901234567890")
        self.assertEqual(res["status"], "error")
        self.assertIn("Google Gemini", res["error"])

    def test_invalid_model_error_extraction(self):
        import io
        t = LLMTranslator(provider="gemini", api_key="AIzaSyTest1234567890123456789012345")
        err_json = json.dumps({"error": {"message": "models/non-existent-model is not found"}}).encode("utf-8")
        err_fp = io.BytesIO(err_json)
        err = urllib.error.HTTPError(
            url="https://generativelanguage.googleapis.com",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=err_fp
        )
        with patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(ValueError) as ctx:
                t._do_translate_batch(["Hello"], target_lang="vi", source_lang="en")
            self.assertIn("models/non-existent-model is not found", str(ctx.exception))

    def test_model_casing_normalization(self):
        t_gem = LLMTranslator(provider="gemini", model="Gemini-1.5-FLASH")
        self.assertEqual(t_gem.model, "gemini-1.5-flash")

        t_oai = LLMTranslator(provider="openai", model="  GPT-4o-Mini  ")
        self.assertEqual(t_oai.model, "gpt-4o-mini")

        t_claude = LLMTranslator(provider="claude", model="Claude-3-5-Sonnet")
        self.assertEqual(t_claude.model, "claude-3-5-sonnet")

        # Custom LLM preserves case (e.g. Ollama tags)
        t_custom = LLMTranslator(provider="custom_llm", model="Qwen/Qwen2.5-7B")
        self.assertEqual(t_custom.model, "Qwen/Qwen2.5-7B")



