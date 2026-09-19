import pytest
import os
from atm.config.schema import GameProfile
from atm.core.events.event_bus import EventBus
from atm.core.translation.cache_manager import TranslationCache
from atm.core.translation.translation_memory import TranslationMemory


@pytest.fixture
def sample_game_profile():
    """
    Fixture tạo một đối tượng GameProfile giả lập dùng chung cho các test case.
    """
    return GameProfile(
        game_name="Test Visual Novel",
        exe_path="C:/Games/TestVN/game.exe",
        engine="Unity IL2CPP",
        translator="google",
        input_lang="ja",
        output_lang="vi"
    )


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """
    Auto-use fixture that isolates EVERY test from the real data/ directory.
    Prevents tests from ever touching or polluting production data.
    """
    sandbox_data = tmp_path / "sandbox_data"
    sandbox_data.mkdir(parents=True, exist_ok=True)
    
    profiles_dir = sandbox_data / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    
    jobs_dir = sandbox_data / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    
    translations_dir = sandbox_data / "translations"
    translations_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = str(sandbox_data / "config.json")
    
    # Patch paths functions
    monkeypatch.setattr("atm.utils.paths.get_app_data_dir", lambda: str(sandbox_data))
    monkeypatch.setattr("atm.utils.paths.get_profiles_dir", lambda: str(profiles_dir))
    monkeypatch.setattr("atm.utils.paths.get_translations_dir", lambda: str(translations_dir))
    
    # Patch repository constants
    monkeypatch.setattr("atm.storage.repositories.profile_repository.PROFILES_DIR", str(profiles_dir))
    monkeypatch.setattr("atm.storage.repositories.job_repository.JOBS_DIR", str(jobs_dir))
    monkeypatch.setattr("atm.storage.repositories.settings_repository.CONFIG_PATH", config_path)
    monkeypatch.setattr("atm.storage.repositories.translation_repository.TRANSLATIONS_DIR", str(translations_dir))
    
    # Reset singletons
    TranslationCache._instance = None
    TranslationMemory._instance = None
    
    yield sandbox_data
    
    TranslationCache._instance = None
    TranslationMemory._instance = None


@pytest.fixture
def temp_profiles_dir(isolate_test_environment):
    """Backward compatibility fixture for tests explicitly asking for temp_profiles_dir."""
    from pathlib import Path
    return Path(isolate_test_environment) / "profiles"


