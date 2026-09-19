import json
import os
from pathlib import Path
from atm.ui.api import BackendApi, validate_api_key, detect_key_mismatch
from atm.core.translation.cache_manager import TranslationCache
from atm.storage.repositories.sqlite_translation_cache import SQLiteTranslationCache


def test_validate_api_key_soft_warning():
    # 1. Gemini key pasted into OpenAI -> Valid format is True, but with soft warning
    is_valid, warn = validate_api_key("openai", "AIzaSy" + "A" * 34)
    assert is_valid is True
    assert "Google Gemini" in warn

    # 2. Claude key pasted into Gemini -> Valid is True, with warning
    is_valid, warn = validate_api_key("gemini", "sk-ant-" + "B" * 45)
    assert is_valid is True
    assert "Anthropic Claude" in warn

    # 3. DeepL free key pasted into DeepSeek -> Valid is True, with warning
    is_valid, warn = validate_api_key("deepseek", "12345678-1234-1234-1234-123456789012:fx")
    assert is_valid is True
    assert "DeepL" in warn

    # 4. Correct key -> Valid is True, warning is empty
    is_valid, warn = validate_api_key("openai", "sk-" + "C" * 25)
    assert is_valid is True
    assert warn == ""

    # 5. Invalid short key -> Valid is False
    is_valid, err = validate_api_key("openai", "sk-short")
    assert is_valid is False
    assert "quá ngắn" in err or "không hợp lệ" in err


def test_update_settings_saves_key_with_soft_warning(isolate_test_environment):
    api = BackendApi()
    mismatched_key = "AIzaSy" + "A" * 34

    res = api.update_settings(openai_api_key=mismatched_key)
    assert res.get("status") == "success"
    assert "warning" in res
    assert "Google Gemini" in res["warning"]

    settings = api.get_settings()
    assert settings.get("openai_api_key_configured") is True


def test_cache_migration_memory_cleanup(tmp_path):
    data_dir = str(tmp_path / "trans_data")
    os.makedirs(data_dir, exist_ok=True)
    legacy_file = os.path.join(data_dir, "translation_cache.json")

    # Create dummy legacy cache JSON
    legacy_data = {
        "schema_version": 2,
        "entries": {
            "en": {
                "vi": {
                    "general": {
                        "Hello": "Xin chao",
                        "World": "The gioi"
                    }
                }
            }
        }
    }
    with open(legacy_file, "w", encoding="utf-8") as f:
        json.dump(legacy_data, f)

    TranslationCache._instance = None
    cache = TranslationCache(data_dir=data_dir)

    # Verify migration occurred
    assert cache.get("en", "vi", "Hello", "general") == "Xin chao"
    assert cache.get("en", "vi", "World", "general") == "The gioi"

    # Verify legacy file was moved to .bak
    assert not os.path.exists(legacy_file)
    assert os.path.exists(legacy_file + ".bak")
