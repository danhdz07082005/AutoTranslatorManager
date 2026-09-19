import unittest
from unittest.mock import MagicMock, patch
import tempfile
import os
from atm.core.detectors.game_detector import GameDetector
from atm.core.deployment.game_deployer import GameDeployer
from atm.config.schema import GameProfile

class TestSteamUnityDetector(unittest.TestCase):
    def test_steam_launcher_mismatch_detected_via_data_folder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            launcher_exe = os.path.join(tmp_dir, "SteamLauncher.exe")
            with open(launcher_exe, "w") as f:
                f.write("")
            
            # The Data folder has a completely different name from the launcher exe, with a Unity signature
            game_data = os.path.join(tmp_dir, "RealGame_Data")
            os.makedirs(game_data, exist_ok=True)
            with open(os.path.join(game_data, "boot.config"), "w") as f:
                f.write("player-connection-debug=0")

            engine = GameDetector.detect_engine(launcher_exe)
            self.assertEqual(engine, "Unity Mono")

    def test_renpy_with_save_data_not_misidentified_as_unity(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            renpy_exe = os.path.join(tmp_dir, "RenpyGame.exe")
            with open(renpy_exe, "w") as f:
                f.write("")
            
            # Contains Save_Data folder (ending in _Data) AND renpy folder
            os.makedirs(os.path.join(tmp_dir, "Save_Data"), exist_ok=True)
            os.makedirs(os.path.join(tmp_dir, "renpy"), exist_ok=True)

            engine = GameDetector.detect_engine(renpy_exe)
            # MUST NOT be misidentified as Unity Mono!
            self.assertEqual(engine, "RenPy")

    def test_rpgmaker_with_user_data_not_misidentified_as_unity(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            rpg_exe = os.path.join(tmp_dir, "Game.exe")
            with open(rpg_exe, "w") as f:
                f.write("")
            
            # Contains User_Data folder (ending in _Data) AND www/data folder
            os.makedirs(os.path.join(tmp_dir, "User_Data"), exist_ok=True)
            os.makedirs(os.path.join(tmp_dir, "www", "data"), exist_ok=True)

            engine = GameDetector.detect_engine(rpg_exe)
            # MUST NOT be misidentified as Unity Mono!
            self.assertEqual(engine, "RPG Maker")

    def test_unknown_game_with_save_data_returns_unknown(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            custom_exe = os.path.join(tmp_dir, "IndieGame.exe")
            with open(custom_exe, "w") as f:
                f.write("")
            
            # Only contains a non-Unity Save_Data folder
            os.makedirs(os.path.join(tmp_dir, "Save_Data"), exist_ok=True)

            engine = GameDetector.detect_engine(custom_exe)
            self.assertEqual(engine, "Unknown")

    def test_steam_launcher_il2cpp_detected_via_game_assembly(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            launcher_exe = os.path.join(tmp_dir, "Launcher.exe")
            with open(launcher_exe, "w") as f:
                f.write("")
            
            # GameAssembly.dll exists in root
            assembly_dll = os.path.join(tmp_dir, "GameAssembly.dll")
            with open(assembly_dll, "w") as f:
                f.write("")

            engine = GameDetector.detect_engine(launcher_exe)
            self.assertEqual(engine, "Unity IL2CPP")

    def test_unity_detected_via_unity_player_dll(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            custom_exe = os.path.join(tmp_dir, "CustomStart.exe")
            with open(custom_exe, "w") as f:
                f.write("")
            
            # UnityPlayer.dll exists in root
            player_dll = os.path.join(tmp_dir, "UnityPlayer.dll")
            with open(player_dll, "w") as f:
                f.write("")

            engine = GameDetector.detect_engine(custom_exe)
            self.assertEqual(engine, "Unity Mono")

    def test_deployer_raises_permission_denied_on_winerror_5(self):
        deployer = GameDeployer()
        profile = GameProfile(
            id="steam-game-uac",
            game_name="Steam Protected Game",
            exe_path="C:\\Program Files (x86)\\Steam\\Game.exe",
            engine="Unity Mono",
            translator="google",
            input_lang="auto",
            output_lang="vi"
        )

        mock_copy_res = MagicMock()
        mock_copy_res.success = False
        mock_copy_res.copied_items = []
        mock_copy_res.error = "[WinError 5] Access is denied: 'C:\\Program Files (x86)\\Steam\\BepInEx'"

        with tempfile.TemporaryDirectory() as fake_payload:
            with patch("atm.core.deployment.game_deployer.copy_payload", return_value=mock_copy_res):
                with self.assertRaises(RuntimeError) as ctx:
                    deployer.deploy_and_launch(profile, payload_dir=fake_payload)
                
                self.assertIn("Permission Denied (WinError 5)", str(ctx.exception))
                self.assertIn("Run as Administrator", str(ctx.exception))

if __name__ == '__main__':
    unittest.main()
