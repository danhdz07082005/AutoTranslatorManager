"""Ren'Py translation workflow based on the engine's own templates.

The previous workflow decompiled source scripts, found dialogue with a regex,
and wrote translated text back into those scripts.  Ren'Py already provides a
safe localisation format, so this module now translates only generated files
under ``game/tl/<language>``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping, Sequence

from atm.config.schema import GameProfile
from atm.core.translation.translators import RateLimitError
from atm.core.translation.renpy_tl_generator import (
    RenPyTLGenerator,
    TranslationTemplateEntry,
    DialogueEntry,
)
from atm.core.translation.pipeline import TranslatableString, TranslationPipeline, TranslationOrigin
from atm.core.translation.translation_memory import TranslationMemory
from atm.core.translation.translators import BaseTranslator, GoogleTranslator, DeepLTranslator
from atm.storage.repositories.settings_repository import SettingsRepository
from atm.utils.logger import get_logger


logger = get_logger(__name__, "launcher.log")


class RenPyTranslator:
    """Translate generated Ren'Py ``old`` / ``new`` template pairs.

    Constructor injection is optional and primarily keeps tests independent of
    a locally installed Ren'Py SDK or network translation service.
    """

    def __init__(
        self,
        settings=None,
        generator_factory: Callable[..., RenPyTLGenerator] = RenPyTLGenerator,
        translator_factory: Callable[[GameProfile, object], BaseTranslator] | None = None,
        translation_memory: object | bool | None = None,
        cache: object | bool | None = None,
    ) -> None:
        self.settings = settings if settings is not None else SettingsRepository().load()
        self._generator_factory = generator_factory
        self._translator_factory = translator_factory
        self._translation_memory = translation_memory
        self._cache = cache

    def _make_generator(self, project_path: Path, language: str) -> RenPyTLGenerator:
        return self._generator_factory(project_path, language)

    def extract_template_entries(
        self, project_path: str | Path, language: str
    ) -> list[TranslationTemplateEntry]:
        """Expose template extraction for the shared translation pipeline."""

        generator = self._make_generator(Path(project_path), language)
        return generator.parse_templates()

    def write_template_translations(
        self,
        project_path: str | Path,
        language: str,
        translations: Mapping[str, str],
    ) -> int:
        """Expose safe template write-back for the shared translation pipeline."""

        generator = self._make_generator(Path(project_path), language)
        return generator.write_translations(translations)

    def _get_translator(self, profile: GameProfile) -> BaseTranslator:
        if self._translator_factory is not None:
            return self._translator_factory(profile, self.settings)

        translator_id = getattr(profile, "translator", "google")
        if translator_id == "deepl" and self.settings and getattr(self.settings, "deepl_api_key", ""):
            return DeepLTranslator(self.settings.deepl_api_key)
        return GoogleTranslator()

    @staticmethod
    def _is_cancelled(is_cancelled: Callable[[], bool] | None) -> bool:
        return bool(is_cancelled and is_cancelled())

    def _translate_entries(
        self,
        entries: Sequence[TranslationTemplateEntry],
        profile: GameProfile,
    ) -> dict[str, str]:
        """Translate extracted source strings without syntax placeholders.

        Ren'Py's template generator has already parsed the source AST, so tags,
        interpolation, and quoting stay inside the `old`/`new` string values.
        The shared pipeline can call ``extract_template_entries`` and
        ``write_template_translations`` directly when it owns deduplication and
        validation.  This fallback preserves the pre-pipeline public workflow.
        """

        glossary = getattr(profile, "glossary", {}) or {}
        results: dict[str, str] = {}
        untranslated: list[str] = []

        for entry in entries:
            if entry.old in results:
                continue
            glossary_value = glossary.get(entry.old)
            if isinstance(glossary_value, str):
                results[entry.old] = glossary_value
            else:
                untranslated.append(entry.old)

        if not untranslated:
            return results

        translator = self._get_translator(profile)
        source_lang = getattr(profile, "input_lang", "auto") or "auto"
        target_lang = getattr(profile, "output_lang", None)
        if not target_lang:
            raise ValueError("output_lang must be provided")
        translated_values = translator.translate_batch(
            untranslated, target_lang=target_lang, source_lang=source_lang
        )

        for index, source_text in enumerate(untranslated):
            translated = translated_values[index] if index < len(translated_values) else source_text
            results[source_text] = translated if isinstance(translated, str) else source_text
        return results

    def _extract_and_decompile(self, game_path: Path, progress_callback: Callable[[int, int, str], None] | None = None) -> None:
        """Extract all .rpa archives and decompile all .rpyc files so the SDK can see them."""
        import sys
        import subprocess
        
        unren_dir = Path(__file__).parent / "unren_tools"
        rpatool = unren_dir / "rpatool.py"
        unrpyc = unren_dir / "unrpyc.py"

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        rpa_files = list(game_path.rglob("*.rpa"))
        total = len(rpa_files)
        for i, rpa in enumerate(rpa_files):
            if progress_callback:
                progress_callback(i, total + 1, f"Đang bung nén (Extracting) {rpa.name}...")
            logger.info("Extracting %s", rpa)
            try:
                subprocess.run(
                    [sys.executable, str(rpatool), "-x", str(rpa), "-o", str(game_path)],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                    timeout=300
                )
            except subprocess.TimeoutExpired:
                logger.error("RPA extraction timed out for %s", rpa)
            
            try:
                rpa.replace(rpa.with_suffix(".rpa.bak"))
            except Exception as e:
                logger.warning("Could not rename %s: %s", rpa, e)
                
        if progress_callback:
            progress_callback(total, total + 1, "Đang dịch ngược (Decompiling) RPYC...")
        logger.info("Decompiling RPYC files in %s", game_path)
        try:
            subprocess.run(
                [sys.executable, str(unrpyc), "--clobber", str(game_path)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
                timeout=600
            )
        except subprocess.TimeoutExpired:
            logger.error("RPYC decompilation timed out for %s", game_path)

    def translate_game(
        self,
        profile: GameProfile,
        progress_callback: Callable[[int, int, str], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> bool:
        """Generate/read templates, translate both string pairs and dialogue blocks.

        Handles two types of RenPy translatable content:
        1. ``old``/``new`` string pairs (UI: Save, Load, etc.)
        2. Dialogue blocks (``translate <lang> <label>:`` with character dialogue)

        Original scripts are intentionally never passed to a write operation.
        If templates already exist they are reused, so a later resume does not
        require an SDK to be installed again.
        """

        project_path = Path(profile.exe_path).expanduser().parent
        game_path = project_path / "game"
        if not game_path.is_dir():
            message = "Lỗi: Không tìm thấy thư mục 'game'."
            logger.error(message)
            if progress_callback:
                progress_callback(1, 1, message)
            return False

        language = getattr(profile, "output_lang", None)
        if not language:
            raise ValueError("output_lang must be provided")
        try:
            generator = self._make_generator(project_path, language)
        except ValueError as error:
            message = f"Lỗi: Ngôn ngữ Ren'Py không hợp lệ: {error}"
            logger.error(message)
            if progress_callback:
                progress_callback(1, 1, message)
            return False

        if self._is_cancelled(is_cancelled):
            return False

        if progress_callback:
            progress_callback(0, 1, "Đang bung nén game (Extract & Decompile)...")
        self._extract_and_decompile(game_path, progress_callback)

        if progress_callback:
            progress_callback(0, 1, "Đang chuẩn bị mẫu dịch Ren'Py...")
        generation = generator.generate_templates()
        if not generation.success:
            message = f"Lỗi: {generation.message}"
            logger.error(message)
            if progress_callback:
                progress_callback(1, 1, message)
            return False

        # ── Extract BOTH types of translatable content ──────────────────
        string_entries = generator.parse_templates()
        dialogue_entries = generator.parse_dialogue_blocks()

        total_strings = len(string_entries)
        total_dialogue = len(dialogue_entries)
        total = total_strings + total_dialogue

        if total == 0:
            message = "Không tìm thấy chuỗi hoặc hội thoại nào cần dịch."
            logger.info(message)
            if progress_callback:
                progress_callback(1, 1, message)
            return True

        logger.info(
            "Found %d string pairs + %d dialogue blocks = %d total entries",
            total_strings, total_dialogue, total,
        )

        if self._is_cancelled(is_cancelled):
            return False

        if progress_callback:
            progress_callback(0, total, f"Đang dịch {total} mục ({total_strings} chuỗi UI + {total_dialogue} hội thoại)...")

        # ── Build unified pipeline entries ──────────────────────────────
        pipeline_entries: list[TranslatableString] = []

        # String pairs (old/new)
        for entry in string_entries:
            pipeline_entries.append(
                TranslatableString(
                    text=entry.old,
                    path=(str(entry.template_path), entry.new_line),
                    category="ui_string",
                    metadata={"type": "old_new", "template_entry": entry},
                )
            )

        # Dialogue blocks
        for entry in dialogue_entries:
            pipeline_entries.append(
                TranslatableString(
                    text=entry.text,
                    path=(str(entry.template_path), entry.line_number),
                    category="dialogue",
                    metadata={"type": "dialogue", "dialogue_entry": entry},
                )
            )

        # ── Run translation pipeline ────────────────────────────────────
        try:
            translator = self._get_translator(profile)
            string_translations: dict[str, str] = {}
            dialogue_translations: dict[str, str] = {}

            def _write_callback(entry: TranslatableString, text: str) -> None:
                entry_type = entry.metadata.get("type", "old_new")
                if entry_type == "dialogue":
                    dialogue_translations[entry.text] = text
                else:
                    string_translations[entry.text] = text

            result = TranslationPipeline(
                translator,
                cache=(
                    None
                    if self._cache is False
                    else self._cache or getattr(translator, "cache", None)
                ),
                glossary=getattr(profile, "glossary", {}) or {},
                translation_memory=(
                    None
                    if self._translation_memory is False
                    else self._translation_memory or TranslationMemory()
                ),
            ).run(
                pipeline_entries,
                source_lang=getattr(profile, "input_lang", "auto") or "auto",
                target_lang=language,
                writer=_write_callback,
                is_cancelled=is_cancelled,
                progress_callback=progress_callback,
            )
            if getattr(result, "rate_limited", False):
                raise RateLimitError("Pipeline rate limited during Ren'Py translation")
        except RateLimitError as rate_limit_err:
            logger.warning("Rate limit hit. Writing partial translations...")
            generator.write_translations(string_translations)
            generator.write_dialogue_translations(dialogue_translations)
            self._inject_language_config(game_path, language)
            if progress_callback:
                progress_callback(0, total, "translation.rate_limited", {"error": str(rate_limit_err)})
            raise
        except Exception as error:
            logger.exception("Ren'Py template translation failed: %s", error)
            if progress_callback:
                progress_callback(total, total, f"Lỗi dịch Ren'Py: {error}")
            return False

        if self._is_cancelled(is_cancelled):
            return False

        # ── Write back both types ───────────────────────────────────────
        updated_strings = generator.write_translations(string_translations)
        updated_dialogue = generator.write_dialogue_translations(dialogue_translations)
        updated_total = updated_strings + updated_dialogue

        # ── Inject language config so the game actually uses the translation
        self._inject_language_config(game_path, language)

        message = (
            f"Dịch Ren'Py hoàn tất: {updated_total}/{total} mục "
            f"({updated_strings} chuỗi UI + {updated_dialogue} hội thoại), "
            f"unique={result.stats.unique}, rejected={result.stats.validation_rejected}."
        )
        logger.info(message)
        if progress_callback:
            progress_callback(total, total, message)
        return True

    @staticmethod
    def _inject_language_config(game_path: Path, language: str) -> None:
        """Create/update an ATM-managed .rpy file that activates the translation.

        RenPy only loads translations from ``game/tl/<language>/`` when
        ``config.language`` is set to that language name.  Without this
        injection the game runs in the default None language (original English)
        even if all the template files have been fully translated.

        This mirrors what tools like ZenPy do (``zenpy_define_language.rpy``)
        and what the official RenPy docs describe under "Default Language".

        The generated file uses the lowest possible init priority (``init -999``)
        so it runs before any game-defined ``config.language`` assignment and
        can be safely overridden by the developer.
        """

        inject_file = game_path / "atm_language_config.rpy"
        content = (
            "# Auto-generated by AutoTranslatorManager — safe to delete if you\n"
            "# want to revert to the original language or use the in-game menu.\n"
            f"init -999 python:\n"
            f"    if config.language is None:\n"
            f"        config.language = {language!r}\n"
        )

        try:
            # Only write if file doesn't exist or content changed
            if inject_file.exists() and inject_file.read_text(encoding="utf-8") == content:
                logger.debug("Language config injection unchanged: %s", inject_file)
                return
            inject_file.write_text(content, encoding="utf-8")
            logger.info("Injected language config (%r) into: %s", language, inject_file)
        except OSError as exc:
            logger.warning("Could not write language config injection: %s", exc)

    @staticmethod
    def remove_language_injection(game_path: Path) -> bool:
        """Remove the ATM language config injection file if it exists.

        Call this when the user wants to revert a game to its original language.
        Returns True if a file was removed.
        """

        inject_file = game_path / "atm_language_config.rpy"
        if inject_file.exists():
            try:
                inject_file.unlink()
                logger.info("Removed language config injection: %s", inject_file)
                return True
            except OSError as exc:
                logger.warning("Could not remove language config injection: %s", exc)
        return False
