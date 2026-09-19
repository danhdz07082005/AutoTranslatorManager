import os
import shutil

from typing import List, Optional
from atm.core.events.event_bus import EventBus, SystemEvents
from atm.core.deployment.process_monitor import ProcessMonitor
from atm.storage.repositories.settings_repository import SettingsRepository
from atm.utils.file_system import copy_payload, cleanup_items, atomic_write
from atm.utils.logger import get_logger
from atm.config.schema import GameProfile

logger = get_logger(__name__, "deploy.log")

class GameDeployer:
    """Xử lý sao chép/deploy payload vào thư mục game."""
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        if not event_bus:
            try:
                from atm.container import container
                event_bus = container.get("EventBus")
            except Exception:
                pass
        self.event_bus = event_bus or EventBus()
        self.monitor = ProcessMonitor()
        self._deployed_items: List[str] = []
        self.is_deploying = False
        self.current_game_id = None
        self._config_backup_file: Optional[str] = None
        self._created_config_file: Optional[str] = None

    def deploy_and_launch(self, profile: GameProfile, payload_dir: str) -> None:
        self.is_deploying = True
        self.current_game_id = profile.id
        self.current_output_lang = getattr(profile, 'output_lang', 'vi') or 'vi'
        try:
            game_dir = os.path.dirname(profile.exe_path)
            self.current_game_dir = game_dir
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
                    err_text = str(copy_res.error or "")
                    logger.error(f"Failed to copy payload: {err_text}")
                    cleanup_items(self._deployed_items)
                    self._deployed_items = []
                    self.is_deploying = False
                    if self.monitor:
                        self.monitor.is_monitoring = False

                    if "WinError 5" in err_text or "Access is denied" in err_text or "PermissionError" in err_text or "permission" in err_text.lower():
                        raise RuntimeError(
                            f"Permission Denied (WinError 5): Cannot copy BepInEx into protected folder '{dest_dir}'. "
                            f"Please run AutoTranslatorManager as Administrator (Run as Administrator) to translate Steam games in Program Files."
                        )
                    else:
                        raise RuntimeError(f"Failed to copy payload to game directory: {err_text}")
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
                backup_file = config_file + ".atm_backup"
                try:
                    import configparser
                    cp = configparser.ConfigParser(interpolation=None, strict=False)
                    cp.optionxform = str  # Giữ nguyên hoa thường của key

                    has_existing = os.path.exists(config_file)
                    self._config_backup_file = backup_file if has_existing else None
                    self._created_config_file = config_file if not has_existing else None

                    if has_existing:
                        if not os.path.exists(backup_file):
                            try:
                                shutil.copy2(config_file, backup_file)
                                logger.info(f"Backed up original AutoTranslatorConfig.ini to {backup_file}")
                            except Exception as e:
                                logger.warning(f"Failed to create config backup: {e}")
                        try:
                            cp.read(config_file, encoding="utf-8-sig")
                        except Exception as e:
                            logger.warning(f"Failed to parse existing config, creating fresh parser: {e}")
                            cp = configparser.ConfigParser(interpolation=None, strict=False)
                            cp.optionxform = str

                    from_lang = profile.input_lang if profile.input_lang else "auto"
                    to_lang = profile.output_lang if profile.output_lang else "vi"
                    port = os.environ.get('ATM_SERVER_PORT', '5000')

                    if not cp.has_section("Service"):
                        cp.add_section("Service")
                    cp.set("Service", "Endpoint", "CustomTranslate")
                    cp.set("Service", "FallbackEndpoint", "")

                    if not cp.has_section("Custom"):
                        cp.add_section("Custom")
                    cp.set("Custom", "Url", f"http://127.0.0.1:{port}/api/translate/unity/{profile.id}")
                    cp.set("Custom", "EnableShortDelay", "False")
                    cp.set("Custom", "DisableSpamChecks", "True")

                    if not cp.has_section("Files"):
                        cp.add_section("Files")
                    if not cp.has_option("Files", "Directory"):
                        cp.set("Files", "Directory", "Translation")
                    if not cp.has_option("Files", "OutputFile"):
                        cp.set("Files", "OutputFile", r"Translation\{Lang}\Text\_AutoGeneratedTranslations.txt")

                    if not cp.has_section("TextFrameworks"):
                        cp.add_section("TextFrameworks")
                    for opt in ["EnableUGUI", "EnableNGUI", "EnableTextMeshPro", "EnableTextMesh", "EnableIMGUI", "EnableFairyGUI"]:
                        if not cp.has_option("TextFrameworks", opt):
                            cp.set("TextFrameworks", opt, "True")

                    if not cp.has_section("General"):
                        cp.add_section("General")
                    cp.set("General", "Language", to_lang)
                    cp.set("General", "FromLanguage", from_lang)
                    if not cp.has_option("General", "UseStaticTranslations"):
                        cp.set("General", "UseStaticTranslations", "True")

                    if not cp.has_section("Behaviour"):
                        cp.add_section("Behaviour")
                    defaults_behaviour = {
                        "MaxCharactersPerTranslation": "2500",
                        "MinDialogueChars": "20",
                        "OutputTooLongText": "True",
                        "IgnoreWhitespaceInDialogue": "True",
                        "EnableBatching": "True",
                        "DisableSpamChecks": "True",
                        "EnableShortDelay": "False",
                        "OverrideFontTextMeshPro": "",
                        "OverrideFont": ""
                    }
                    for k, v in defaults_behaviour.items():
                        if not cp.has_option("Behaviour", k):
                            cp.set("Behaviour", k, v)
                    if to_lang in ["vi"] and not cp.has_option("Behaviour", "FallbackFont"):
                        cp.set("Behaviour", "FallbackFont", "arial")

                    with open(config_file, "w", encoding="utf-8") as f:
                        cp.write(f, space_around_delimiters=False)

                    # Pre-populate static translations strictly for this game (Folder Isolation)
                    try:
                        trans_dir = os.path.join(game_dir, "BepInEx", "Translation", to_lang, "Text")
                        os.makedirs(trans_dir, exist_ok=True)
                        trans_file = os.path.join(trans_dir, "_AutoGeneratedTranslations.txt")

                        existing_translations = {}

                        # 0. Preserve any pre-existing translations already in the game directory on disk
                        if os.path.exists(trans_file):
                            with open(trans_file, "r", encoding="utf-8-sig") as ef:
                                for line in ef:
                                    if "=" in line:
                                        k, v = line.strip().split("=", 1)
                                        if k and v:
                                            existing_translations[k] = v

                        # 1. From safe_dest synced log for this specific game id
                        from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
                        safe_dest = os.path.join(TRANSLATIONS_DIR, "synced_logs")
                        game_sync_file = os.path.join(safe_dest, f"{profile.id}_AutoGeneratedTranslations.txt")
                        if os.path.exists(game_sync_file):
                            with open(game_sync_file, "r", encoding="utf-8-sig") as sf:
                                for line in sf:
                                    if "=" in line:
                                        k, v = line.strip().split("=", 1)
                                        if k and v:
                                            existing_translations[k] = v

                        # 2. From SQLite game_lines repository strictly for profile.id
                        from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
                        gl_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
                        db_translations = gl_repo.get_all_by_game(profile.id)
                        existing_translations.update(db_translations)

                        if existing_translations:
                            with open(trans_file, "w", encoding="utf-8-sig") as tf:
                                for orig, trans in existing_translations.items():
                                    tf.write(f"{orig}={trans}\n")
                            logger.info(f"Pre-populated {len(existing_translations)} static translations for {profile.game_name} ({profile.id})")
                    except Exception as pe:
                        logger.warning(f"Failed to pre-populate static translations: {pe}")

                    self._config_backup_file = backup_file if has_existing else None
                    self._created_config_file = config_file if not has_existing else None
                    logger.info(f"Safely merged AutoTranslatorConfig.ini (has_backup={has_existing})")
                except Exception as e:
                    logger.error(f"Failed to create/merge config file: {e}")
    
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
                error_msg = self.monitor.last_error or "Unknown error"
                if "WinError 740" in error_msg:
                    raise RuntimeError("Game requires Administrator privileges (WinError 740). Please restart ATM as Administrator.")
                else:
                    raise RuntimeError(f"Failed to launch game: {error_msg}")
        finally:
            self.is_deploying = False

    def _on_game_exited(self) -> None:
        self.event_bus.publish(SystemEvents.GAME_EXITED)
        logger.info("Starting cleanup and log sync process...")
        from atm.storage.repositories.translation_repository import TRANSLATIONS_DIR
        safe_dest = os.path.join(TRANSLATIONS_DIR, "synced_logs")
        os.makedirs(safe_dest, exist_ok=True)
        
        to_lang = getattr(self, 'current_output_lang', 'vi') or 'vi'
        if hasattr(self, 'current_game_dir') and self.current_game_dir:
            bepinex_dir = os.path.join(self.current_game_dir, "BepInEx")
            if os.path.isdir(bepinex_dir):
                trans_file = os.path.join(bepinex_dir, "Translation", to_lang, "Text", "_AutoGeneratedTranslations.txt")
                if not os.path.exists(trans_file) and to_lang != "vi":
                    alt_file = os.path.join(bepinex_dir, "Translation", "vi", "Text", "_AutoGeneratedTranslations.txt")
                    if os.path.exists(alt_file):
                        trans_file = alt_file
                        to_lang = "vi"
                if os.path.exists(trans_file):
                    try:
                        shutil.copy2(trans_file, os.path.join(safe_dest, "_AutoGeneratedTranslations.txt"))
                        if self.current_game_id:
                            shutil.copy2(trans_file, os.path.join(safe_dest, f"{self.current_game_id}_AutoGeneratedTranslations.txt"))
                        from atm.core.translation.cache_manager import TranslationCache
                        from atm.storage.repositories.sqlite_game_lines import SQLiteGameLinesRepository
                        cache = TranslationCache()
                        
                        game_lines_repo = None
                        if self.current_game_id:
                            game_lines_repo = SQLiteGameLinesRepository(os.path.join(TRANSLATIONS_DIR, "translation_cache.db"))
                            
                        count = 0
                        game_lines_batch = []
                        with open(trans_file, 'r', encoding='utf-8-sig') as tf:
                            for line in tf:
                                if '=' in line:
                                    k, v = line.strip().split('=', 1)
                                    if k and v:
                                        cache.set("auto", to_lang, k, v)
                                        if game_lines_repo:
                                            game_lines_batch.append({
                                                "original": k,
                                                "translated": v,
                                                "category": "dialogue"
                                            })
                                        count += 1
                        cache.save_to_disk()
                        
                        if game_lines_repo and game_lines_batch:
                            game_lines_repo.batch_insert(self.current_game_id, game_lines_batch)
                                
                        logger.info(f"Successfully synced translation log and imported {count} items to cache and game DB.")
                    except Exception as e:
                        logger.error(f"Failed to sync log: {e}")
                        
                log_file = os.path.join(bepinex_dir, "LogOutput.log")
                if os.path.exists(log_file):
                    try:
                        shutil.copy2(log_file, os.path.join(safe_dest, "LogOutput.log"))
                        logger.info("Successfully synced LogOutput.log")
                    except Exception as e:
                        logger.error(f"Failed to sync LogOutput.log: {e}")

        # Khôi phục hoặc dọn dẹp AutoTranslatorConfig.ini
        if hasattr(self, '_config_backup_file') and self._config_backup_file and os.path.exists(self._config_backup_file):
            target_cfg = self._config_backup_file[:-len(".atm_backup")]
            for attempt in range(3):
                try:
                    shutil.move(self._config_backup_file, target_cfg)
                    logger.info(f"Restored original AutoTranslatorConfig.ini from backup.")
                    break
                except Exception as e:
                    if attempt == 2:
                        logger.error(f"Failed to restore original config: {e}")
                        self.event_bus.publish(SystemEvents.ERROR_OCCURRED, {"game_id": getattr(self, 'current_game_id', 'unknown'), "error_code": "error.cleanup_permission_denied", "error_details": str(e)})
                    import time
                    time.sleep(0.2)
        elif hasattr(self, '_created_config_file') and self._created_config_file and os.path.exists(self._created_config_file):
            for attempt in range(3):
                try:
                    os.remove(self._created_config_file)
                    logger.info("Cleaned up temporary AutoTranslatorConfig.ini.")
                    break
                except Exception as e:
                    if attempt == 2:
                        logger.error(f"Failed to remove temporary config: {e}")
                        self.event_bus.publish(SystemEvents.ERROR_OCCURRED, {"game_id": getattr(self, 'current_game_id', 'unknown'), "error_code": "error.cleanup_permission_denied", "error_details": str(e)})
                    import time
                    time.sleep(0.2)

        self._config_backup_file = None
        self._created_config_file = None

        cleanup_items(self._deployed_items)
        self._deployed_items.clear()
        self.event_bus.publish(SystemEvents.CLEANUP_FINISHED)
        logger.info("Cleanup complete. Game directory is pristine.")


