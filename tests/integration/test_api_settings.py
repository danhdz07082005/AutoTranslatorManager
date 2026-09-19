from atm.ui.api import BackendApi

def test_get_settings_hides_deepl_key(tmp_path, monkeypatch):
    test_config = tmp_path / "config.json"
    monkeypatch.setattr("atm.storage.repositories.settings_repository.CONFIG_PATH", str(test_config))
    api = BackendApi()
    
    api.update_settings(deepl_api_key="secret_key_1234567890_deepl", dark_mode=True)
    
    settings = api.get_settings()
    assert "deepl_api_key" not in settings
    assert settings.get("deepl_api_key_configured") is True
    assert settings.get("dark_mode") is True
    
    api.update_settings(deepl_api_key="")
    settings = api.get_settings()
    assert "deepl_api_key" not in settings
    assert settings.get("deepl_api_key_configured") is False


def test_detect_model_mismatch():
    from atm.ui.api import detect_model_mismatch
    # Gemini tab with Claude model
    res = detect_model_mismatch("gemini", "claude-3-5-sonnet")
    assert res is not None
    assert res["detected_provider"] == "claude"

    # OpenAI tab with Gemini model
    res = detect_model_mismatch("openai", "gemini-1.5-flash")
    assert res is not None
    assert res["detected_provider"] == "gemini"

    # DeepSeek tab with DeepSeek model (correct)
    assert detect_model_mismatch("deepseek", "deepseek-chat") is None

    # Custom LLM allows any model
    assert detect_model_mismatch("custom_llm", "claude-3-5-sonnet") is None


def test_update_settings_rejects_model_mismatch(tmp_path, monkeypatch):
    test_config = tmp_path / "config.json"
    monkeypatch.setattr("atm.storage.repositories.settings_repository.CONFIG_PATH", str(test_config))
    api = BackendApi()

    # Attempt to save a Claude model under Gemini
    res = api.update_settings(gemini_model="claude-3-5-sonnet")
    assert res.get("status") == "error"
    assert res.get("code") == "error.invalid_model_format"


def test_save_model_independently_when_key_locked(tmp_path, monkeypatch):
    test_config = tmp_path / "config.json"
    monkeypatch.setattr("atm.storage.repositories.settings_repository.CONFIG_PATH", str(test_config))
    api = BackendApi()

    # 1. First save a valid Gemini key and default model
    valid_key = "AIzaSy" + "B" * 35
    api.update_settings(gemini_api_key=valid_key, gemini_model="gemini-1.5-flash")
    
    settings = api.get_settings()
    assert settings.get("gemini_api_key_configured") is True
    assert settings.get("gemini_model") == "gemini-1.5-flash"

    # 2. Update ONLY the model to a new future model (e.g. gemini-3.8-flash) without sending key
    res = api.update_settings(gemini_model="gemini-3.8-flash")
    assert res.get("status") == "success"

    # 3. Verify model updated and key is STILL configured
    settings = api.get_settings()
    assert settings.get("gemini_api_key_configured") is True
    assert settings.get("gemini_model") == "gemini-3.8-flash"


def test_test_ai_connection_rejects_mismatched_model(tmp_path, monkeypatch):
    test_config = tmp_path / "config.json"
    monkeypatch.setattr("atm.storage.repositories.settings_repository.CONFIG_PATH", str(test_config))
    api = BackendApi()

    valid_key = "AIzaSy" + "B" * 35
    res = api.test_ai_connection(provider="gemini", api_key=valid_key, model="gpt-4o")
    assert res.get("status") == "error"
    assert res.get("code") == "error.invalid_model_format"


def test_fetch_available_models_missing_key():
    api = BackendApi()
    res = api.fetch_available_models(provider="gemini", api_key="")
    assert res.get("status") == "error"
    assert res.get("code") == "error.api_key_missing"


def test_fetch_available_models_gemini_success(monkeypatch):
    import io
    import json
    api = BackendApi()

    mock_body = {
        "models": [
            {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.8-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
        ]
    }

    class MockResponse:
        def __init__(self):
            self.data = json.dumps(mock_body).encode("utf-8")
        def read(self):
            return self.data
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=None: MockResponse())
    res = api.fetch_available_models(provider="gemini", api_key="AIzaSyDummyKey12345678901234567890")
    assert res.get("status") == "success"
    assert "gemini-3.8-flash" in res.get("models", [])
    assert "gemini-2.5-flash" in res.get("models", [])
    assert not any("embedding" in m for m in res.get("models", []))


def test_fetch_available_models_openai_success(monkeypatch):
    import json
    api = BackendApi()

    mock_body = {
        "data": [
            {"id": "gpt-4o-mini"},
            {"id": "gpt-6-astra"},
            {"id": "text-embedding-3-small"},
        ]
    }

    class MockResponse:
        def __init__(self):
            self.data = json.dumps(mock_body).encode("utf-8")
        def read(self):
            return self.data
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=None: MockResponse())
    res = api.fetch_available_models(provider="openai", api_key="sk-testkey12345678901234567890")
    assert res.get("status") == "success"
    assert "gpt-6-astra" in res.get("models", [])
    assert "gpt-4o-mini" in res.get("models", [])
    assert not any("embedding" in m for m in res.get("models", []))


