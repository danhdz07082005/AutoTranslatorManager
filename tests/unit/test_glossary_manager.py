import pytest
from atm.config.schema import GameProfile
from atm.storage.repositories.profile_repository import ProfileRepository
from atm.core.translation.glossary_manager import GlossaryManager
import os
import tempfile
import json

class MockProfileRepo:
    def __init__(self):
        self.profiles = {
            "test_game_1": GameProfile(
                id="test_game_1",
                game_name="Test Game",
                exe_path="dummy.exe",
                engine="RenPy",
                glossary={
                    "Hello": "Xin chào",
                    "Sword": "Kiếm"
                }
            )
        }
        
    def get_by_id(self, game_id):
        return self.profiles.get(game_id)
        
    def save(self, profile):
        self.profiles[profile.id] = profile

def test_export_csv():
    repo = MockProfileRepo()
    manager = GlossaryManager(repo)
    csv_out = manager.export_glossary("test_game_1", "csv")
    assert "source,target,notes" in csv_out
    assert "Hello,Xin chào," in csv_out
    assert "Sword,Kiếm," in csv_out

def test_export_json():
    repo = MockProfileRepo()
    manager = GlossaryManager(repo)
    json_out = manager.export_glossary("test_game_1", "json")
    data = json.loads(json_out)
    assert len(data) == 2
    assert data[0]["source"] == "Hello"
    assert data[0]["target"] == "Xin chào"

def test_preview_import():
    repo = MockProfileRepo()
    manager = GlossaryManager(repo)
    
    # Simulate importing a CSV that has:
    # 1. New term (Shield)
    # 2. Duplicate term (Sword -> Kiếm)
    # 3. Conflict term (Hello -> Chào bạn)
    # 4. Invalid term (missing source/target)
    csv_content = "source,target,notes\nShield,Khiên,\nSword,Kiếm,\nHello,Chào bạn,\n,Lỗi,"
    
    preview = manager.preview_import("test_game_1", csv_content, "csv")
    
    assert len(preview["new"]) == 1
    assert preview["new"][0]["source"] == "Shield"
    
    assert len(preview["duplicate"]) == 1
    assert preview["duplicate"][0]["source"] == "Sword"
    
    assert len(preview["conflict"]) == 1
    assert preview["conflict"][0]["source"] == "Hello"
    assert preview["conflict"][0]["target"] == "Chào bạn"
    assert preview["conflict"][0]["existing_target"] == "Xin chào"
    
    assert len(preview["invalid"]) == 1

def test_apply_import_merge():
    repo = MockProfileRepo()
    manager = GlossaryManager(repo)
    
    new_data = [
        {"source": "Shield", "target": "Khiên"},
        {"source": "Hello", "target": "Chào bạn"} # Conflict update
    ]
    
    manager.apply_import("test_game_1", new_data, strategy="merge")
    
    profile = repo.get_by_id("test_game_1")
    assert len(profile.glossary) == 3 # Hello (updated), Sword (kept), Shield (new)
    assert profile.glossary["Hello"] == "Chào bạn"
    assert profile.glossary["Shield"] == "Khiên"

def test_apply_import_replace():
    repo = MockProfileRepo()
    manager = GlossaryManager(repo)
    
    new_data = [
        {"source": "Shield", "target": "Khiên"}
    ]
    
    manager.apply_import("test_game_1", new_data, strategy="replace")
    
    profile = repo.get_by_id("test_game_1")
    assert len(profile.glossary) == 1 # Only Shield remains
    assert profile.glossary.get("Shield") == "Khiên"
