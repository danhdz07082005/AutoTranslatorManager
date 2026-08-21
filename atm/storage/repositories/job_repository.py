import json
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from atm.utils.paths import get_app_data_dir
from atm.utils.logger import get_logger
from atm.storage.repositories.json_storage import atomic_write

logger = get_logger(__name__, "launcher.log")

class TranslationJob(BaseModel):
    game_id: str
    status: str = "idle"  # idle, running, paused, completed, error
    progress: int = 0
    total: int = 0
    message_code: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)
    error_details: str = ""

JOBS_DIR = os.path.join(get_app_data_dir(), "jobs")

class JobRepository:
    def __init__(self):
        if not os.path.exists(JOBS_DIR):
            os.makedirs(JOBS_DIR, exist_ok=True)
            
    def save(self, job: TranslationJob) -> None:
        filepath = os.path.join(JOBS_DIR, f"{job.game_id}.json")
        atomic_write(filepath, job.model_dump_json(indent=4))
            
    def load(self, game_id: str) -> Optional[TranslationJob]:
        filepath = os.path.join(JOBS_DIR, f"{game_id}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return TranslationJob(**data)
        except Exception as e:
            logger.error(f"Failed to load job {game_id}: {e}")
            return None

    def get_all(self):
        jobs = []
        if not os.path.exists(JOBS_DIR):
            return jobs
        for filename in os.listdir(JOBS_DIR):
            if filename.endswith(".json"):
                game_id = filename[:-5]
                job = self.load(game_id)
                if job:
                    jobs.append(job)
        return jobs
            
    def delete(self, game_id: str) -> bool:
        filepath = os.path.join(JOBS_DIR, f"{game_id}.json")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                return True
            except OSError:
                pass
        return False
