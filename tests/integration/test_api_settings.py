from atm.ui.api import BackendApi

def test_get_settings_hides_deepl_key(temp_profiles_dir):
    api = BackendApi()
    
    api.update_settings(deepl_api_key="secret_key_123", dark_mode=True)
    
    settings = api.get_settings()
    assert "deepl_api_key" not in settings
    assert settings.get("deepl_api_key_configured") is True
    assert settings.get("dark_mode") is True
    
    api.update_settings(deepl_api_key="")
    settings = api.get_settings()
    assert "deepl_api_key" not in settings
    assert settings.get("deepl_api_key_configured") is False
