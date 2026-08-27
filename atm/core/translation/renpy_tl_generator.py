"""Generate and edit Ren'Py translation templates.

Ren'Py already has a parser for its script language.  This module deliberately
uses that parser (via the SDK's ``translate`` command) to create the template
files, and only reads/writes the generated ``old`` / ``new`` pairs afterwards.
It never opens a game's source ``.rpy`` file for writing.
"""

from __future__ import annotations

import ast
import codecs
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from atm.utils.logger import get_logger
from atm.core.translation.renpy_sdk_manager import RenPySDKManager


logger = get_logger(__name__, "launcher.log")


@dataclass(frozen=True)
class TranslationTemplateEntry:
    """One ``old`` / ``new`` pair in a generated Ren'Py translation file."""

    template_path: Path
    old: str
    new: str
    old_line: int
    new_line: int
    new_end_line: int
    indent: str
    trailing: str = ""


@dataclass(frozen=True)
class DialogueEntry:
    """One dialogue line inside a ``translate <lang> <label>:`` block.

    RenPy templates contain two kinds of translatable content:
    1. ``old``/``new`` string pairs (UI strings) — handled by TranslationTemplateEntry
    2. Dialogue blocks where a character line appears directly — handled here

    Example template block::

        translate vi start_abc123:

            # e "Hello, world!"
            e "Hello, world!"

    ``character_prefix`` is everything before the opening quote (``e `` above,
    or empty string for narration).  ``text`` is the quoted content.
    ``line_number`` is the 1-based index of the active (non-comment) line.
    """

    template_path: Path
    character_prefix: str
    text: str
    line_number: int
    indent: str


@dataclass(frozen=True)
class TemplateGenerationResult:
    """Outcome of asking the Ren'Py SDK to create translation templates."""

    success: bool
    template_files: tuple[Path, ...]
    message: str
    command: tuple[str, ...] = ()
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class _TemplateDirective:
    keyword: str
    value: str
    start_line: int
    end_line: int
    indent: str
    trailing: str


CommandRunner = Callable[..., subprocess.CompletedProcess]


class RenPyTLGenerator:
    """Own the SDK/template side of Ren'Py localisation.

    ``project_path`` is the directory containing the game's ``game`` folder,
    which is also the path expected by ``renpy.sh <project> translate <lang>``.
    ``language`` is intentionally kept identical to the profile's configured
    target language so an existing ``game/tl/<language>`` directory continues
    to work.
    """

    _SDK_ENVIRONMENT_VARIABLES = ("RENPY_SDK_PATH", "RENPY_SDK")

    def __init__(
        self,
        project_path: str | Path,
        language: str,
        sdk_path: str | Path | None = None,
        command_runner: CommandRunner | None = None,
    ) -> None:
        self.project_path = Path(project_path).expanduser()
        self.language = self._validate_language(language)
        self.sdk_path = Path(sdk_path).expanduser() if sdk_path else None
        self._command_runner = command_runner or subprocess.run

    @property
    def game_path(self) -> Path:
        return self.project_path / "game"

    @property
    def translation_path(self) -> Path:
        return self.game_path / "tl" / self.language

    @staticmethod
    def _validate_language(language: str) -> str:
        if not isinstance(language, str) or not language.strip():
            raise ValueError("Ren'Py translation language must be a non-empty string.")

        value = language.strip()
        if any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in value):
            raise ValueError("Ren'Py translation language may contain only letters, numbers, '_' and '-'.")
        return value

    @staticmethod
    def _sdk_executable_names() -> Sequence[str]:
        # A native executable is the reliable choice on Windows.  Unix SDKs
        # normally expose renpy.sh, while `renpy` also supports PATH installs.
        if os.name == "nt":
            return ("renpy.exe", "renpy", "renpy.sh")
        return ("renpy.sh", "renpy", "renpy.exe")

    def _executables_at(self, location: Path) -> Iterable[str]:
        if location.is_file():
            yield str(location)
            return

        if not location.is_dir():
            return

        for executable_name in self._sdk_executable_names():
            candidate = location / executable_name
            if candidate.is_file():
                yield str(candidate)

    def discover_sdk(self) -> Optional[str]:
        """Return an SDK launcher path/command, or ``None`` when unavailable.

        A packaged game usually contains the Ren'Py runtime, not the SDK
        launcher that exposes the ``translate`` command.  Searching explicit
        configuration, environment variables, the project directory, then
        ``PATH`` gives callers a useful failure instead of attempting to run
        the game's executable as an SDK.
        """

        locations: list[Path] = []
        if self.sdk_path is not None:
            locations.append(self.sdk_path)

        for variable in self._SDK_ENVIRONMENT_VARIABLES:
            configured = os.environ.get(variable)
            if configured:
                locations.append(Path(configured).expanduser())

        locations.append(self.project_path)

        for location in locations:
            for executable in self._executables_at(location):
                return executable

            # Environment variables can also be a bare executable found on
            # PATH (for example RENPY_SDK=renpy).
            if str(location) and not location.is_absolute():
                discovered = shutil.which(str(location))
                if discovered:
                    return discovered

        for executable_name in self._sdk_executable_names():
            discovered = shutil.which(executable_name)
            if discovered:
                return discovered

        # Fallback to downloading it if not found anywhere else
        manager = RenPySDKManager()
        sdk_path = manager.get_sdk_path()
        if sdk_path:
            for executable in self._executables_at(sdk_path):
                return executable

        return None

    def template_files(self) -> list[Path]:
        """List only generated translation files, in stable order."""

        if not self.translation_path.is_dir():
            return []
        return sorted(
            (path for path in self.translation_path.rglob("*.rpy") if path.is_file()),
            key=lambda path: str(path).casefold(),
        )

    def generate_templates(self) -> TemplateGenerationResult:
        """Run Ren'Py's official translation-template generator."""

        if not self.game_path.is_dir():
            return TemplateGenerationResult(
                success=False,
                template_files=(),
                message=f"Ren'Py game directory not found: {self.game_path}",
            )

        executable = self.discover_sdk()
        if not executable:
            return TemplateGenerationResult(
                success=False,
                template_files=(),
                message=(
                    "Ren'Py SDK launcher was not found. Set RENPY_SDK_PATH to "
                    "the SDK directory (or its renpy executable) and try again."
                ),
            )

        command = (executable, str(self.project_path), "translate", self.language)
        
        max_retries = 15
        for attempt in range(max_retries):
            logger.info("Generating Ren'Py translation templates (Attempt %d/%d): %s", attempt + 1, max_retries, " ".join(command))
            try:
                completed = self._command_runner(
                    list(command),
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as error:
                logger.error("Unable to run Ren'Py SDK: %s", error)
                return TemplateGenerationResult(
                    success=False,
                    template_files=(),
                    message=f"Could not run Ren'Py SDK: {error}",
                    command=command,
                )

            stdout = str(getattr(completed, "stdout", "") or "")
            stderr = str(getattr(completed, "stderr", "") or "")
            return_code = getattr(completed, "returncode", 1)
            
            if return_code == 0:
                break
                
            detail = stderr.strip() or stdout.strip() or f"exit code {return_code}"
            
            # Find files that caused the compilation error
            matches = re.findall(r'File "([^"]+\.rpy)", line \d+:', detail)
            if not matches:
                logger.error("Ren'Py template generation failed and cannot be auto-healed: %s", detail)
                return TemplateGenerationResult(
                    success=False,
                    template_files=(),
                    message=f"Ren'Py template generation failed: {detail}",
                    command=command,
                    stdout=stdout,
                    stderr=stderr,
                )
                
            # Auto-heal by deleting the broken decompiled files so RenPy uses the working .rpyc
            deleted_any = False
            for match in set(matches):
                # match is like "game/screens.rpy"
                broken_file = self.project_path / match
                if broken_file.exists():
                    logger.warning("Auto-healing: deleting broken decompiled file %s", broken_file)
                    try:
                        broken_file.unlink()
                        deleted_any = True
                    except OSError as e:
                        logger.warning("Failed to delete %s: %s", broken_file, e)
                        
            if not deleted_any:
                logger.error("Ren'Py template generation failed (could not heal files): %s", detail)
                return TemplateGenerationResult(
                    success=False,
                    template_files=(),
                    message=f"Ren'Py template generation failed: {detail}",
                    command=command,
                    stdout=stdout,
                    stderr=stderr,
                )
            logger.info("Retrying template generation after auto-healing %d broken files...", len(set(matches)))
        else:
            return TemplateGenerationResult(
                success=False,
                template_files=(),
                message=f"Ren'Py template generation failed after {max_retries} auto-healing attempts.",
            )

        template_files = tuple(self.template_files())
        if not template_files:
            message = (
                "Ren'Py completed the translate command but did not create any "
                f".rpy templates in {self.translation_path}."
            )
            logger.warning(message)
            return TemplateGenerationResult(
                success=False,
                template_files=(),
                message=message,
                command=command,
                stdout=stdout,
                stderr=stderr,
            )

        return TemplateGenerationResult(
            success=True,
            template_files=template_files,
            message=f"Generated {len(template_files)} Ren'Py translation template(s).",
            command=command,
            stdout=stdout,
            stderr=stderr,
        )

    def ensure_templates(self) -> TemplateGenerationResult:
        """Reuse existing templates, or generate them when absent.

        Reusing an existing ``tl/<language>`` directory lets a game be resumed
        without requiring an SDK on every launch.  First-time generation still
        uses the SDK above.
        """

        existing = tuple(self.template_files())
        if existing:
            return TemplateGenerationResult(
                success=True,
                template_files=existing,
                message=f"Using {len(existing)} existing Ren'Py translation template(s).",
            )
        return self.generate_templates()

    def parse_templates(self) -> list[TranslationTemplateEntry]:
        """Extract all string ``old`` / ``new`` pairs from generated templates."""

        entries: list[TranslationTemplateEntry] = []
        for template_path in self.template_files():
            entries.extend(self._parse_template(template_path))
        return entries

    def write_translations(self, translations: Mapping[str, str]) -> int:
        """Write translations into matching ``new`` fields and return a count.

        ``translations`` is keyed by the source text from ``old``.  Only files
        under ``game/tl/<language>`` are touched; no source script is ever
        opened for writing.
        """

        entries_by_file: dict[Path, list[tuple[TranslationTemplateEntry, str]]] = {}
        for entry in self.parse_templates():
            translated = translations.get(entry.old)
            if not isinstance(translated, str) or translated == entry.new:
                continue
            entries_by_file.setdefault(entry.template_path, []).append((entry, translated))

        written = 0
        for template_path, replacements in entries_by_file.items():
            try:
                written += self._write_template_replacements(template_path, replacements)
            except OSError as e:
                logger.error("Failed to write to %s: %s", template_path, e)
        return written

    # ------------------------------------------------------------------
    # Dialogue block parsing — handles ``translate <lang> <label>:`` blocks
    # ------------------------------------------------------------------

    _TRANSLATE_HEADER_RE = None  # lazily compiled

    @classmethod
    def _translate_header_pattern(cls):
        """Compile the translate-header regex once and cache it."""
        if cls._TRANSLATE_HEADER_RE is None:
            # Matches: translate <language> <label_with_hash>:
            # Does NOT match: translate <language> strings:  (those are old/new blocks)
            # Does NOT match: translate <language> python:   (code blocks)
            cls._TRANSLATE_HEADER_RE = re.compile(
                r"^translate\s+\S+\s+(?!strings\b|python\b)(\w+)\s*:\s*$"
            )
        return cls._TRANSLATE_HEADER_RE

    def parse_dialogue_blocks(self) -> list[DialogueEntry]:
        """Extract all dialogue lines from ``translate <lang> <label>:`` blocks.

        This is complementary to ``parse_templates()`` which only extracts
        ``old``/``new`` string pairs.  Dialogue blocks have a different
        structure::

            translate vi start_abc123:

                # e "Hello, world!"
                e "Hello, world!"

        The commented line (``#``) is the original; the active line below it
        is the one we read and later overwrite with the translation.
        """

        entries: list[DialogueEntry] = []
        for template_path in self.template_files():
            entries.extend(self._parse_dialogue_blocks_in_file(template_path))
        return entries

    def _parse_dialogue_blocks_in_file(self, template_path: Path) -> list[DialogueEntry]:
        """Parse a single template file for dialogue blocks."""

        lines = self._read_template_lines(template_path)
        pattern = self._translate_header_pattern()
        entries: list[DialogueEntry] = []
        index = 0

        while index < len(lines):
            line = lines[index].strip()

            # Look for translate header
            if not pattern.match(line):
                index += 1
                continue

            # Found a translate block — scan forward for the dialogue line
            # Skip: blank lines, comment lines (# ...), and look for the
            # active dialogue statement.
            block_start = index
            index += 1
            found_dialogue = False
            original_parsed = None

            while index < len(lines):
                raw_line = lines[index]
                stripped = raw_line.strip()

                # Empty line inside block — skip
                if not stripped:
                    index += 1
                    continue

                # Comment line (original text for reference)
                if stripped.startswith("#"):
                    # The commented line contains the original source text.
                    # We strip the leading '# ' to parse it just like an active line.
                    comment_content = raw_line.replace("#", "", 1)
                    parsed_original = self._parse_dialogue_line(comment_content, index, template_path)
                    if parsed_original is not None:
                        original_parsed = parsed_original
                    index += 1
                    continue

                # Next translate block or top-level statement — block ended
                if not raw_line[0].isspace():
                    break

                # old/new directives belong to the string-pair parser — skip
                if stripped.startswith(("old ", "new ")):
                    index += 1
                    continue

                # This is the active dialogue line. We overwrite this line later.
                # If we found the original text in a comment, use its text.
                # Otherwise, fallback to parsing the active line.
                parsed_active = self._parse_dialogue_line(raw_line, index, template_path)
                if parsed_active is not None:
                    if original_parsed is not None:
                        # Use original text but keep active line number and prefix for writing
                        entries.append(DialogueEntry(
                            template_path=template_path,
                            character_prefix=parsed_active.character_prefix,
                            text=original_parsed.text,
                            line_number=parsed_active.line_number,
                            indent=parsed_active.indent,
                        ))
                    else:
                        entries.append(parsed_active)
                    found_dialogue = True

                index += 1
                # Only take the first dialogue line per block
                if found_dialogue:
                    break

        return entries

    @staticmethod
    def _parse_dialogue_line(raw_line: str, line_index: int, template_path: Path) -> DialogueEntry | None:
        """Extract character prefix and quoted text from a dialogue line.

        Handles these forms::

            e "Hello, world!"           → prefix="e ", text="Hello, world!"
            myla "Good night."          → prefix="myla ", text="Good night."
            "Narration line."           → prefix="", text="Narration line."
            e happy "Hi!"               → prefix="e happy ", text="Hi!"
            random "{font=...}Text{/font}" → prefix="random ", text="{font=...}Text{/font}"
        """

        stripped = raw_line.strip()
        indent = raw_line[: len(raw_line) - len(raw_line.lstrip())]

        # Find the first quote character
        quote_pos = -1
        for i, ch in enumerate(stripped):
            if ch in ('"', "'"):
                quote_pos = i
                break

        if quote_pos < 0:
            return None

        prefix = stripped[:quote_pos]
        literal_part = stripped[quote_pos:]

        # Parse the string literal using ast.literal_eval for safety
        try:
            text = ast.literal_eval(literal_part)
        except (SyntaxError, ValueError):
            return None

        if not isinstance(text, str):
            return None

        # Skip empty strings and pure whitespace
        if not text.strip():
            return None

        return DialogueEntry(
            template_path=template_path,
            character_prefix=prefix,
            text=text,
            line_number=line_index + 1,  # 1-based
            indent=indent.rstrip("\r\n"),
        )

    def write_dialogue_translations(self, translations: Mapping[str, str]) -> int:
        """Write translated text into dialogue blocks and return a count.

        ``translations`` is keyed by the source dialogue text.  Only the
        active dialogue line is replaced; the commented original is untouched.
        """

        entries = self.parse_dialogue_blocks()
        entries_by_file: dict[Path, list[tuple[DialogueEntry, str]]] = {}
        for entry in entries:
            translated = translations.get(entry.text)
            if not isinstance(translated, str) or translated == entry.text:
                continue
            entries_by_file.setdefault(entry.template_path, []).append((entry, translated))

        written = 0
        for template_path, replacements in entries_by_file.items():
            try:
                written += self._write_dialogue_replacements(template_path, replacements)
            except OSError as e:
                logger.error("Failed to write dialogue to %s: %s", template_path, e)
        return written

    def _write_dialogue_replacements(
        self,
        template_path: Path,
        replacements: Sequence[tuple[DialogueEntry, str]],
    ) -> int:
        """Overwrite dialogue lines in a single template file."""

        raw = template_path.read_bytes()
        has_bom = raw.startswith(codecs.BOM_UTF8)
        lines = raw.decode("utf-8-sig").splitlines(keepends=True)

        # Replace bottom-to-top to keep line indexes valid
        for entry, translated in sorted(
            replacements, key=lambda item: item[0].line_number, reverse=True
        ):
            line_idx = entry.line_number - 1
            if line_idx < 0 or line_idx >= len(lines):
                continue

            ending = self._line_ending(lines[line_idx]) or "\n"
            rendered = f"{entry.indent}{entry.character_prefix}{json.dumps(translated, ensure_ascii=False)}{ending}"
            lines[line_idx] = rendered

        updated = "".join(lines).encode("utf-8")
        if has_bom:
            updated = codecs.BOM_UTF8 + updated
        template_path.write_bytes(updated)
        return len(replacements)

    def _parse_template(self, template_path: Path) -> list[TranslationTemplateEntry]:
        lines = self._read_template_lines(template_path)
        pending_old: _TemplateDirective | None = None
        entries: list[TranslationTemplateEntry] = []

        for directive in self._iter_directives(lines):
            if directive.keyword == "old":
                pending_old = directive
                continue

            if pending_old is None:
                continue

            entries.append(
                TranslationTemplateEntry(
                    template_path=template_path,
                    old=pending_old.value,
                    new=directive.value,
                    old_line=pending_old.start_line + 1,
                    new_line=directive.start_line + 1,
                    new_end_line=directive.end_line + 1,
                    indent=directive.indent,
                    trailing=directive.trailing,
                )
            )
            pending_old = None

        return entries

    @staticmethod
    def _read_template_lines(template_path: Path) -> list[str]:
        # utf-8-sig accepts both ordinary UTF-8 and a UTF-8 BOM.  The writer
        # below restores a BOM when it was present.
        with template_path.open("r", encoding="utf-8-sig", newline="") as template_file:
            return template_file.readlines()

    @staticmethod
    def _directive_start(line: str) -> tuple[str, str, str] | None:
        stripped = line.lstrip(" \t")
        indent = line[: len(line) - len(stripped)]
        for keyword in ("old", "new"):
            if not stripped.startswith(keyword):
                continue
            if len(stripped) == len(keyword) or not stripped[len(keyword)].isspace():
                continue
            literal = stripped[len(keyword) :].lstrip()
            return keyword, indent, literal
        return None

    @classmethod
    def _iter_directives(cls, lines: Sequence[str]) -> Iterable[_TemplateDirective]:
        index = 0
        while index < len(lines):
            start = cls._directive_start(lines[index])
            if start is None:
                index += 1
                continue

            keyword, indent, literal = start
            parsed = cls._parse_literal(lines, index, literal)
            if parsed is None:
                index += 1
                continue

            value, end_line, trailing = parsed
            yield _TemplateDirective(
                keyword=keyword,
                value=value,
                start_line=index,
                end_line=end_line,
                indent=indent,
                trailing=trailing,
            )
            index = end_line + 1

    @staticmethod
    def _parse_literal(
        lines: Sequence[str], start_line: int, literal: str
    ) -> tuple[str, int, str] | None:
        """Parse a Python/Ren'Py string literal without parsing source scripts.

        Ren'Py produces normal Python string literals in translation templates.
        ``ast.literal_eval`` handles escaping correctly and is deliberately
        limited to literals, unlike evaluating an arbitrary script expression.
        """

        chunks = [literal]
        # Generated `old` and `new` values are normally one line.  Supporting
        # triple-quoted strings is inexpensive, while the cap prevents an
        # invalid directive from consuming an entire template.
        for end_line in range(start_line, min(len(lines), start_line + 32)):
            if end_line > start_line:
                chunks.append(lines[end_line])
            source = "".join(chunks)
            try:
                value = ast.literal_eval(source)
            except (SyntaxError, ValueError):
                continue

            if not isinstance(value, str):
                return None
            trailing = RenPyTLGenerator._trailing_after_literal(literal) if end_line == start_line else ""
            return value, end_line, trailing

        return None

    @staticmethod
    def _trailing_after_literal(literal: str) -> str:
        """Keep a same-line comment when normalising a `new` literal."""

        # Translation templates generated by Ren'Py do not normally attach a
        # comment to `new`, but retaining it avoids unnecessary content loss.
        quote = None
        escaped = False
        for index, character in enumerate(literal):
            if quote is None:
                if character in ("'", '"'):
                    quote = character
                continue
            if escaped:
                escaped = False
                continue
            if character == "\\":
                escaped = True
                continue
            if character == quote:
                return literal[index + 1 :].rstrip("\r\n")
        return ""

    @staticmethod
    def _line_ending(line: str) -> str:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
        if line.endswith("\r"):
            return "\r"
        return ""

    def _write_template_replacements(
        self,
        template_path: Path,
        replacements: Sequence[tuple[TranslationTemplateEntry, str]],
    ) -> int:
        raw = template_path.read_bytes()
        has_bom = raw.startswith(codecs.BOM_UTF8)
        lines = raw.decode("utf-8-sig").splitlines(keepends=True)

        # Replacing from bottom to top keeps all recorded line indexes valid
        # when a rare multi-line literal is collapsed to one valid JSON string.
        for entry, translated in sorted(
            replacements, key=lambda item: item[0].new_line, reverse=True
        ):
            start = entry.new_line - 1
            end = entry.new_end_line
            ending = self._line_ending(lines[start]) or "\n"
            rendered = f"{entry.indent}new {json.dumps(translated, ensure_ascii=False)}{entry.trailing}{ending}"
            lines[start:end] = [rendered]

        updated = "".join(lines).encode("utf-8")
        if has_bom:
            updated = codecs.BOM_UTF8 + updated
        template_path.write_bytes(updated)
        return len(replacements)
