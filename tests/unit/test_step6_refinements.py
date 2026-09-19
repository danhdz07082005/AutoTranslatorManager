import re
import os
from pathlib import Path
import pytest
from atm.config.schema import AppSettings
from atm.ui.server import ATMHandler


def test_default_models_schema():
    """Verify default models are updated to 2026 modern standards."""
    cfg = AppSettings()
    assert cfg.gemini_model == "gemini-2.5-flash"
    assert cfg.claude_model == "claude-3-7-sonnet-20250219"


def test_process_monitor_uses_list_args():
    """Verify process_monitor.py launches subprocess with a list [exe_path] to handle spaces safely."""
    path = Path(__file__).resolve().parents[2] / "atm" / "core" / "deployment" / "process_monitor.py"
    content = path.read_text(encoding="utf-8")
    assert "subprocess.Popen([exe_path], cwd=cwd)" in content or "subprocess.Popen([exe_path]" in content
    assert "subprocess.Popen(exe_path, cwd=cwd)" not in content


def test_server_mime_charset_utf8():
    """Verify server.py sets charset=utf-8 for html, css, js, json."""
    path = Path(__file__).resolve().parents[2] / "atm" / "ui" / "server.py"
    content = path.read_text(encoding="utf-8")
    assert "text/html; charset=utf-8" in content
    assert "text/css; charset=utf-8" in content
    assert "application/javascript; charset=utf-8" in content
    assert "application/json; charset=utf-8" in content


def test_bakin_beta_badge_in_frontend():
    """Verify Bakin is marked with (BETA) badge in games.js, workspace.js, and data.js."""
    base = Path(__file__).resolve().parents[2] / "atm" / "ui" / "web" / "js" / "features"
    for fname in ["games.js", "workspace.js", "data.js"]:
        content = (base / fname).read_text(encoding="utf-8")
        assert "Bakin (BETA)" in content, f"Missing Bakin (BETA) badge in {fname}"


def test_settings_js_zero_hardcoded_vietnamese():
    """Verify settings.js has zero Vietnamese diacritics in executable code."""
    path = Path(__file__).resolve().parents[2] / "atm" / "ui" / "web" / "js" / "features" / "settings.js"
    vn_regex = re.compile(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', re.IGNORECASE)
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            s = line.strip()
            if s.startswith("//") or s.startswith("/*") or s.startswith("*"):
                continue
            assert not vn_regex.search(line), f"Found Vietnamese string in settings.js line {idx}: {s}"


def test_i18n_key_too_short_parity():
    """Verify key_too_short error keys exist in both vi and en dictionaries."""
    path = Path(__file__).resolve().parents[2] / "atm" / "ui" / "web" / "js" / "core" / "i18n.js"
    content = path.read_text(encoding="utf-8")
    for key in ["error.key_too_short_5", "error.key_too_short_deepl", "error.key_too_short_general"]:
        matches = re.findall(rf"['\"]{re.escape(key)}['\"]\s*:", content)
        assert len(matches) >= 2, f"Key {key} must exist in both vi and en (found {len(matches)})"


def test_delete_game_cleans_translated_marker(tmp_path, isolate_test_environment):
    """Verify delete_game removes .atm_translated marker if present."""
    from atm.ui.api import BackendApi
    from atm.config.schema import GameProfile

    game_dir = tmp_path / "TestGame"
    game_dir.mkdir()
    marker_file = game_dir / ".atm_translated"
    marker_file.write_text("done", encoding="utf-8")
    assert marker_file.exists()

    api = BackendApi()
    profile = GameProfile(
        game_name="Test Game",
        exe_path=str(game_dir / "game.exe"),
        engine="RenPy"
    )
    api.profile_repo.save(profile)

    res = api.delete_game(profile.id)
    assert res.get("status") == "success"
    assert not marker_file.exists(), ".atm_translated marker should have been cleaned up on delete_game"
