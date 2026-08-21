import uuid
import pytest
from pydantic import ValidationError
from atm.config.schema import GameProfile, AppSettings


def test_game_profile_default_values():
    """Kiểm tra các giá trị mặc định của GameProfile schema."""
    profile = GameProfile(
        game_name="Demo Game",
        exe_path="C:/Games/Demo/game.exe"
    )
    
    assert profile.version == 1
    assert profile.game_name == "Demo Game"
    assert profile.exe_path == "C:/Games/Demo/game.exe"
    assert profile.engine == "Unity IL2CPP"
    assert profile.translator == "google"
    assert profile.input_lang == "ja"
    assert profile.output_lang == "vi"
    assert isinstance(profile.id, str)
    assert len(profile.id) > 0


def test_game_profile_id_auto_generation():
    """Kiểm tra việc tự động tạo ID duy nhất (UUID4) cho các bản ghi khác nhau."""
    profile1 = GameProfile(game_name="Game 1", exe_path="C:/Game1/game.exe")
    profile2 = GameProfile(game_name="Game 2", exe_path="C:/Game2/game.exe")
    
    # Đảm bảo ID không rỗng và hợp lệ dạng UUID
    uuid.UUID(profile1.id)
    uuid.UUID(profile2.id)
    
    # Hai đối tượng phải có ID khác nhau
    assert profile1.id != profile2.id


def test_game_profile_validation():
    """Kiểm tra Pydantic validation khi thiếu các trường bắt buộc (game_name, exe_path)."""
    with pytest.raises(ValidationError):
        # Thiếu exe_path và game_name
        GameProfile()

    with pytest.raises(ValidationError):
        # Thiếu exe_path
        GameProfile(game_name="Incomplete Game")


def test_game_profile_custom_values():
    """Kiểm tra GameProfile khi truyền vào các giá trị tùy chỉnh."""
    custom_id = str(uuid.uuid4())
    profile = GameProfile(
        version=2,
        id=custom_id,
        game_name="Custom Game",
        exe_path="D:/Games/Custom/main.exe",
        engine="RenPy",
        translator="deepl",
        input_lang="en",
        output_lang="vi"
    )
    
    assert profile.version == 2
    assert profile.id == custom_id
    assert profile.game_name == "Custom Game"
    assert profile.exe_path == "D:/Games/Custom/main.exe"
    assert profile.engine == "RenPy"
    assert profile.translator == "deepl"
    assert profile.input_lang == "en"
    assert profile.output_lang == "vi"


def test_app_settings_defaults():
    """Kiểm tra cấu hình chung AppSettings mặc định."""
    settings = AppSettings()
    assert settings.version == 1
    assert settings.auto_update is True
    assert settings.dark_mode is True
    assert settings.ui_language == "vi"
