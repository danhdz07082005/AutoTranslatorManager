import os
from unittest.mock import MagicMock, patch
from atm.config.schema import GameProfile
from atm.core.deployment.game_deployer import GameDeployer
from atm.ui.api import BackendApi
from atm.ui.server import create_server
import urllib.request

def test_game_deployer_configures_custom_translate_for_llm(tmp_path, monkeypatch):
    monkeypatch.setenv('ATM_SERVER_PORT', '9999')
    game_dir = tmp_path / 'UnityLLM'
    game_dir.mkdir()
    exe_path = game_dir / 'Game.exe'
    exe_path.touch()

    profile = GameProfile(
        game_name='UnityLLM',
        exe_path=str(exe_path),
        engine='Unity Mono',
        translator='gemini',
        input_lang='ja',
        output_lang='vi'
    )

    deployer = GameDeployer()
    deployer.monitor = MagicMock()
    deployer.monitor.start_and_monitor.return_value = True

    deployer.deploy_and_launch(profile, payload_dir='')

    ini_file = game_dir / 'BepInEx' / 'config' / 'AutoTranslatorConfig.ini'
    assert ini_file.exists()
    content = ini_file.read_text(encoding='utf-8')
    assert 'Endpoint=CustomTranslate' in content or 'Endpoint = CustomTranslate' in content
    assert f'http://127.0.0.1:9999/api/translate/unity/{profile.id}' in content

def test_translate_unity_text_api_flow(isolate_test_environment):
    api = BackendApi()
    profile = GameProfile(
        game_name='ActiveUnityGame',
        exe_path='C:/Games/Active/Game.exe',
        engine='Unity Mono',
        translator='gemini',
        input_lang='ja',
        output_lang='vi',
        glossary={'Hero': 'Anh hung'}
    )
    api.profile_repo.save(profile)

    # Register active deployer
    deployer = GameDeployer()
    deployer.current_game_id = profile.id
    api.active_deployers[profile.id] = deployer

    # 1. Test glossary hit
    res_glossary = api.translate_unity_text('Hero', 'ja', 'vi')
    assert res_glossary == 'Anh hung'

    # 2. Test LLM call
    with patch('atm.core.translation.translators.LLMTranslator.translate_batch', return_value=['Chao buoi sang']):
        res_llm = api.translate_unity_text('Good morning', 'en', 'vi')
        assert res_llm == 'Chao buoi sang'

    # 3. Test Cache hit on next request (does not call translate_batch again)
    with patch('atm.core.translation.translators.LLMTranslator.translate_batch', side_effect=Exception('Should not be called')):
        res_cached = api.translate_unity_text('Good morning', 'en', 'vi')
        assert res_cached == 'Chao buoi sang'

def test_server_http_translate_unity_endpoint(isolate_test_environment):
    api = BackendApi()
    api.translate_unity_text = MagicMock(return_value='Xin chao the gioi')

    # Find free port and start server
    import socket, threading
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()

    server = create_server(port, api)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    url = f'http://127.0.0.1:{port}/api/translate/unity?text=Hello%20World&from=en&to=vi'
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        content_type = resp.headers.get('Content-Type')
        assert 'text/plain' in content_type
        body = resp.read().decode('utf-8')
        assert body == 'Xin chao the gioi'

    server.shutdown()


def test_start_game_keeps_active_deployer_while_game_running(tmp_path, isolate_test_environment):
    api = BackendApi()
    game_dir = tmp_path / "UnityGame"
    game_dir.mkdir()
    exe_path = game_dir / "Game.exe"
    exe_path.touch()

    profile = GameProfile(
        game_name="UnityActiveTest",
        exe_path=str(exe_path),
        engine="Unity Mono",
        translator="gemini",
        input_lang="ja",
        output_lang="vi",
    )
    api.profile_repo.save(profile)
    api.update_settings(gemini_api_key="AIzaSy" + "A" * 35)

    import threading, time
    fake_thread = threading.Thread(target=lambda: time.sleep(0.2))
    fake_thread.start()

    with patch.object(GameDeployer, "deploy_and_launch", autospec=True) as mock_launch:
        def fake_launch(deployer_self, p, payload):
            deployer_self.monitor = MagicMock()
            deployer_self.monitor.monitor_thread = fake_thread
            return True
        mock_launch.side_effect = fake_launch

        res = api.start_game(profile.id)
        assert res["status"] == "success"
        time.sleep(0.05)
        # While thread is running, deployer MUST be in active_deployers
        assert profile.id in api.active_deployers

        # Wait for thread to finish
        fake_thread.join()
        time.sleep(0.05)
        # Once finished, deployer is cleaned up
        assert profile.id not in api.active_deployers
