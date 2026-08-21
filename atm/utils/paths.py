import os
import sys

def get_app_data_dir() -> str:
    """Get the canonical application data directory.
    If running as a PyInstaller executable, uses %LOCALAPPDATA%/AutoTranslatorManager.
    Otherwise (dev mode), uses the local ./data folder.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        local_app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        app_data_dir = os.path.join(local_app_data, 'AutoTranslatorManager')
    else:
        # Running from source
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        app_data_dir = os.path.join(base_dir, 'data')
    
    os.makedirs(app_data_dir, exist_ok=True)
    return app_data_dir

def get_profiles_dir() -> str:
    path = os.path.join(get_app_data_dir(), 'profiles')
    os.makedirs(path, exist_ok=True)
    return path

def get_cache_dir() -> str:
    path = os.path.join(get_app_data_dir(), 'cache')
    os.makedirs(path, exist_ok=True)
    return path

def get_memory_dir() -> str:
    path = os.path.join(get_app_data_dir(), 'memory')
    os.makedirs(path, exist_ok=True)
    return path

def get_games_dir() -> str:
    path = os.path.join(get_app_data_dir(), 'games')
    os.makedirs(path, exist_ok=True)
    return path

def get_translations_dir() -> str:
    path = os.path.join(get_app_data_dir(), 'translations')
    os.makedirs(path, exist_ok=True)
    return path
