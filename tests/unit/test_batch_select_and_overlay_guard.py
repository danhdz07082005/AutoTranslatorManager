import os
import re
from pathlib import Path
import pytest
from atm.config.schema import GameProfile
from atm.ui.api import BackendApi

REPO_ROOT = Path(__file__).resolve().parents[2]

def test_i18n_batch_select_keys():
    i18n_path = REPO_ROOT / 'atm' / 'ui' / 'web' / 'js' / 'core' / 'i18n.js'
    content = i18n_path.read_text(encoding='utf-8')
    
    required_keys = [
        'games.btn_select',
        'games.btn_select_all',
        'games.btn_deselect_all',
        'games.btn_delete_selected',
        'games.btn_cancel_select',
        'games.delete_multiple_confirm',
        'games.delete_multiple_success',
        'games.no_game_selected',
    ]
    
    for key in required_keys:
        assert key in content, f'Missing {key} in i18n.js'

def test_html_selection_elements():
    html_path = REPO_ROOT / 'atm' / 'ui' / 'web' / 'index.html'
    content = html_path.read_text(encoding='utf-8')
    
    assert 'id="games-select-mode-btn"' in content
    assert 'id="games-selection-controls"' in content
    assert 'id="games-select-all-btn"' in content
    assert 'id="games-delete-selected-btn"' in content
    assert 'id="games-cancel-select-btn"' in content
    assert 'class="game-card-checkbox"' in content
    assert 'class="btn-outline-theme"' in content
    assert 'class="btn-outline-danger"' in content

def test_css_outline_buttons_and_selection_mode():
    css_path = REPO_ROOT / 'atm' / 'ui' / 'web' / 'styles.css'
    content = css_path.read_text(encoding='utf-8')
    
    assert '.btn-outline-theme' in content
    assert '.btn-outline-danger' in content
    assert '.btn-outline-secondary' in content
    assert '.games-grid.selection-mode' in content
    assert '.game-card-select-col' in content

def test_rpgmaker_overlay_guard(tmp_path):
    # Setup dummy RPG Maker directory
    game_dir = tmp_path / 'game'
    js_dir = game_dir / 'js'
    plugins_dir = js_dir / 'plugins'
    plugins_dir.mkdir(parents=True)
    
    plugins_js = js_dir / 'plugins.js'
    plugins_js.write_text(
        'var $plugins = [{"name":"ATM_Overlay","status":true,"description":"","parameters":{}},{"name":"Other","status":true,"parameters":{}}];',
        encoding='utf-8-sig'
    )
    
    exe_file = game_dir / 'Game.exe'
    exe_file.write_text('', encoding='utf-8')
    
    # Instantiate BackendApi
    api = BackendApi()
    profile = GameProfile(
        id='test-game-rpgm',
        game_name='Test RPGM',
        exe_path=str(exe_file),
        engine='RPG Maker'
    )
    
    # Call _revert_game_directory
    api._revert_game_directory(profile, str(game_dir))
    
    # Check that plugins.js was unpatched
    updated_pjs = plugins_js.read_text(encoding='utf-8-sig')
    assert 'ATM_Overlay' not in updated_pjs
    assert 'Other' in updated_pjs
