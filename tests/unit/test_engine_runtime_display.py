from pathlib import Path
import re
from atm.core.translation.renpy_translator import RenPyTranslator
from atm.core.translation.classification import classify, WritePolicy, StringClassification

def test_renpy_language_config_init_999_and_persistent(tmp_path: Path):
    game_dir = tmp_path / "game"
    game_dir.mkdir(parents=True)
    
    RenPyTranslator._inject_language_config(game_dir, "vi")
    
    inject_file = game_dir / "atm_language_config.rpy"
    assert inject_file.exists(), "atm_language_config.rpy must be created in game/ folder"
    
    text = inject_file.read_text(encoding="utf-8")
    assert "init 999 python:" in text, "Must use init 999 to execute after game options.rpy default assignments"
    assert "config.language = 'vi'" in text
    assert "_preferences.language = 'vi'" in text
    assert "persistent._atm_lang_initialized" in text

def test_settings_js_multi_model_suggestion_guards():
    settings_js_path = Path("atm/ui/web/js/features/settings.js")
    assert settings_js_path.exists()
    content = settings_js_path.read_text(encoding="utf-8")
    
    # Verify exact match guard
    assert "meta.models.some" in content, "Must guard against suggesting for already-known exact models"
    # Verify dated/versioned suffix guard
    assert "claude-[a-z0-9" in content, "Must guard official dated/versioned Claude model identifiers"
    # Verify multi-provider coverage in suggestModelName
    assert "prov === 'kimi'" in content, "Must support Kimi suggestions"
    assert "gemini-1.5-flash" in content, "Must support Gemini 1.5 suggestions"
    assert "deepseek-chat" in content, "Must support DeepSeek suggestions"
    assert "gpt-4o-mini" in content, "Must support OpenAI suggestions"

def test_settings_js_draft_sync_on_tab_switch():
    settings_js_path = Path("atm/ui/web/js/features/settings.js")
    content = settings_js_path.read_text(encoding="utf-8")
    
    assert "const syncDraftInputs = () => {" in content, "Must define syncDraftInputs helper"
    assert "syncDraftInputs();" in content, "Must invoke syncDraftInputs before changing provider"
    assert "currentSettings[`${currentProvider}_model`] = e.target.value.trim();" in content
    assert "currentSettings[`${currentProvider}_base_url`] = e.target.value.trim();" in content

def test_rpgmaker_runtime_display_parity():
    # 1. Dialogue events must be WRITE_BACK so they persist directly to Map files
    cls, wp = classify("Hello hero", ["events", 1, "pages", 0, "list", 2, "parameters", 0], "Map001.json", event_code=401, inside_event_parameters=True)
    assert wp == WritePolicy.WRITE_BACK, "Map dialogue events must be WRITE_BACK"
    assert cls == StringClassification.TRANSLATABLE

    # 2. System terms must be DISPLAY_ONLY to prevent Yanfly/plugin script crash while overlay patches in RAM
    cls_sys, wp_sys = classify("Game Title", ["gameTitle"], "System.json")
    assert wp_sys == WritePolicy.DISPLAY_ONLY, "System terms must be DISPLAY_ONLY for overlay"
    assert cls_sys == StringClassification.TRANSLATABLE

def test_unity_deployer_runtime_auto_and_google(tmp_path: Path):
    from atm.config.schema import GameProfile
    from atm.core.deployment.game_deployer import GameDeployer
    from unittest.mock import MagicMock, patch
    import configparser

    game_dir = tmp_path / "ChineseExeName"
    game_dir.mkdir()
    exe_path = game_dir / "冒險途中全員告白.exe"
    exe_path.touch()

    # Test 1: Google translator with input_lang='auto' must keep FromLanguage='auto' and Endpoint='GoogleTranslate'
    profile_google = GameProfile(
        game_name="Love Confessions on the Adventure",
        exe_path=str(exe_path),
        engine="Unity Mono",
        translator="google",
        input_lang="auto",
        output_lang="vi"
    )

    deployer = GameDeployer()
    deployer.monitor = MagicMock()
    deployer.monitor.start_and_monitor.return_value = True

    deployer.deploy_and_launch(profile_google, payload_dir="")

    ini_file = game_dir / "BepInEx" / "config" / "AutoTranslatorConfig.ini"
    assert ini_file.exists()
    cp = configparser.ConfigParser()
    cp.read(ini_file, encoding="utf-8")

    assert cp.get("Service", "Endpoint") == "CustomTranslate"
    assert cp.has_section("Custom")
    assert f"http://127.0.0.1:5000/api/translate/unity/{profile_google.id}" in cp.get("Custom", "Url")
    assert cp.get("General", "FromLanguage") == "auto", "Must NOT force 'zh' on auto for Chinese exe filenames"
    assert cp.get("General", "Language") == "vi"
    assert cp.get("Behaviour", "FallbackFont") == "arial"
