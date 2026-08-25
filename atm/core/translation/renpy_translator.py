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
)
from atm.core.translation.pipeline import TranslatableString, TranslationPipeline, TranslationOrigin
from atm.core.translation.translation_memory import TranslationMemory
from atm.core.translation.translators import BaseTranslator
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
        target_lang = getattr(profile, "output_lang", "vi") or "vi"
        translated_values = translator.translate_batch(
            untranslated, target_lang=target_lang, source_lang=source_lang
        )

        for index, source_text in enumerate(untranslated):
            translated = translated_values[index] if index < len(translated_values) else source_text
            results[source_text] = translated if isinstance(translated, str) else source_text
        return results

    def translate_game(
        self,
        profile: GameProfile,
        progress_callback: Callable[[int, int, str], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> bool:
        """Generate/read templates, translate `old` values, and update `new`.

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

        language = getattr(profile, "output_lang", "vi") or "vi"
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
            progress_callback(0, 1, "Đang chuẩn bị mẫu dịch Ren'Py...")
        generation = generator.ensure_templates()
        if not generation.success:
            message = f"Lỗi: {generation.message}"
            logger.error(message)
            if progress_callback:
                progress_callback(1, 1, message)
            return False

        entries = generator.parse_templates()
        if not entries:
            message = "Không có chuỗi old/new nào cần dịch trong mẫu Ren'Py."
            logger.info(message)
            if progress_callback:
                progress_callback(1, 1, message)
            return True

        if self._is_cancelled(is_cancelled):
            return False

        total = len(entries)
        if progress_callback:
            progress_callback(0, total, f"Đang dịch {total} chuỗi từ mẫu Ren'Py...")

        try:
            translator = self._get_translator(profile)
            translations: dict[str, str] = {}
            pipeline_entries = [
                TranslatableString(
                    text=entry.old,
                    path=(str(entry.template_path), entry.new_line),
                    category="dialogue",
                    metadata={"template_entry": entry},
                )
                for entry in entries
            ]
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
                writer=lambda entry, text: translations.__setitem__(entry.text, text),
                is_cancelled=is_cancelled,
                progress_callback=progress_callback,
            )
            if getattr(result, "rate_limited", False):
                raise RateLimitError("Pipeline rate limited during Ren'Py translation")
        except RateLimitError as rate_limit_err:
            logger.warning("Rate limit hit. Writing partial translations...")
            generator.write_translations(translations)
            if progress_callback:
                progress_callback(total, total, "translation.rate_limited", {"error": str(rate_limit_err)})
            raise
        except Exception as error:
            logger.exception("Ren'Py template translation failed: %s", error)
            if progress_callback:
                progress_callback(total, total, f"Lỗi dịch Ren'Py: {error}")
            return False

        if self._is_cancelled(is_cancelled):
            return False

        updated = generator.write_translations(translations)
        message = (
            f"Dịch Ren'Py hoàn tất: đã cập nhật {updated}/{total} mẫu dịch, "
            f"unique={result.stats.unique}, rejected={result.stats.validation_rejected}."
        )
        logger.info(message)
        if progress_callback:
            progress_callback(total, total, message)
        return True
