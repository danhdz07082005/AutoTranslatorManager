from unittest.mock import MagicMock
from atm.ui.api import BackendApi


def test_full_api_game_lifecycle_flow(temp_profiles_dir, tmp_path, monkeypatch):
    """
    Test tích hợp luồng nghiệp vụ hoàn chỉnh của BackendApi:
    add_game -> get_games -> update_game_lang -> delete_game
    """
    # 1. Chuẩn bị file game giả lập
    game_dir = tmp_path / "VN_Game"
    game_dir.mkdir()
    exe_file = game_dir / "VN_Launcher.exe"
    exe_file.touch()
    
    # Tạo thư mục Unity IL2CPP để GameDetector nhận diện
    data_dir = game_dir / "VN_Launcher_Data"
    data_dir.mkdir()
    (data_dir / "il2cpp_data").mkdir()

    # Khởi tạo BackendApi và giả lập tkinter dialog
    api = BackendApi()
    mock_askopenfilename = MagicMock(return_value=str(exe_file))
    monkeypatch.setattr("tkinter.filedialog.askopenfilename", mock_askopenfilename)

    # STEP 1: Thêm game mới (add_game)
    add_res = api.add_game()
    assert add_res is not None
    assert add_res.get("status") == "success"
    game_data = add_res.get("game")
    assert game_data is not None
    game_id = game_data["id"]
    assert game_data["game_name"] == "VN_Game"
    assert game_data["engine"] == "Unity IL2CPP"

    # STEP 2: Lấy danh sách game (get_games)
    games_res = api.get_games()
    games = games_res.get("games", [])
    assert len(games) == 1
    assert games[0]["id"] == game_id

    # STEP 3: Cập nhật settings game
    update_res = api.update_game_settings(game_id, input_lang="en", output_lang="ja", translator="deepl", glossary={})
    assert update_res.get("status") == "success"
    games_res_after = api.get_games()
    updated_game = next(g for g in games_res_after.get("games", []) if g["id"] == game_id)
    assert updated_game["input_lang"] == "en"
    assert updated_game["output_lang"] == "ja"
    assert updated_game["translator"] == "deepl"

    # STEP 4: Xóa game (delete_game)
    del_res = api.delete_game(game_id)
    assert del_res.get("status") == "success"
    games_res_final = api.get_games()
    assert len(games_res_final.get("games", [])) == 0


def test_add_game_cancelled_dialog(temp_profiles_dir, monkeypatch):
    """Kiểm tra khi người dùng hủy chọn file trong hộp thoại dialog."""
    api = BackendApi()
    # Giả lập người dùng bấm Cancel (trả về chuỗi rỗng)
    mock_askopenfilename = MagicMock(return_value="")
    monkeypatch.setattr("tkinter.filedialog.askopenfilename", mock_askopenfilename)

    result = api.add_game()
    assert result == {"status": "cancelled"}
    assert len(api.get_games().get("games", [])) == 0


def test_update_non_existent_game(temp_profiles_dir):
    """Kiểm tra báo lỗi khi cập nhật ngôn ngữ cho game ID không tồn tại."""
    api = BackendApi()
    res = api.update_game_settings("invalid_game_id_123", "en", "vi", "google")
    assert res["status"] == "error"
    assert "Game not found" in res.get("error", "")


def test_get_languages():
    """Kiểm tra API trả về danh sách các ngôn ngữ hỗ trợ."""
    api = BackendApi()
    languages = api.get_languages()
    assert isinstance(languages, dict)
    assert "ja" in languages
    assert "vi" in languages
    assert "en" in languages
