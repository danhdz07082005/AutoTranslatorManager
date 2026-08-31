from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from atm.config.schema import GameProfile
from atm.core.translation.translators import RateLimitError
from atm.core.translation.cache_manager import TranslationCache
from atm.core.translation.classification import (
    StringClassification,
    TranslationEntry,
    category_for,
    classify,
    count_by_classification,
    make_entry,
    parse_note_field,
)
from atm.core.translation.pipeline import (
    TranslatableString as PipelineEntry,
    TranslationPipeline,
)
from atm.core.translation.translation_memory import TranslationMemory
from atm.core.translation.translators import DeepLTranslator, GoogleTranslator
from atm.storage.repositories.settings_repository import SettingsRepository
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")


def _normalise_key(key: Any) -> str | None:
    return key.casefold() if isinstance(key, str) else None


def _event_code(node: dict[Any, Any]) -> int | None:
    for key, value in node.items():
        if _normalise_key(key) == "code" and isinstance(value, int):
            return value
    return None


def _overlay_key(source_file: str, path: tuple[Any, ...]) -> str:
    stem = Path(source_file).stem
    return ".".join(str(part) for part in (stem, *path))


def visit(
    node: Any,
    path: list[Any] | None = None,
    *,
    source_file: str = "",
    schema: object | None = None,
) -> Iterator[TranslationEntry]:
    """Recursively yield only schema-confirmed player-facing strings."""

    current_path = [] if path is None else path
    yield from _visit(node, current_path, source_file=source_file, schema=schema)


def _visit(
    node: Any,
    path: list[Any],
    *,
    source_file: str,
    schema: object | None,
    event_code: int | None = None,
    inside_event_parameters: bool = False,
) -> Iterator[TranslationEntry]:
    if isinstance(node, str):
        classification, write_policy = classify(
            node,
            path,
            source_file,
            schema,
            event_code=event_code,
            inside_event_parameters=inside_event_parameters,
        )
        if classification is StringClassification.TRANSLATABLE:
            yield make_entry(node, source_file, path, classification, write_policy)
        elif classification is StringClassification.SPECIAL:
            yield from _visit_note_field(node, path, source_file)
        return

    if isinstance(node, list):
        for index, item in enumerate(node):
            yield from _visit(
                item,
                path + [index],
                source_file=source_file,
                schema=schema,
                event_code=event_code,
                inside_event_parameters=inside_event_parameters,
            )
        return

    if isinstance(node, dict):
        command_code = _event_code(node)
        for key, value in node.items():
            key_name = _normalise_key(key)
            is_parameters = key_name == "parameters"
            yield from _visit(
                value,
                path + [key],
                source_file=source_file,
                schema=schema,
                event_code=command_code if is_parameters else event_code,
                inside_event_parameters=is_parameters or inside_event_parameters,
            )


def _visit_note_field(
    text: str, path: list[Any], source_file: str
) -> Iterator[TranslationEntry]:
    for part in parse_note_field(text):
        if part.classification is not StringClassification.TRANSLATABLE:
            continue
        note_path = (*path, "__note_line__", part.line_index)
        yield TranslationEntry(
            original_text=part.text,
            source_file=source_file,
            path=_overlay_key(source_file, note_path),
            category=category_for(source_file, path),
            classification=StringClassification.TRANSLATABLE,
            raw_path=note_path,
        )


class RPGMakerTranslator:
    """Offline translation processor for RPG Maker MV/MZ."""

    OVERLAY_FILENAME = "translation_overlay.json"
    OVERLAY_PLUGIN_FILENAME = "ATM_Overlay.js"

    def __init__(
        self,
        settings=None,
        translator_factory: Callable[[GameProfile, object], object] | None = None,
        translation_memory: object | bool | None = None,
        cache: object | bool | None = None,
    ):
        self.settings = settings if settings is not None else SettingsRepository().load()
        self._translator_factory = translator_factory
        self._translation_memory = translation_memory
        self._cache = cache

    def visit(
        self,
        node: Any,
        path: list[Any] | None = None,
        *,
        source_file: str = "",
        schema: object | None = None,
    ) -> Iterator[TranslationEntry]:
        yield from visit(node, path, source_file=source_file, schema=schema)

    def _extract_texts_from_json(self, data: Any, source_file: str = "") -> list[str]:
        return [entry.text for entry in self.visit(data, source_file=source_file)]

    def _replace_texts_in_json(self, data: Any, translated_map: dict[str, str]) -> Any:
        """Compatibility helper for older tests; production writes an overlay."""

        for entry in self.visit(data, source_file="Map001.json"):
            translated = translated_map.get(entry.text)
            if translated is not None and "__note_line__" not in entry.raw_path:
                self._set_value_at_path(data, list(entry.raw_path), translated)
        return data

    @staticmethod
    def _set_value_at_path(data: Any, path: list[Any], value: Any) -> None:
        parent = data
        for segment in path[:-1]:
            parent = parent[segment]
        parent[path[-1]] = value

    def _get_translator(self, profile: GameProfile):
        if self._translator_factory is not None:
            return self._translator_factory(profile, self.settings)

        translator_id = getattr(profile, "translator", "google")
        if translator_id == "deepl" and self.settings and getattr(self.settings, "deepl_api_key", ""):
            return DeepLTranslator(self.settings.deepl_api_key)
        return GoogleTranslator()

    def _find_data_dirs(self, game_dir: Path) -> tuple[Path, Path] | None:
        candidates = (
            (game_dir / "www" / "data", game_dir / "www" / "data_backup"),
            (game_dir / "data", game_dir / "data_backup"),
        )
        for data_dir, backup_dir in candidates:
            if data_dir.exists():
                return data_dir, backup_dir
        return None

    def _iter_json_files(self, backup_dir: Path) -> Iterator[Path]:
        yield from sorted(
            (path for path in backup_dir.rglob("*.json") if path.name != self.OVERLAY_FILENAME),
            key=lambda path: str(path).casefold(),
        )

    def translate_game(
        self,
        profile: GameProfile,
        progress_callback: Callable[[int, int, str, dict | None], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> bool:
        game_dir = Path(profile.exe_path).expanduser().parent
        dirs = self._find_data_dirs(game_dir)
        if dirs is None:
            logger.error("Cannot find RPG Maker data folder in %s", game_dir)
            return False

        data_dir, backup_dir = dirs
        if not backup_dir.exists():
            logger.info("Creating backup for RPG Maker data...")
            shutil.copytree(data_dir, backup_dir)

        if progress_callback:
            progress_callback(0, 100, "translation.preparing", {"engine": "RPG Maker"})

        extracted_entries: list[TranslationEntry] = []
        overlay_entries: dict[str, dict[str, str]] = {}
        parsed_files: dict[Path, Any] = {}
        
        for source_file in self._iter_json_files(backup_dir):
            if is_cancelled and is_cancelled():
                return False
            try:
                with source_file.open("r", encoding="utf-8-sig") as file:
                    data = json.load(file)
                    parsed_files[source_file] = data
            except Exception as error:
                logger.error("Error scanning %s: %s", source_file, error)
                continue
            relative_file = str(source_file.relative_to(backup_dir)).replace(os.sep, "/")
            extracted_entries.extend(self.visit(data, source_file=relative_file))

        logger.info("RPG Maker classification report: %s", count_by_classification(extracted_entries))
        if not extracted_entries:
            if progress_callback:
                progress_callback(100, 100, "translation.no_strings", {})
            return True

        translator = self._get_translator(profile)
        pipeline_entries = [
            PipelineEntry(
                text=entry.original_text,
                path=(entry.path,),
                category=entry.category,
                metadata={"classification": entry.classification.value},
            )
            for entry in extracted_entries
        ]

        translated_by_path: dict[str, str] = {}
        pipeline = TranslationPipeline(
            translator,
            cache=(
                None
                if self._cache is False
                else self._cache or getattr(translator, "cache", None) or TranslationCache()
            ),
            glossary=getattr(profile, "glossary", {}) or {},
            translation_memory=(
                None
                if self._translation_memory is False
                else self._translation_memory or TranslationMemory()
            ),
        )
        result = pipeline.run(
            pipeline_entries,
            source_lang=getattr(profile, "input_lang", None),
            target_lang=getattr(profile, "output_lang", None),
            writer=lambda entry, text: translated_by_path.__setitem__(str(entry.path[0]), text),
            is_cancelled=is_cancelled,
            progress_callback=progress_callback,
        )

        rate_limited_error = None
        if getattr(result, "rate_limited", False):
            rate_limited_error = RateLimitError("Pipeline rate limited during RPG Maker translation")
            logger.warning("Rate limit hit during RPG Maker translation. Writing partial results...")

        if is_cancelled and is_cancelled():
            return False

        write_back_files: set[Path] = set()

        glossary_dict = getattr(profile, "glossary", {}) or {}
        for src_key, tgt_val in glossary_dict.items():
            if isinstance(src_key, str) and src_key and tgt_val:
                fake_path = f"__glossary__.{src_key}"
                overlay_entries[fake_path] = {
                    "source_file": "glossary",
                    "path": fake_path,
                    "category": "glossary",
                    "classification": "translatable",
                    "original": src_key,
                    "translation": str(tgt_val),
                }

        for entry in extracted_entries:
            translated = translated_by_path.get(entry.path)
            if not translated:
                continue

            if getattr(entry, "write_policy", None) == "write_back" or getattr(getattr(entry, "write_policy", None), "name", None) == "WRITE_BACK":
                source_file = backup_dir / entry.source_file
                if source_file in parsed_files:
                    self._set_value_at_path(parsed_files[source_file], list(entry.raw_path), translated)
                    write_back_files.add(source_file)
            else:
                overlay_entries[entry.path] = {
                    "source_file": entry.source_file,
                    "path": entry.path,
                    "category": entry.category,
                    "classification": entry.classification.value if hasattr(entry.classification, "value") else str(entry.classification),
                    "original": entry.original_text,
                    "translation": translated,
                }

        for source_file in write_back_files:
            relative = source_file.relative_to(backup_dir)
            dest_file = data_dir / relative
            tmp_path = dest_file.with_suffix(dest_file.suffix + ".tmp")
            tmp_path.write_text(
                json.dumps(parsed_files[source_file], ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(tmp_path, dest_file)

        if self._translation_memory:
            try:
                tm_entries = self._translation_memory.entries()
                output_lang = getattr(profile, "output_lang", None)
                if not output_lang:
                    raise ValueError("output_lang must be provided")
                for idx, tm in enumerate(tm_entries):
                    if tm.target_lang == output_lang:
                        fake_path = f"__tm_{idx}"
                        overlay_entries[fake_path] = {
                            "source_file": "tm",
                            "path": fake_path,
                            "category": "ui",
                            "classification": "translatable",
                            "original": tm.original_text,
                            "translation": tm.translated_text,
                        }
            except Exception as e:
                logger.error(f"Failed to inject TM into overlay: {e}")

        self._atomic_write_overlay(data_dir / self.OVERLAY_FILENAME, overlay_entries)
        self._install_overlay_plugin(game_dir, data_dir)

        message = (
            f"Finished RPG Maker (or paused): {len(write_back_files)} files written back, {len(overlay_entries)} entries in overlay / "
            f"{len(extracted_entries)} total entries, unique={result.stats.unique}, "
            f"rejected={result.stats.validation_rejected}."
        )
        logger.info(message)
        if progress_callback:
            progress_callback(100, 100, "translation.success" if not rate_limited_error else "translation.rate_limited", {"updated": len(write_back_files), "total": len(extracted_entries)})
            
        if rate_limited_error:
            raise rate_limited_error
            
        return True

    def _atomic_write_overlay(
        self, overlay_path: Path, entries: dict[str, dict[str, str]]
    ) -> None:
        payload = {
            "schema_version": 1,
            "entries": entries,
        }
        tmp_path = overlay_path.with_suffix(overlay_path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        json.loads(tmp_path.read_text(encoding="utf-8"))
        os.replace(tmp_path, overlay_path)

    def _install_overlay_plugin(self, game_dir: Path, data_dir: Path) -> None:
        js_dir = data_dir.parent / "js" / "plugins"
        js_dir.mkdir(parents=True, exist_ok=True)
        plugin_path = js_dir / self.OVERLAY_PLUGIN_FILENAME
        tmp_path = plugin_path.with_suffix(plugin_path.suffix + ".tmp")
        tmp_path.write_text(self._overlay_plugin_source(data_dir), encoding="utf-8")
        os.replace(tmp_path, plugin_path)

        # Patch plugins.js
        plugins_js_path = data_dir.parent / "js" / "plugins.js"
        if plugins_js_path.exists():
            try:
                content = plugins_js_path.read_text(encoding="utf-8-sig")
                if "ATM_Overlay" not in content:
                    import re, json
                    match = re.search(r'(?s)var\s+\$plugins\s*=\s*(\[.*\])\s*;', content)
                    if match:
                        try:
                            plugins_arr = json.loads(match.group(1))
                            plugins_arr.append({"name": "ATM_Overlay", "status": True, "description": "AutoTranslatorManager overlay", "parameters": {}})
                            new_arr_str = json.dumps(plugins_arr, indent=0, ensure_ascii=False)
                            new_content = content[:match.start(1)] + new_arr_str + content[match.end(1):]
                            plugins_js_path.write_text(new_content, encoding="utf-8-sig")
                            logger.info("Patched plugins.js to include ATM_Overlay.")
                        except Exception as parse_e:
                            logger.warning(f"JSON parsing plugins.js failed: {parse_e}, trying fallback...")
                            last_bracket = content.rfind("]")
                            if last_bracket != -1:
                                plugin_entry = '{"name":"ATM_Overlay","status":true,"description":"AutoTranslatorManager overlay","parameters":{}}'
                                inner_content = content[:last_bracket].strip()
                                needs_comma = not inner_content.endswith("[") and not inner_content.endswith(",")
                                prefix = ",\n" if needs_comma else "\n"
                                new_content = content[:last_bracket] + prefix + plugin_entry + "\n" + content[last_bracket:]
                                plugins_js_path.write_text(new_content, encoding="utf-8-sig")
                                logger.info("Patched plugins.js to include ATM_Overlay (fallback).")
            except Exception as e:
                logger.error(f"Failed to patch plugins.js: {e}")

    def _overlay_plugin_source(self, data_dir: Path) -> str:
        return f"""/*:
 * @plugindesc AutoTranslatorManager display overlay. Keeps RPG Maker data values unchanged.
 * @author ATM
 *
 * @help
 * Loads {self.OVERLAY_FILENAME} and swaps only text being drawn by common UI
 * windows. Original database strings remain intact for script logic.
 */
(function() {{
  "use strict";

  // Register overlay database file
  DataManager._databaseFiles.push({{ name: '$dataATMOverlay', src: '{self.OVERLAY_FILENAME}' }});

  var ATMOverlay = window.ATMOverlay = window.ATMOverlay || {{}};
  ATMOverlay.byOriginal = {{}};
  ATMOverlay.byLower = {{}};
  ATMOverlay.patched = false;

  var _Scene_Boot_isReady = Scene_Boot.prototype.isReady;
  Scene_Boot.prototype.isReady = function() {{
      var ready = _Scene_Boot_isReady.call(this);
      if (ready && !ATMOverlay.patched && window.$dataATMOverlay) {{
          ATMOverlay.buildIndexes(window.$dataATMOverlay.entries);
          ATMOverlay.patched = true;
      }}
      return ready;
  }};

  ATMOverlay.buildIndexes = function(entries) {{
      if (!entries) return;
      Object.keys(entries).forEach(function(key) {{
          var item = entries[key];
          if (item && item.original && item.translation) {{
              ATMOverlay.byOriginal[item.original] = item.translation;
              ATMOverlay.byLower[item.original.toLowerCase()] = item.translation;
          }}
      }});
  }};

  var translateText = function(text) {{
      if (typeof text !== 'string') return text;
      if (Object.prototype.hasOwnProperty.call(ATMOverlay.byOriginal, text)) {{
          return ATMOverlay.byOriginal[text];
      }}
      var lowerText = text.toLowerCase();
      if (Object.prototype.hasOwnProperty.call(ATMOverlay.byLower, lowerText)) {{
          return ATMOverlay.byLower[lowerText];
      }}
      return text;
  }};

  var drawText = Window_Base.prototype.drawText;
  Window_Base.prototype.drawText = function(text, x, y, maxWidth, align) {{
      return drawText.call(this, translateText(text), x, y, maxWidth, align);
  }};

  var drawTextEx = Window_Base.prototype.drawTextEx;
  Window_Base.prototype.drawTextEx = function(text, x, y) {{
      return drawTextEx.call(this, translateText(text), x, y);
  }};

  var bitmapDrawText = Bitmap.prototype.drawText;
  if (bitmapDrawText) {{
      Bitmap.prototype.drawText = function(text, x, y, maxWidth, lineHeight, align) {{
          return bitmapDrawText.call(this, translateText(text), x, y, maxWidth, lineHeight, align);
      }};
  }}

  var drawItemName = Window_Base.prototype.drawItemName;
  Window_Base.prototype.drawItemName = function(item, x, y, width) {{
      if (item && item.name) {{
          var clone = Object.create(item);
          clone.name = translateText(item.name);
          return drawItemName.call(this, clone, x, y, width);
      }}
      return drawItemName.call(this, item, x, y, width);
  }};
}})();
"""
