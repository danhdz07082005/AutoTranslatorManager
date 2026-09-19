import pytest
from unittest.mock import MagicMock, patch
from atm.ui.api import BackendApi
from atm.config.schema import GameProfile

def test_backend_api_has_get_game_lines_repo():
    api = BackendApi()
    assert hasattr(api, "_get_game_lines_repo")
    repo = api._get_game_lines_repo()
    assert repo is not None
    assert hasattr(repo, "list_by_game")

def test_get_game_translations_success(tmp_path, monkeypatch):
    api = BackendApi()
    mock_repo = MagicMock()
    mock_repo.list_by_game.return_value = {"items": [], "total": 0, "page": 1, "limit": 50}
    monkeypatch.setattr(api, "_get_game_lines_repo", lambda: mock_repo)
    
    res = api.get_game_translations("dummy_game_id")
    assert res["status"] == "success"
    assert res["data"]["items"] == []
    assert res["data"]["total"] == 0

def test_delete_glossary_terms_batch(monkeypatch):
    api = BackendApi()
    profile = GameProfile(
        id="game_123",
        game_name="Test Game",
        exe_path="dummy.exe",
        output_lang="vi",
        input_lang="en",
        glossary={"hero": "anh hùng", "sword": "kiếm", "shield": "khiên"}
    )
    
    saved_profiles = []
    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = profile
    mock_profile_repo.save.side_effect = lambda p: saved_profiles.append(p)
    api.profile_repo = mock_profile_repo
    
    res = api.delete_glossary_terms("game_123", ["hero", "shield"])
    assert res["status"] == "success"
    assert res["count"] == 2
    assert "hero" not in profile.glossary
    assert "shield" not in profile.glossary
    assert "sword" in profile.glossary
    assert len(saved_profiles) == 1

def test_glossary_ui_template_elements():
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    html_path = os.path.join(base_dir, "atm", "ui", "web", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
        
    assert 'id="glossary-select-mode-btn"' in html
    assert 'id="glossary-selection-controls"' in html
    assert 'id="glossary-select-all-btn"' in html
    assert 'id="glossary-delete-selected-btn"' in html
    assert 'id="glossary-cancel-select-btn"' in html
