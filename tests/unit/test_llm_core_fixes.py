from unittest.mock import MagicMock, patch
import json
from atm.core.translation.translators import LLMTranslator, RateLimitError

def test_repair_truncated_json():
    t = LLMTranslator(provider='gemini', api_key='AIzaSyTest')
    assert t._repair_truncated_json('["a", "b"]') == '["a", "b"]'
    assert t._repair_truncated_json('["hello", "wor') == '["hello", "wor"]'
    assert t._repair_truncated_json('["hello", "world"') == '["hello", "world"]'

def test_claude_max_tokens():
    t = LLMTranslator(provider='claude', api_key='sk-ant-test')
    with patch('urllib.request.urlopen') as mock_url:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({'content': [{'type': 'text', 'text': '["chao"]'}]}).encode('utf-8')
        mock_resp.__enter__.return_value = mock_resp
        mock_url.return_value = mock_resp

        t._call_claude_api('https://api.anthropic.com/v1/messages', 'system', '["hello"]')
        args, kwargs = mock_url.call_args
        req = args[0]
        payload = json.loads(req.data.decode('utf-8'))
        assert payload['max_tokens'] == 8192

def test_llm_progress_callback_delta():
    t = LLMTranslator(provider='gemini', api_key='AIzaSyTest', batch_size=2)
    deltas = []
    def on_progress(count):
        deltas.append(count)

    with patch.object(t, '_call_openai_compatible_api', return_value='["mot", "hai"]'):
        res = t.translate_batch(['one', 'two'], 'vi', 'en', progress_callback=on_progress)
        assert res == ['mot', 'hai']
        assert deltas == [2]

def test_llm_fallback_on_parse_error():
    t = LLMTranslator(provider='gemini', api_key='AIzaSyTest', batch_size=2)
    with patch.object(t, '_call_openai_compatible_api', return_value='INVALID_NOT_JSON'):
        with patch.object(t, '_get_fallback') as mock_fb_getter:
            mock_fb = MagicMock()
            mock_fb.translate_batch.return_value = ['mot', 'hai']
            mock_fb_getter.return_value = mock_fb

            res = t.translate_batch(['one', 'two'], 'vi', 'en')
            assert res == ['mot', 'hai']
            assert mock_fb.translate_batch.called

def test_rate_limit_error_contains_partial_results():
    t = LLMTranslator(provider='gemini', api_key='AIzaSyTest')
    t.batch_size = 1
    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["mot"]'
        import urllib.error
        raise urllib.error.HTTPError('url', 429, 'Rate Limit', {}, None)

    with patch.object(t, '_call_openai_compatible_api', side_effect=side_effect):
        with patch.object(t, '_get_fallback') as mock_fb_getter:
            mock_fb = MagicMock()
            mock_fb.translate_batch.side_effect = Exception('Fallback failed too')
            mock_fb_getter.return_value = mock_fb

            try:
                t.translate_batch(['one', 'two'], 'vi', 'en')
                assert False, 'Should have raised RateLimitError'
            except RateLimitError as e:
                assert e.partial_results is not None
                assert e.partial_results[0] == 'mot'
                assert e.partial_results[1] is None

def test_disable_fallback_prevents_google_and_raises_immediately():
    t = LLMTranslator(provider='gemini', api_key='AIzaSyTest')
    import urllib.error
    with patch.object(t, '_call_openai_compatible_api', side_effect=urllib.error.HTTPError('url', 429, 'Rate Limit', {}, None)):
        with patch.object(t, '_get_fallback') as mock_fb_getter:
            try:
                t.translate_batch(['hello'], 'vi', 'en', disable_fallback=True)
                assert False, 'Should have raised RateLimitError immediately'
            except RateLimitError:
                assert not mock_fb_getter.called

