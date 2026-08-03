import os
import json
from atm.storage.repositories.profile_repository import ProfileRepository
from atm.config.schema import GameProfile


def test_save_and_get_by_id(temp_profiles_dir, sample_game_profile):
    """Kiểm tra lưu profile vào file JSON và lấy lại bằng ID."""
    repo = ProfileRepository()
    repo.save(sample_game_profile)
    
    # Kiểm tra file json thực sự tồn tại trong thư mục tạm
    expected_file = temp_profiles_dir / f"{sample_game_profile.id}.json"
    assert expected_file.exists()
    
    # Lấy profile bằng ID
    loaded_profile = repo.get_by_id(sample_game_profile.id)
    assert loaded_profile is not None
    assert loaded_profile.id == sample_game_profile.id
    assert loaded_profile.game_name == sample_game_profile.game_name
    assert loaded_profile.exe_path == sample_game_profile.exe_path


def test_load_existing_and_non_existing(temp_profiles_dir, sample_game_profile):
    """Kiểm tra phương thức load với file tồn tại và không tồn tại."""
    repo = ProfileRepository()
    repo.save(sample_game_profile)
    
    filename = f"{sample_game_profile.id}.json"
    loaded = repo.load(filename)
    assert loaded is not None
    assert loaded.id == sample_game_profile.id
    
    # Load file không tồn tại
    non_existent = repo.load("non_existent_profile.json")
    assert non_existent is None


def test_get_all_profiles(temp_profiles_dir):
    """Kiểm tra lấy toàn bộ danh sách Game Profile."""
    repo = ProfileRepository()
    
    # Ban đầu chưa có profile nào
    assert len(repo.get_all()) == 0
    
    # Tạo 3 profiles
    p1 = GameProfile(game_name="Game 1", exe_path="C:/G1/game.exe")
    p2 = GameProfile(game_name="Game 2", exe_path="C:/G2/game.exe")
    p3 = GameProfile(game_name="Game 3", exe_path="C:/G3/game.exe")
    
    repo.save(p1)
    repo.save(p2)
    repo.save(p3)
    
    all_profiles = repo.get_all()
    assert len(all_profiles) == 3
    loaded_ids = {p.id for p in all_profiles}
    assert loaded_ids == {p1.id, p2.id, p3.id}


def test_delete_profile(temp_profiles_dir, sample_game_profile):
    """Kiểm tra xóa game profile theo ID."""
    repo = ProfileRepository()
    repo.save(sample_game_profile)
    
    # Xác nhận đã lưu
    assert repo.get_by_id(sample_game_profile.id) is not None
    
    # Xóa thành công
    deleted = repo.delete(sample_game_profile.id)
    assert deleted is True
    assert repo.get_by_id(sample_game_profile.id) is None
    
    # Xóa ID không tồn tại
    deleted_again = repo.delete("non_existent_id")
    assert deleted_again is False


def test_load_corrupted_json(temp_profiles_dir):
    """Kiểm tra xử lý ngoại lệ khi file JSON bị lỏng/hỏng dữ liệu."""
    repo = ProfileRepository()
    corrupted_file = temp_profiles_dir / "invalid.json"
    
    # Ghi nội dung JSON không hợp lệ
    with open(corrupted_file, "w", encoding="utf-8") as f:
        f.write("{ invalid json content ...")
        
    result = repo.load("invalid.json")
    assert result is None
