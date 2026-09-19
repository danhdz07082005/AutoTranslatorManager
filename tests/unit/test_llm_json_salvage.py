import unittest
from unittest.mock import MagicMock, patch
import json
import urllib.error
from atm.core.translation.translators import LLMTranslator, RateLimitError

class TestLLMJsonSalvage(unittest.TestCase):
    def setUp(self):
        self.translator = LLMTranslator(provider="gemini", api_key="AIzaFakeKey")

    def test_repair_trailing_comma(self):
        # Case 1: Trailing comma with space
        raw1 = '["Hello", "World", '
        repaired1 = self.translator._repair_truncated_json(raw1)
        self.assertEqual(repaired1, '["Hello", "World"]')
        parsed1 = json.loads(repaired1)
        self.assertEqual(parsed1, ["Hello", "World"])

        # Case 2: Trailing comma without space
        raw2 = '["Item 1","Item 2",'
        repaired2 = self.translator._repair_truncated_json(raw2)
        self.assertEqual(repaired2, '["Item 1","Item 2"]')
        parsed2 = json.loads(repaired2)
        self.assertEqual(parsed2, ["Item 1", "Item 2"])

        # Case 3: Truncated inside a string
        raw3 = '["First", "Seco'
        repaired3 = self.translator._repair_truncated_json(raw3)
        self.assertEqual(repaired3, '["First", "Seco"]')
        parsed3 = json.loads(repaired3)
        self.assertEqual(parsed3, ["First", "Seco"])

    def test_parse_llm_json_partial_salvage(self):
        raw = '["Sword", "Shield", '
        
        # When allow_partial=False, mismatch should return None
        res_no_partial = self.translator._parse_llm_json(raw, expected_len=4, allow_partial=False)
        self.assertIsNone(res_no_partial)

        # When allow_partial=True, should salvage 2 items and pad with None
        res_partial = self.translator._parse_llm_json(raw, expected_len=4, allow_partial=True)
        self.assertIsNotNone(res_partial)
        self.assertEqual(res_partial, ["Sword", "Shield", None, None])

    def test_partial_results_salvaged_with_targeted_fallback(self):
        # 3 items to translate
        texts = ["Text A", "Text B", "Text C"]
        
        # LLM only returns 2 items due to truncation
        mock_raw_response = '["Dịch A", "Dịch B", '
        
        fallback_mock = MagicMock()
        # Fallback should only be asked to translate the 1 missing item ("Text C")
        fallback_mock.translate_batch.return_value = ["Dịch C (Fallback)"]
        self.translator._fallback_translator = fallback_mock

        with patch.object(self.translator, "_call_openai_compatible_api", return_value=mock_raw_response):
            results = self.translator.translate_batch(texts, target_lang="vi", source_lang="en")
            
            # Check fallback was called with only the 3rd missing text!
            fallback_mock.translate_batch.assert_called_once()
            called_texts = fallback_mock.translate_batch.call_args[0][0]
            self.assertEqual(called_texts, ["Text C"])
            
            # Check final combined results: 2 from LLM + 1 from fallback
            self.assertEqual(results, ["Dịch A", "Dịch B", "Dịch C (Fallback)"])

    def test_error_classification_runtime_error_not_rate_limit(self):
        # Non-429 error (e.g. malformed response) where fallback also fails
        mock_raw_response = "Invalid non-json output"
        
        fallback_mock = MagicMock()
        fallback_mock.translate_batch.side_effect = Exception("Fallback network failure")
        self.translator._fallback_translator = fallback_mock

        with patch.object(self.translator, "_call_openai_compatible_api", return_value=mock_raw_response):
            # _do_translate_batch must raise RuntimeError, NOT RateLimitError!
            with self.assertRaises(RuntimeError) as ctx:
                self.translator._do_translate_batch(["Hello"], target_lang="vi", source_lang="en")
            self.assertNotIsInstance(ctx.exception, RateLimitError)
            self.assertIn("Translation failed for GEMINI", str(ctx.exception))

            # translate_batch safely catches RuntimeError and returns [None] without false RateLimitError
            res = self.translator.translate_batch(["Hello"], target_lang="vi", source_lang="en")
            self.assertEqual(res, [None])

    def test_error_classification_rate_limit_error_on_429(self):
        http_429 = urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None)
        
        fallback_mock = MagicMock()
        fallback_mock.translate_batch.side_effect = Exception("Fallback network failure")
        self.translator._fallback_translator = fallback_mock

        with patch.object(self.translator, "_call_openai_compatible_api", side_effect=http_429):
            # Must raise RateLimitError
            with self.assertRaises(RateLimitError) as ctx:
                self.translator.translate_batch(["Hello"], target_lang="vi", source_lang="en")
            self.assertIn("rate limit exceeded", str(ctx.exception).lower())

if __name__ == '__main__':
    unittest.main()
