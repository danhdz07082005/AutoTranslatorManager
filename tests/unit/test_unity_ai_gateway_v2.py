import unittest
from unittest.mock import MagicMock, patch
from atm.config.schema import GameProfile, AppSettings
from atm.ui.api import BackendApi
from atm.core.deployment.game_deployer import GameDeployer
import configparser
import tempfile
import os

class TestUnityAIGatewayV2(unittest.TestCase):
    def setUp(self):
        self.api = BackendApi()

    def test_deployer_sets_restful_url_with_game_id(self):
        deployer = GameDeployer()
        profile = GameProfile(
            id="test-game-xyz-789",
            game_name="Unity AI Game",
            exe_path="C:\\Games\\Test\\Game.exe",
            engine="Unity Mono",
            translator="gemini",
            input_lang="ja",
            output_lang="vi"
        )
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            game_dir = os.path.join(tmp_dir, "Game")
            os.makedirs(os.path.join(game_dir, "BepInEx", "config"), exist_ok=True)
            profile.exe_path = os.path.join(game_dir, "Game.exe")

            with patch.dict(os.environ, {"ATM_SERVER_PORT": "5055"}):
                # Call config generation via deploy_and_launch mock
                with patch.object(deployer.monitor, "start_and_monitor", return_value=True):
                    with patch("atm.core.deployment.game_deployer.copy_payload", return_value=MagicMock(success=True, copied_items=[])):
                        deployer.deploy_and_launch(profile, tmp_dir)

            config_file = os.path.join(game_dir, "BepInEx", "config", "AutoTranslatorConfig.ini")
            self.assertTrue(os.path.exists(config_file))
            cp = configparser.ConfigParser()
            cp.read(config_file, encoding="utf-8")
            
            self.assertEqual(cp.get("Service", "Endpoint"), "CustomTranslate")
            custom_url = cp.get("Custom", "Url")
            # Should be clean RESTful URL with game_id
            self.assertEqual(custom_url, "http://127.0.0.1:5055/api/translate/unity/test-game-xyz-789")
            # Must NOT have duplicate query parameters or {0} literals
            self.assertNotIn("?text=", custom_url)
            self.assertNotIn("{0}", custom_url)

    def test_translate_unity_text_with_game_id_isolation(self):
        # Create 2 game profiles with different glossaries
        p1 = GameProfile(
            id="game-1",
            game_name="Game 1",
            exe_path="C:\\G1\\Game.exe",
            engine="Unity Mono",
            translator="gemini",
            input_lang="ja",
            output_lang="vi",
            glossary={"Sword": "Thanh Gươm 1"}
        )
        p2 = GameProfile(
            id="game-2",
            game_name="Game 2",
            exe_path="C:\\G2\\Game.exe",
            engine="Unity Mono",
            translator="gemini",
            input_lang="ja",
            output_lang="vi",
            glossary={"Sword": "Đoản Kiếm 2"}
        )
        self.api.profile_repo.save(p1)
        self.api.profile_repo.save(p2)

        # Request with game_id="game-1" -> gets Game 1's glossary
        res1 = self.api.translate_unity_text("Sword", from_lang="ja", to_lang="vi", game_id="game-1")
        self.assertEqual(res1, "Thanh Gươm 1")

        # Request with game_id="game-2" -> gets Game 2's glossary
        res2 = self.api.translate_unity_text("Sword", from_lang="ja", to_lang="vi", game_id="game-2")
        self.assertEqual(res2, "Đoản Kiếm 2")

    def test_translate_unity_provenance_recording(self):
        profile = GameProfile(
            id="prov-game-1",
            game_name="Prov Game",
            exe_path="C:\\Prov\\Game.exe",
            engine="Unity Mono",
            translator="gemini",
            input_lang="ja",
            output_lang="vi",
            glossary={}
        )
        self.api.profile_repo.save(profile)

        # Mock LLMTranslator to return a translation
        mock_llm = MagicMock()
        mock_llm.translate_batch.return_value = ["Xin chào hiệp sĩ"]

        with patch("atm.core.translation.translators.LLMTranslator", return_value=mock_llm):
            with patch("atm.storage.repositories.sqlite_game_lines.SQLiteGameLinesRepository.insert_or_ignore") as mock_insert:
                res = self.api.translate_unity_text("Konnichiwa Yuusha", from_lang="ja", to_lang="vi", game_id="prov-game-1")
                self.assertEqual(res, "Xin chào hiệp sĩ")
                mock_insert.assert_called_once()
                call_kwargs = mock_insert.call_args.kwargs
                self.assertEqual(call_kwargs["game_id"], "prov-game-1")
                self.assertEqual(call_kwargs["source_file"], "Unity_Runtime [gemini]")

    def test_translate_unity_fallback_provenance(self):
        profile = GameProfile(
            id="fb-game-1",
            game_name="Fallback Game",
            exe_path="C:\\FB\\Game.exe",
            engine="Unity Mono",
            translator="gemini",
            input_lang="ja",
            output_lang="vi",
            glossary={}
        )
        self.api.profile_repo.save(profile)

        # LLM fails, Google fallback succeeds
        mock_llm = MagicMock()
        mock_llm.translate_batch.side_effect = Exception("API connection dropped")
        mock_google = MagicMock()
        mock_google.translate_batch.return_value = ["Cứu hộ Google"]

        with patch("atm.core.translation.translators.LLMTranslator", return_value=mock_llm):
            with patch("atm.core.translation.translators.GoogleTranslator", return_value=mock_google):
                with patch("atm.storage.repositories.sqlite_game_lines.SQLiteGameLinesRepository.insert_or_ignore") as mock_insert:
                    res = self.api.translate_unity_text("Tasukete", from_lang="ja", to_lang="vi", game_id="fb-game-1")
                    self.assertEqual(res, "Cứu hộ Google")
                    mock_insert.assert_called_once()
                    call_kwargs = mock_insert.call_args.kwargs
                    self.assertEqual(call_kwargs["game_id"], "fb-game-1")
                    self.assertEqual(call_kwargs["source_file"], "Unity_Runtime [gemini_fallback_to_google]")

    def test_glossary_priority_over_global_cache(self):
        from atm.core.translation.cache_manager import TranslationCache
        cache = TranslationCache()
        # Seed global cache with a generic translation
        cache.set("ja", "vi", "Shield", "Tấm khiên thường", category="dialogue")

        # Game B has custom glossary overriding the general cache
        profile_b = GameProfile(
            id="game-b",
            game_name="Game B",
            exe_path="C:\\GB\\Game.exe",
            engine="Unity Mono",
            translator="gemini",
            input_lang="ja",
            output_lang="vi",
            glossary={"Shield": "Khiên Thần Thánh"}
        )
        # Game C has no glossary
        profile_c = GameProfile(
            id="game-c",
            game_name="Game C",
            exe_path="C:\\GC\\Game.exe",
            engine="Unity Mono",
            translator="gemini",
            input_lang="ja",
            output_lang="vi",
            glossary={}
        )
        self.api.profile_repo.save(profile_b)
        self.api.profile_repo.save(profile_c)

        with patch("atm.storage.repositories.sqlite_game_lines.SQLiteGameLinesRepository.insert_or_ignore") as mock_insert:
            # Game B must get its own glossary ("Khiên Thần Thánh"), NOT the cached "Tấm khiên thường"
            res_b = self.api.translate_unity_text("Shield", from_lang="ja", to_lang="vi", game_id="game-b")
            self.assertEqual(res_b, "Khiên Thần Thánh")
            mock_insert.assert_called_once()
            self.assertEqual(mock_insert.call_args.kwargs["source_file"], "Unity_Runtime [Glossary]")
            self.assertEqual(mock_insert.call_args.kwargs["game_id"], "game-b")
            self.assertEqual(mock_insert.call_args.kwargs["category"], "glossary")
            self.assertEqual(mock_insert.call_args.kwargs["translated"], "Khiên Thần Thánh")

        # Game C (no glossary) must fall back to the global cache ("Tấm khiên thường")
        res_c = self.api.translate_unity_text("Shield", from_lang="ja", to_lang="vi", game_id="game-c")
        self.assertEqual(res_c, "Tấm khiên thường")

    def test_deployer_configures_custom_translate_for_google_engine(self):
        deployer = GameDeployer()
        profile = GameProfile(
            id="google-game-123",
            game_name="Google Unity Game",
            exe_path="C:\\Games\\GoogleGame\\Game.exe",
            engine="Unity Mono",
            translator="google",
            input_lang="auto",
            output_lang="vi"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            game_dir = os.path.join(tmp_dir, "GoogleGame")
            os.makedirs(os.path.join(game_dir, "BepInEx", "config"), exist_ok=True)
            profile.exe_path = os.path.join(game_dir, "Game.exe")

            with patch.dict(os.environ, {"ATM_SERVER_PORT": "54321"}):
                with patch.object(deployer.monitor, "start_and_monitor", return_value=True):
                    with patch("atm.core.deployment.game_deployer.copy_payload", return_value=MagicMock(success=True, copied_items=[])):
                        deployer.deploy_and_launch(profile, tmp_dir)

            config_file = os.path.join(game_dir, "BepInEx", "config", "AutoTranslatorConfig.ini")
            self.assertTrue(os.path.exists(config_file))
            cp = configparser.ConfigParser()
            cp.read(config_file, encoding="utf-8")

            self.assertEqual(cp.get("Service", "Endpoint"), "CustomTranslate")
            self.assertEqual(cp.get("Custom", "Url"), "http://127.0.0.1:54321/api/translate/unity/google-game-123")
            self.assertEqual(cp.get("Custom", "EnableShortDelay"), "False")
            self.assertEqual(cp.get("Behaviour", "DisableSpamChecks"), "True")
            self.assertEqual(cp.get("Behaviour", "EnableShortDelay"), "False")

    def test_deployer_pre_populates_static_translations_strictly_for_game(self):
        deployer = GameDeployer()
        target_game_id = "target-game-folder-10"
        other_game_id = "other-game-folder-4"

        profile = GameProfile(
            id=target_game_id,
            game_name="Target Adventure Game",
            exe_path="C:\\Games\\TargetGame\\Game.exe",
            engine="Unity Mono",
            translator="google",
            input_lang="ja",
            output_lang="vi"
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
            from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository

            game_dir = os.path.join(tmp_dir, "TargetGame")
            os.makedirs(os.path.join(game_dir, "BepInEx", "config"), exist_ok=True)
            profile.exe_path = os.path.join(game_dir, "Game.exe")

            # Seed target game translations in SQLite DB
            gl_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
            gl_repo.insert_or_ignore(target_game_id, "Hello Hero", "Xin chào dũng sĩ", "dialogue", "test")
            # Seed other game translations (must NOT bleed into target game)
            gl_repo.insert_or_ignore(other_game_id, "Forbidden Secret", "Bí mật cấm", "dialogue", "test")

            with patch.object(deployer.monitor, "start_and_monitor", return_value=True):
                with patch("atm.core.deployment.game_deployer.copy_payload", return_value=MagicMock(success=True, copied_items=[])):
                    deployer.deploy_and_launch(profile, tmp_dir)

            trans_file = os.path.join(game_dir, "BepInEx", "Translation", "vi", "Text", "_AutoGeneratedTranslations.txt")
            self.assertTrue(os.path.exists(trans_file))

            with open(trans_file, "r", encoding="utf-8-sig") as f:
                content = f.read()

            self.assertIn("Hello Hero=Xin chào dũng sĩ", content)
            self.assertNotIn("Forbidden Secret", content, "Folder isolation failed: other game translation leaked into target game!")

    def test_google_translator_zero_delay_for_realtime_and_single_text(self):
        from atm.core.translation.translators import GoogleTranslator
        translator = GoogleTranslator()
        
        # Mock network response
        mock_response = MagicMock()
        mock_response.read.return_value = b'[[["Tr\xc3\xb2 ch\xc6\xa1i m\xe1\xbb\x9bi", "New Game", null, null]]]'
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            with patch("time.sleep") as mock_sleep:
                # 1. Realtime flag explicit
                res = translator.translate_batch(["New Game"], target_lang="vi", source_lang="en", is_realtime=True)
                self.assertEqual(res, ["Trò chơi mới"])
                mock_sleep.assert_not_called()

                # 2. Single text implicit realtime (len == 1)
                res_single = translator.translate_batch(["New Game"], target_lang="vi", source_lang="en")
                self.assertEqual(res_single, ["Trò chơi mới"])
                mock_sleep.assert_not_called()

    def test_google_translator_batch_offline_delay_between_chunks_only(self):
        from atm.core.translation.translators import GoogleTranslator
        translator = GoogleTranslator()
        # Force small chunks to generate 2 chunks
        translator.MAX_TEXTS_PER_CHUNK = 2

        mock_response = MagicMock()
        mock_response.read.return_value = b'[[["T1", "A", null, null], ["T2", "B", null, null]]]'
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            with patch("time.sleep") as mock_sleep:
                texts = ["A", "B", "C", "D"]
                res = translator._do_translate_batch(texts, target_lang="vi", source_lang="en", is_realtime=False)
                # Should sleep between chunk 0 and chunk 1
                self.assertTrue(mock_sleep.called)

    def test_api_runtime_lines_and_status_reporting(self):
        target_game_id = "realtime-report-game-123"
        profile = GameProfile(
            id=target_game_id,
            game_name="Realtime Report Game",
            exe_path="C:\\Games\\Report\\Game.exe",
            engine="Unity Mono",
            translator="google",
            input_lang="ja",
            output_lang="vi"
        )
        self.api.profile_repo.save(profile)

        # Mock deployer in active_deployers
        mock_deployer = MagicMock()
        mock_deployer.is_deploying = False
        mock_deployer.monitor.is_monitoring = True
        self.api.active_deployers[target_game_id] = mock_deployer

        with patch("atm.storage.repositories.sqlite_game_lines.SQLiteGameLinesRepository.count_by_game", return_value=27):
            # 1. get_games() should include runtime_lines and TRANSLATING state
            games_res = self.api.get_games()["games"]
            game_entry = next((g for g in games_res if g["id"] == target_game_id), None)
            self.assertIsNotNone(game_entry)
            self.assertEqual(game_entry["runtime_state"], "TRANSLATING")
            self.assertEqual(game_entry["runtime_lines"], 27)

            # 2. get_translation_status() should return 27 lines and realtime_running code
            status = self.api.get_translation_status(target_game_id)
            self.assertEqual(status["code"], "translation.realtime_running")
            self.assertEqual(status["translated_lines"], 27)
            self.assertFalse(status["done"])

        # Clean up
        if target_game_id in self.api.active_deployers:
            del self.api.active_deployers[target_game_id]

    def test_game_card_template_progress_bar_and_css_integrity(self):
        # 1. Verify index.html template does NOT have class="hidden" on progress-container
        index_html_path = os.path.join(os.path.dirname(__file__), "..", "..", "atm", "ui", "web", "index.html")
        with open(index_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        self.assertIn('<template id="game-card-template">', html_content)
        # progress-container should be visible when styled (not blocked by .hidden)
        template_chunk = html_content[html_content.find('<template id="game-card-template">'):html_content.find('</template>')]
        self.assertIn('<div class="progress-container mb-sm" style="display:none;">', template_chunk)
        self.assertNotIn('progress-container hidden', template_chunk)

        # 2. Verify styles.css has .progress-bar-animated and @keyframes progress-bar-stripes
        styles_css_path = os.path.join(os.path.dirname(__file__), "..", "..", "atm", "ui", "web", "styles.css")
        with open(styles_css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        self.assertIn(".progress-bar-animated", css_content)
        self.assertIn("@keyframes progress-bar-stripes", css_content)

        # 3. Verify games.js sets card.dataset.lines
        games_js_path = os.path.join(os.path.dirname(__file__), "..", "..", "atm", "ui", "web", "js", "features", "games.js")
        with open(games_js_path, "r", encoding="utf-8") as f:
            js_content = f.read()

        self.assertIn("card.dataset.lines = game.runtime_lines || 0;", js_content)
        self.assertIn("progBarFill.classList.add('progress-bar-animated')", js_content)
        self.assertIn("translation.realtime_running", js_content)

    def test_sqlite_game_lines_latest_update_wins_and_syncs(self):
        from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
        from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
        import time

        repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
        game_id = "test-game-order-check"

        # Clean up any leftover
        repo.clear_by_game(game_id)

        # 1. Insert original with category="dialogue"
        repo.insert_or_ignore(game_id, "Recall", "Nhớ lại", category="dialogue")
        # 2. Insert same original with category="default" (simulate log sync)
        repo.insert_or_ignore(game_id, "Recall", "Hồi tưởng cũ", category="default")

        # 3. Find item id for the dialogue one and update it
        items = repo.list_by_game(game_id)["items"]
        dialogue_item = next(it for it in items if it["category"] == "dialogue")
        time.sleep(0.01) # Ensure updated_at is distinctly higher
        success = repo.update(dialogue_item["id"], game_id, "Nhớ lại mới nhất", dialogue_item["version"])
        self.assertTrue(success)

        # 4. Verify get_all_by_game returns the latest updated one
        all_lines = repo.get_all_by_game(game_id)
        self.assertEqual(all_lines["Recall"], "Nhớ lại mới nhất")

        # 5. Verify sibling row was also updated
        updated_items = repo.list_by_game(game_id)["items"]
        for it in updated_items:
            self.assertEqual(it["translated"], "Nhớ lại mới nhất")

        # Clean up
        repo.clear_by_game(game_id)

if __name__ == '__main__':
    unittest.main()


