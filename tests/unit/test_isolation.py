import os
from atm.ui.api import BackendApi
from atm.config.schema import GameProfile
from atm.storage.repositories.job_repository import JobRepository, TranslationJob

def test_delete_game_deletes_associated_job(isolate_test_environment):
    api = BackendApi()
    profile = GameProfile(
        game_name='TestVN',
        exe_path='C:/Games/TestVN/game.exe',
        engine='Unity Mono'
    )
    api.profile_repo.save(profile)
    
    # Save a job
    job_repo = JobRepository()
    job_repo.save(TranslationJob(game_id=profile.id, status='completed'))
    assert job_repo.load(profile.id) is not None
    
    # Delete game with purge_data=True (full purge)
    res = api.delete_game(profile.id, purge_data=True)
    assert res['status'] == 'success'
    
    # Job should be deleted as well
    assert job_repo.load(profile.id) is None
    assert api.profile_repo.get_by_id(profile.id) is None
