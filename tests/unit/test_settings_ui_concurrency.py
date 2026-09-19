import os
import re
import pytest
from atm.ui.api import BackendApi

def get_file_content(relative_path):
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.join(base_dir, relative_path)
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()

def test_settings_concurrency_guards_exist():
    """Kiểm tra biến cờ isStudioBusy và cơ chế khóa đồng thời trong settings.js."""
    content = get_file_content("atm/ui/web/js/features/settings.js")

    # 1. State flags
    assert "let isStudioBusy = false;" in content
    assert "const setStudioBusy = (busy," in content

    # 2. setStudioBusy disables interactive controls
    assert "studio-test-btn" in content
    assert "studio-save-btn" in content
    assert "studio-clear-btn" in content
    assert "studio-fetch-models-btn" in content
    assert "studio-reset-model-btn" in content
    assert "is-studio-locked" in content

    # 3. Guard conditions in all studio async operations
    assert "if (isStudioBusy)" in content
    assert "plugins.operation_in_progress" in content

    # 4. Tab switching lock
    tabs_snippet = content[content.rfind("studio-provider-tabs"):content.rfind("studio-provider-tabs") + 600]
    assert "if (isStudioBusy)" in tabs_snippet

    # 5. Change key lock
    change_key_snippet = content[content.rfind("studio-change-key-btn"):content.rfind("studio-change-key-btn") + 600]
    assert "if (isStudioBusy)" in change_key_snippet

    # 6. Change key and clear button re-enabling when busy completes
    assert "if (changeKeyBtn) changeKeyBtn.disabled = false;" in content
    assert "if (clearBtn) clearBtn.disabled = false;" in content
    assert "changeKeyBtn.disabled = isStudioBusy;" in content

    # 7. CSS pointer-events enabled for non-disabled change key button
    css_content = get_file_content("atm/ui/web/styles.css")
    assert ".btn-change-key:not(:disabled)" in css_content
    assert "pointer-events: auto;" in css_content


def test_provider_isolation_during_in_flight_requests():
    """Kiểm tra snapshot opProvider để kết quả fetch/test không ghi đè nhầm provider khác khi chuyển tab."""
    content = get_file_content("atm/ui/web/js/features/settings.js")

    # Fetch models isolation
    assert "const opProvider = currentProvider;" in content
    assert "if (currentProvider === opProvider)" in content

    # Test connection isolation
    assert "currentProvider === opProvider && resultSpan" in content


def test_reset_model_button_and_handler():
    """Kiểm tra nút Reset Model trong HTML và handler trong settings.js."""
    html_content = get_file_content("atm/ui/web/index.html")
    js_content = get_file_content("atm/ui/web/js/features/settings.js")

    # HTML button
    assert 'id="studio-reset-model-btn"' in html_content
    assert 'data-i18n-title="plugins.reset_model_btn"' in html_content

    # JS handler and binding
    assert "const handleResetModel = async () => {" in js_content
    assert "modelInput.value = defaultModel;" in js_content
    assert "resetModelBtn.addEventListener('click', handleResetModel);" in js_content
    assert "plugins.reset_model_success" in js_content


def test_clear_studio_config_supports_all_providers():
    """Kiểm tra cơ chế xóa cấu hình thống nhất cho tất cả provider (Gemini, Claude, DeepSeek, OpenAI, Kimi, Custom LLM) qua in-app modal confirm."""
    js_content = get_file_content("atm/ui/web/js/features/settings.js")

    assert "const clearStudioConfig = async (providerToClear) => {" in js_content
    assert "window.ATM.Modals.confirm" in js_content
    assert "if (!window.confirm(" not in js_content
    assert "plugins.clear_key_confirm" in js_content
    assert "plugins.clear_key_success" in js_content
    assert "custom_llm_model = '';" in js_content
    assert "custom_llm_base_url = '';" in js_content
    assert "btn-chip-remove" in js_content


def test_games_js_engine_options_unified():
    """Kiểm tra games.js kiểm tra trạng thái cấu hình của tất cả các engine đồng đều, không hardcode."""
    games_content = get_file_content("atm/ui/web/js/features/games.js")
    assert "if (!engine || engine === 'google' || engine === 'custom_llm') return true;" not in games_content
    assert "isEngineConfigured('custom_llm')" in games_content


def test_i18n_keys_parity_for_new_features():
    """Kiểm tra đầy đủ key song ngữ Việt - Anh cho tính năng chuyển/xóa model và concurrency guard."""
    from tests.unit.test_js_i18n import get_i18n_js_content, parse_keys_for_lang

    content = get_i18n_js_content()
    vi_keys = parse_keys_for_lang(content, "vi")
    en_keys = parse_keys_for_lang(content, "en")

    required_keys = [
        "plugins.clear_key_confirm",
        "plugins.clear_key_success",
        "plugins.reset_model_btn",
        "plugins.reset_model_success",
        "plugins.operation_in_progress",
        "plugins.saving_in_progress",
        "plugins.clearing_in_progress",
        "plugins.remove_profile_tooltip",
    ]

    for k in required_keys:
        assert k in vi_keys, f"Thiếu key {k} trong tiếng Việt"
        assert k in en_keys, f"Thiếu key {k} trong tiếng Anh"


def test_backend_clear_settings_integration(tmp_path, monkeypatch):
    """Kiểm tra Backend API xử lý xóa key cloud và xóa cấu hình custom_llm."""
    test_config = tmp_path / "config.json"
    monkeypatch.setattr("atm.storage.repositories.settings_repository.CONFIG_PATH", str(test_config))
    api = BackendApi()

    # 1. Cấu hình Gemini & Custom LLM
    api.update_settings(
        gemini_api_key="AIzaSy" + "K" * 35,
        gemini_model="gemini-2.5-flash",
        custom_llm_model="qwen2.5:7b",
        custom_llm_base_url="http://localhost:11434/v1"
    )

    s1 = api.get_settings()
    assert s1.get("gemini_api_key_configured") is True
    assert s1.get("custom_llm_model") == "qwen2.5:7b"

    # 2. Xóa Gemini key
    api.update_settings(gemini_api_key="")
    s2 = api.get_settings()
    assert s2.get("gemini_api_key_configured") is False

    # 3. Xóa Custom LLM
    api.update_settings(custom_llm_model="", custom_llm_base_url="")
    s3 = api.get_settings()
    assert s3.get("custom_llm_model") == ""
    assert s3.get("custom_llm_base_url") == ""


def test_fetch_available_models_http_error_detail_handling(monkeypatch):
    """Kiểm tra fetch_available_models xử lý HTTPError 401/403 kèm detail mà không phát sinh NameError."""
    import urllib.error
    import io
    from atm.ui.api import BackendApi
    api = BackendApi()

    error_body = b'{"error": {"message": "Invalid API key provided"}}'
    mock_http_error = urllib.error.HTTPError(
        url="https://api.example.com/models",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=io.BytesIO(error_body)
    )

    def mock_urlopen(*args, **kwargs):
        raise mock_http_error

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    res = api.fetch_available_models("openai", api_key="sk-invalid")
    assert res.get("status") == "error"
    assert res.get("code") == "error.api_unauthorized"
    assert "Invalid API key provided" in res.get("error")
    assert "NameError" not in res.get("error")
