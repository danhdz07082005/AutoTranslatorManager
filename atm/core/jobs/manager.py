from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Dict, Any, Optional

from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Job:
    def __init__(self, job_type: str, game_id: str):
        self.job_id: str = str(uuid.uuid4())
        self.type: str = job_type
        self.game_id: str = game_id
        self.status: str = JobStatus.QUEUED
        self.progress: Dict[str, Any] = {
            "mode": "indeterminate",
            "current": 0,
            "total": 0,
            "percent": 0
        }
        self.error_code: Optional[str] = None
        self.message: str = "Queued..."
        self.cancel_token: threading.Event = threading.Event()
        self.created_at: float = time.time()
        self.updated_at: float = self.created_at
        
        self._future: Optional[Future] = None

    def update_progress(self, current: int, total: int = 0, message: str = ""):
        self.updated_at = time.time()
        if message:
            self.message = message
        
        if total > 0:
            self.progress["mode"] = "determinate"
            self.progress["total"] = total
            self.progress["current"] = current
            self.progress["percent"] = min(100, int((current / total) * 100))
        else:
            self.progress["mode"] = "indeterminate"
            self.progress["current"] = current

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "type": self.type,
            "game_id": self.game_id,
            "status": self.status,
            "progress": self.progress,
            "error_code": self.error_code,
            "message": self.message,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class JobManager:
    """Manages background jobs using a ThreadPoolExecutor with deduplication and safe shutdown."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._is_shutting_down = False

    def submit_job(self, job_type: str, game_id: str, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Submit a job with deduplication based on job_type and game_id."""
        with self._lock:
            if self._is_shutting_down:
                return {"error": "System is shutting down", "status": "failed"}

            # Deduplication: Check if there's already an active job for this game and type
            for existing_job in self.jobs.values():
                if existing_job.game_id == game_id and existing_job.type == job_type:
                    if existing_job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                        logger.info(f"Job {job_type} for game {game_id} is already running (Job ID: {existing_job.job_id}).")
                        return {"status": "already_running", "job_id": existing_job.job_id}

            job = Job(job_type, game_id)
            self.jobs[job.job_id] = job
            
            # Pass the cancel_token and job reference to the worker if it accepts it
            kwargs['cancel_token'] = job.cancel_token
            kwargs['job'] = job

            def _worker_wrapper(job_obj: Job, target_func: Callable, f_args: tuple, f_kwargs: dict):
                job_obj.status = JobStatus.RUNNING
                job_obj.updated_at = time.time()
                try:
                    target_func(*f_args, **f_kwargs)
                    if job_obj.cancel_token.is_set():
                        job_obj.status = JobStatus.CANCELLED
                        job_obj.message = "Job cancelled."
                    else:
                        job_obj.status = JobStatus.COMPLETED
                        job_obj.message = "Job completed successfully."
                except Exception as e:
                    logger.error(f"Job {job_obj.job_id} failed: {e}", exc_info=True)
                    job_obj.status = JobStatus.FAILED
                    job_obj.error_code = type(e).__name__
                    job_obj.message = str(e)
                finally:
                    job_obj.updated_at = time.time()
                    
            job._future = self.executor.submit(_worker_wrapper, job, func, args, kwargs)
            return {"status": "queued", "job_id": job.job_id}

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific job."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            return job.to_dict()

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job cooperatively."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
                
            if job.status == JobStatus.COMPLETED or job.status == JobStatus.FAILED or job.status == JobStatus.CANCELLED:
                return False
                
            job.cancel_token.set()
            
            if job.status == JobStatus.QUEUED:
                if job._future and job._future.cancel():
                    job.status = JobStatus.CANCELLED
                    job.message = "Job cancelled before running."
                    job.updated_at = time.time()
                
            return True

    def cleanup_old_jobs(self, ttl_seconds: int = 3600):
        """Remove completed, failed, or cancelled jobs older than TTL."""
        with self._lock:
            now = time.time()
            to_delete = []
            for job_id, job in self.jobs.items():
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                    if now - job.updated_at > ttl_seconds:
                        to_delete.append(job_id)
            
            for job_id in to_delete:
                del self.jobs[job_id]

    def shutdown(self, wait: bool = True):
        """Reject new jobs and shutdown the executor safely."""
        with self._lock:
            self._is_shutting_down = True
            for job in self.jobs.values():
                if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                    job.cancel_token.set()
        
        self.executor.shutdown(wait=wait)
