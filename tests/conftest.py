import pytest
import os
from atm.config.schema import GameProfile
from atm.core.events.event_bus import EventBus


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


@pytest.fixture
def temp_profiles_dir(tmp_path, monkeypatch):
    """
    Fixture tạo thư mục profiles tạm thời trong tmp_path và monkeypatch PROFILES_DIR
    để đảm bảo không làm ảnh hưởng đến dữ liệu profiles thật.
    """
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    
    # Patch biến PROFILES_DIR trong module profile_repository
    monkeypatch.setattr(
        "atm.storage.repositories.profile_repository.PROFILES_DIR",
        str(profiles_dir)
    )
    return profiles_dir

