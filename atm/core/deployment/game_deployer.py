import os
import shutil

from typing import List, Optional
from atm.core.events.event_bus import EventBus, SystemEvents
from atm.core.deployment.process_monitor import ProcessMonitor
from atm.storage.repositories.settings_repository import SettingsRepository
from atm.utils.file_system import copy_payload, cleanup_items, atomic_write, CopyResult
from atm.utils.logger import get_logger
from atm.config.schema import GameProfile

logger = get_logger(__name__, "deploy.log")

class GameDeployer:
    """Xử lý sao chép/deploy payload vào thư mục game."""
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus or EventBus()
        self.monitor = ProcessMonitor()
        self._deployed_items: List[str] = []
        self.is_deploying = False

    def deploy_and_launch(self, profile: GameProfile, payload_dir: str) -> None:
        self.is_deploying = True
        game_dir = os.path.dirname(profile.exe_path)
        logger.info(f"Preparing deployment for {profile.game_name} at {game_dir}")
        self.event_bus.publish(SystemEvents.GAME_STARTING, profile)

        if payload_dir:
            if not os.path.exists(payload_dir):
                logger.error(f"Payload directory not found: {payload_dir}")
                self.event_bus.publish(SystemEvents.ERROR_OCCURRED, "Payload not found!")
                return
            dest_dir = game_dir
            if profile.engine == "RenPy":
                dest_dir = os.path.join(game_dir, "game")
                os.makedirs(dest_dir, exist_ok=True)
                try:
                    for junk in ["realtimetrans_old.rpy", "realtimetrans_old.rpyc", "transconfig_old.rpy", "transconfig_old.rpyc"]:
                        junk_path = os.path.join(dest_dir, junk)
                        if os.path.exists(junk_path):
                            os.remove(junk_path)
                except Exception: pass
            copy_res = copy_payload(payload_dir, dest_dir)
            self._deployed_items = copy_res.copied_items
            if not copy_res.success:
                logger.error(f"Failed to copy payload: {copy_res.error}")
                cleanup_items(self._deployed_items)
                self._deployed_items = []
                self.is_running = False
                if self.monitor:
                    self.monitor.is_monitoring = False
                return False
        else:
            self._deployed_items = []
        
        info_file = os.path.join(game_dir, "ATM_IS_RUNNING.txt")
        try:
            msg = "==== AUTO TRANSLATOR MANAGER ====\nLauncher dang chay...\n"
            atomic_write(info_file, msg)
            self._deployed_items.append(info_file)
        except Exception:
            pass

        if profile.engine not in ("RenPy", "RPG Maker"):
            config_dir = os.path.join(game_dir, "BepInEx", "config")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "AutoTranslatorConfig.ini")
            try:
                from_lang = profile.input_lang if profile.input_lang else "auto"
                to_lang = profile.output_lang if profile.output_lang else "vi"
                settings = SettingsRepository().load()
                is_deepl = getattr(profile, "translator", "google") == "deepl"
                endpoint = "DeepLTranslateLegitimate" if is_deepl else "GoogleTranslate"
                
                with open(config_file, "w", encoding="utf-8") as f:
                    f.write("[Service]\n")
                    f.write(f"Endpoint={endpoint}\n")
                    if not is_deepl:
                        f.write("FallbackEndpoint=GoogleTranslateV2\n")
                    f.write("[TextFrameworks]\n")
                    f.write("EnableUGUI=True\n")
                    f.write("EnableNGUI=True\n")
                    f.write("EnableTextMeshPro=True\n")
                    f.write("EnableTextMesh=True\n")
                    f.write("EnableIMGUI=True\n")
                    f.write("EnableFairyGUI=True\n")
                    f.write("[General]\n")
                    f.write(f"Language={to_lang}\n")
                    f.write(f"FromLanguage={from_lang}\n")
                    f.write("[Behaviour]\n")
                    f.write("MaxCharactersPerTranslation=2500\n")
                    f.write("MinDialogueChars=20\n")
                    f.write("OutputTooLongText=True\n")
                    f.write("IgnoreWhitespaceInDialogue=True\n")
                    f.write("EnableBatching=True\n")
                    f.write("OverrideFontTextMeshPro=\n")
                    f.write("OverrideFont=\n")
                    if to_lang in ["vi"]:
                        f.write("FallbackFont=arial\n")
                    if is_deepl and settings.deepl_api_key:
                        f.write("\n[DeepLLegitimate]\n")
                        f.write(f"ExecutableLocation=\n")
                        f.write(f"ApiKey={settings.deepl_api_key}\n")
                        is_free = "True" if settings.deepl_api_key.endswith(":fx") else "False"
                        f.write(f"Free={is_free}\n")
                if config_file not in self._deployed_items:
                    self._deployed_items.append(config_file)
            except Exception as e:
                logger.error(f"Failed to create config file: {e}")

        self.event_bus.publish(SystemEvents.DEPLOYMENT_FINISHED, self._deployed_items)

        logger.info(f"Launching game: {profile.exe_path}")
        success = self.monitor.start_and_monitor(
            exe_path=profile.exe_path,
            cwd=game_dir,
            on_exit_callback=self._on_game_exited
        )
        if success:
            logger.info("Game launched successfully. Monitoring...")
        else:
            logger.error("Failed to launch game. Cleanup triggered early.")
        self.is_deploying = False

    def _on_game_exited(self) -> None:
        self.event_bus.publish(SystemEvents.GAME_EXITED)
        logger.info("Starting cleanup and log sync process...")
        from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
        safe_dest = os.path.join(TRANSLATIONS_DIR, "synced_logs")
        os.makedirs(safe_dest, exist_ok=True)
        
        for item in self._deployed_items:
            if os.path.isdir(item) and "BepInEx" in item:
                trans_file = os.path.join(item, "Translation", "vi", "Text", "_AutoGeneratedTranslations.txt")
                if os.path.exists(trans_file):
                    try:
                        shutil.copy2(trans_file, os.path.join(safe_dest, "_AutoGeneratedTranslations.txt"))
                        from atm.core.translation.cache_manager import TranslationCache
                        cache = TranslationCache()
                        count = 0
                        with open(trans_file, 'r', encoding='utf-8-sig') as tf:
                            for line in tf:
                                if '=' in line:
                                    k, v = line.strip().split('=', 1)
                                    if k and v:
                                        cache.set("auto", "vi", k, v)
                                        count += 1
                        cache.save_to_disk()
                        logger.info(f"Successfully synced translation log and imported {count} items to cache.")
                    except Exception as e:
                        logger.error(f"Failed to sync log: {e}")
                        
                log_file = os.path.join(item, "LogOutput.log")
                if os.path.exists(log_file):
                    try:
                        shutil.copy2(log_file, os.path.join(safe_dest, "LogOutput.log"))
                        logger.info("Successfully synced LogOutput.log")
                    except Exception as e:
                        logger.error(f"Failed to sync LogOutput.log: {e}")

        cleanup_items(self._deployed_items)
        self._deployed_items.clear()
        self.event_bus.publish(SystemEvents.CLEANUP_FINISHED)
        logger.info("Cleanup complete. Game directory is pristine.")


