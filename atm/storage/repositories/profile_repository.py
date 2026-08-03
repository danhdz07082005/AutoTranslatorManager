import json
import os
from typing import List, Optional
from pydantic import ValidationError
from atm.config.schema import GameProfile
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "profiles")

class ProfileRepository:
    """Quản lý Game Profiles (.json)."""
    
    def __init__(self) -> None:
        if not os.path.exists(PROFILES_DIR):
            os.makedirs(PROFILES_DIR, exist_ok=True)
            
    def get_all(self) -> List[GameProfile]:
        profiles = []
        for filename in os.listdir(PROFILES_DIR):
            if filename.endswith(".json"):
                profile = self.load(filename)
                if profile:
                    profiles.append(profile)
        return profiles
        
    def load(self, filename: str) -> Optional[GameProfile]:
        filepath = os.path.join(PROFILES_DIR, filename)
        if not os.path.exists(filepath):
            return None
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return GameProfile(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Error loading profile {filename}: {e}")
            return None
            
    def save(self, profile: GameProfile) -> None:
        filename = f"{profile.id}.json"
        filepath = os.path.join(PROFILES_DIR, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(profile.model_dump_json(indent=4))
            logger.info(f"Saved profile to {filename}")
        except Exception as e:
            logger.error(f"Failed to save profile {filename}: {e}")
            
    def delete(self, game_id: str) -> bool:
        filename = f"{game_id}.json"
        filepath = os.path.join(PROFILES_DIR, filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"Deleted profile {filename}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete profile {filename}: {e}")
        return False
        
    def get_by_id(self, game_id: str) -> Optional[GameProfile]:
        filename = f"{game_id}.json"
        return self.load(filename)
