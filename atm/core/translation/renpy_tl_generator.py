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
        import re

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
