import pytest
import time
import threading
from atm.core.jobs.manager import JobManager, JobStatus

def dummy_worker(cancel_token, job, duration=0.1, increments=5):
    """A dummy worker that simulates work and supports cooperative cancellation."""
    sleep_time = duration / increments
    for i in range(increments):
        if cancel_token.is_set():
            break
        time.sleep(sleep_time)
        job.update_progress(i + 1, increments, f"Step {i+1}")

def test_job_submit_and_complete():
    manager = JobManager(max_workers=2)
    res = manager.submit_job("extract", "game_1", dummy_worker, duration=0.1)
    assert res["status"] == "queued"
    job_id = res["job_id"]
    
    # Wait for completion
    time.sleep(0.2)
    status = manager.get_job_status(job_id)
    assert status is not None
    assert status["status"] == JobStatus.COMPLETED
    assert status["progress"]["percent"] == 100

def test_deduplication():
    manager = JobManager(max_workers=2)
    # Submit first job, it should take a little time
    res1 = manager.submit_job("extract", "game_dedup", dummy_worker, duration=0.5)
    assert res1["status"] == "queued"
    
    # Immediately submit second job for the same game and type
    res2 = manager.submit_job("extract", "game_dedup", dummy_worker, duration=0.5)
    assert res2["status"] == "already_running"
    assert res2["job_id"] == res1["job_id"]

def test_concurrent_deduplication():
    """Test 5 threads submitting the same job concurrently to ensure lock works."""
    manager = JobManager(max_workers=2)
    results = []
    
    def submitter():
        res = manager.submit_job("extract", "game_concurrent", dummy_worker, duration=0.5)
        results.append(res)
        
    threads = [threading.Thread(target=submitter) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    queued_count = sum(1 for r in results if r["status"] == "queued")
    already_running_count = sum(1 for r in results if r["status"] == "already_running")
    
    assert queued_count == 1
    assert already_running_count == 4

def test_cancellation():
    manager = JobManager(max_workers=2)
    res = manager.submit_job("extract", "game_cancel", dummy_worker, duration=1.0)
    job_id = res["job_id"]
    
    # Let it start
    time.sleep(0.1)
    
    assert manager.cancel_job(job_id) is True
    
    # Wait for the worker to exit cooperatively
    time.sleep(0.3)
    status = manager.get_job_status(job_id)
    assert status["status"] == JobStatus.CANCELLED

def test_cleanup_old_jobs():
    manager = JobManager(max_workers=2)
    res = manager.submit_job("extract", "game_clean", dummy_worker, duration=0.1)
    time.sleep(0.2)
    
    status = manager.get_job_status(res["job_id"])
    assert status["status"] == JobStatus.COMPLETED
    
    # Should not clean up if TTL is high
    manager.cleanup_old_jobs(ttl_seconds=100)
    assert manager.get_job_status(res["job_id"]) is not None
    
    # Should clean up if TTL is 0
    manager.cleanup_old_jobs(ttl_seconds=0)
    assert manager.get_job_status(res["job_id"]) is None

def test_shutdown():
    manager = JobManager(max_workers=2)
    res = manager.submit_job("extract", "game_shutdown", dummy_worker, duration=1.0)
    
    # Shutdown should cooperatively cancel running jobs and block new ones
    manager.shutdown(wait=True)
    
    res2 = manager.submit_job("extract", "game_after_shutdown", dummy_worker, duration=0.1)
    assert res2["status"] == "failed"
    assert "shutting down" in res2["error"]
    
    # The first job should have been cancelled by the shutdown
    status = manager.get_job_status(res["job_id"])
    assert status["status"] == JobStatus.CANCELLED
