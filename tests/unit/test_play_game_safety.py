import unittest
from unittest.mock import patch, MagicMock
import os
import subprocess
from atm.ui.api import BackendApi
from atm.config.schema import GameProfile

class TestPlayGameSafety(unittest.TestCase):
    def setUp(self):
        self.api = BackendApi()
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def test_play_game_rejected_when_game_translating(self):
        profile = GameProfile(
            id="trans-game-1",
            game_name="Translating Game",
            exe_path="C:\\Fake\\Game.exe",
            engine="RPG Maker",
            translator="google",
            input_lang="ja",
            output_lang="vi",
            glossary={}
        )
        self.api.profile_repo.save(profile)

        # Simulate active translation
        self.api.translation_status["trans-game-1"] = {"done": False, "running": True}

        res = self.api.play_game("trans-game-1")
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("code"), "toast.game_translating")

    def test_play_game_rejects_missing_exe(self):
        profile = GameProfile(
            id="missing-exe-game",
            game_name="Missing Exe Game",
            exe_path="C:\\NonExistentPath\\FakeGame12345.exe",
            engine="RPG Maker",
            translator="google",
            input_lang="ja",
            output_lang="vi",
            glossary={}
        )
        self.api.profile_repo.save(profile)

        res = self.api.play_game("missing-exe-game")
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("code"), "error.exe_not_found")

    def test_play_game_vanilla_detached_process(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            exe_path = os.path.join(tmp_dir, "Game.exe")
            with open(exe_path, "w") as f:
                f.write("fake exe binary")

            profile = GameProfile(
                id="vanilla-game",
                game_name="Vanilla Game",
                exe_path=exe_path,
                engine="RPG Maker",
                translator="google",
                input_lang="ja",
                output_lang="vi",
                glossary={}
            )
            self.api.profile_repo.save(profile)

            with patch("subprocess.Popen") as mock_popen:
                res = self.api.play_game("vanilla-game")
                self.assertEqual(res.get("status"), "success")
                mock_popen.assert_called_once()
                call_kwargs = mock_popen.call_args.kwargs
                self.assertEqual(call_kwargs["cwd"], tmp_dir)
                self.assertTrue(call_kwargs.get("close_fds"))
                if os.name == 'nt':
                    self.assertTrue(call_kwargs.get("creationflags") & 0x00000008)  # DETACHED_PROCESS

    def test_play_game_unity_engine_routes_to_start_game(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            exe_path = os.path.join(tmp_dir, "UnityGame.exe")
            with open(exe_path, "w") as f:
                f.write("fake unity exe binary")

            profile = GameProfile(
                id="unity-play-game",
                game_name="Unity Game",
                exe_path=exe_path,
                engine="Unity Mono",
                translator="google",
                input_lang="ja",
                output_lang="vi",
                glossary={}
            )
            self.api.profile_repo.save(profile)

            with patch.object(self.api, "start_game", return_value={"status": "success"}) as mock_start:
                res = self.api.play_game("unity-play-game")
                self.assertEqual(res.get("status"), "success")
                mock_start.assert_called_once_with("unity-play-game", auto_launch=True)

    def test_play_game_bakin_engine_launches_directly(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            exe_path = os.path.join(tmp_dir, "BakinGame.exe")
            with open(exe_path, "w") as f:
                f.write("fake bakin exe binary")

            profile = GameProfile(
                id="bakin-play-game",
                game_name="Bakin Game",
                exe_path=exe_path,
                engine="Bakin",
                translator="google",
                input_lang="ja",
                output_lang="vi",
                glossary={}
            )
            self.api.profile_repo.save(profile)

            with patch("subprocess.Popen") as mock_popen:
                res = self.api.play_game("bakin-play-game")
                self.assertEqual(res.get("status"), "success")
                mock_popen.assert_called_once()
                self.assertEqual(mock_popen.call_args.args[0], [exe_path])

    def test_play_game_unity_vanilla_launches_directly(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            exe_path = os.path.join(tmp_dir, "UnityVanilla.exe")
            with open(exe_path, "w") as f:
                f.write("fake unity binary")

            profile = GameProfile(
                id="unity-vanilla-game",
                game_name="Unity Vanilla",
                exe_path=exe_path,
                engine="Unity Mono",
                translator="google",
                input_lang="ja",
                output_lang="vi",
                glossary={}
            )
            self.api.profile_repo.save(profile)

            with patch("subprocess.Popen") as mock_popen:
                res = self.api.play_game("unity-vanilla-game", vanilla=True)
                self.assertEqual(res.get("status"), "success")
                mock_popen.assert_called_once()
                self.assertEqual(mock_popen.call_args.args[0], [exe_path])

    def test_play_game_rejected_when_unity_deployer_active(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            exe_path = os.path.join(tmp_dir, "UnityGame2.exe")
            with open(exe_path, "w") as f:
                f.write("fake unity exe binary")

            profile = GameProfile(
                id="active-deployer-game",
                game_name="Active Deployer Game",
                exe_path=exe_path,
                engine="Unity Mono",
                translator="google",
                input_lang="ja",
                output_lang="vi",
                glossary={}
            )
            self.api.profile_repo.save(profile)

            # Mock an active deployer
            mock_dep = MagicMock()
            mock_dep.is_deploying = True
            self.api.active_deployers["active-deployer-game"] = mock_dep

            res = self.api.play_game("active-deployer-game")
            self.assertEqual(res.get("status"), "error")
            self.assertEqual(res.get("code"), "toast.game_translating")

    def test_ui_play_button_integration_and_styling(self):
        html_path = os.path.join(self.base_dir, "atm", "ui", "web", "index.html")
        css_path = os.path.join(self.base_dir, "atm", "ui", "web", "styles.css")
        js_path = os.path.join(self.base_dir, "atm", "ui", "web", "js", "features", "games.js")
        i18n_path = os.path.join(self.base_dir, "atm", "ui", "web", "js", "core", "i18n.js")

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        with open(i18n_path, "r", encoding="utf-8") as f:
            i18n = f.read()

        # HTML Gamepad SVG outline button
        self.assertIn('class="btn-icon btn-play"', html)
        self.assertIn('data-action="play"', html)
        self.assertIn('<rect x="2" y="6" width="20" height="12" rx="2"></rect>', html)

        # CSS outline and disabled state
        self.assertIn(".btn-icon.btn-play", css)
        self.assertIn(".btn-icon.btn-play:disabled", css)

        # JS translating disabled guard and data-i18n-title synchronization
        self.assertIn("card.dataset.state === 'TRANSLATING'", js)
        self.assertIn("btnPlay.disabled = true", js)
        self.assertIn("btnPlay.setAttribute('data-i18n-title', 'card.play_disabled_translating')", js)
        self.assertIn("btnPlay.setAttribute('data-i18n-title', 'card.play_tooltip')", js)
        self.assertIn("card.play_disabled_translating", js)
        self.assertIn("card.retranslate", js)

        # i18n keys in both languages
        for key in ["card.play_tooltip", "card.play_disabled_translating", "card.retranslate", "toast.game_translating"]:
            self.assertIn(f"'{key}'", i18n)

if __name__ == '__main__':
    unittest.main()
