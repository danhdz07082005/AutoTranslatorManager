"""Semantic classification for game strings before translation.

The classifier is intentionally conservative.  A string is translated only when
the source file schema says it is display text; unknown strings stay out of the
automatic translation pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePath
import re
from typing import Any, Iterable, Sequence


class StringClassification(Enum):
    TRANSLATABLE = "translatable"
    PROTECTED = "protected"
    SPECIAL = "special"
    UNKNOWN = "unknown"

class WritePolicy(Enum):
    WRITE_BACK = "write_back"
    DISPLAY_ONLY = "display_only"
    NONE = "none"

@dataclass(frozen=True, slots=True)
class _FieldSpec:
    classification: StringClassification
    write_policy: WritePolicy
    category: str


@dataclass(slots=True)
class TranslationEntry:
    original_text: str
    translated_text: str | None = None
    source_file: str = ""
    path: str = ""
    category: str = "unknown"
    classification: StringClassification = StringClassification.UNKNOWN
    write_policy: WritePolicy = WritePolicy.NONE
    placeholders: list[str] = field(default_factory=list)
    validation_status: str = "pending"
    raw_path: tuple[Any, ...] = ()

    @property
    def text(self) -> str:
        return self.original_text


@dataclass(frozen=True, slots=True)
class NoteFieldPart:
    text: str
    line_index: int
    classification: StringClassification
    category: str = "system"


# Define schema registry mapping (filename -> {field_key -> _FieldSpec})
_SCHEMA_REGISTRY = {
    "actors.json": {
        "name": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "actor_name"),
        "nickname": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "actor_name"),
        "profile": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "actor_name"),
        "note": _FieldSpec(StringClassification.SPECIAL, WritePolicy.DISPLAY_ONLY, "system"),
    },
    "classes.json": {
        "name": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "note": _FieldSpec(StringClassification.SPECIAL, WritePolicy.DISPLAY_ONLY, "system"),
    },
    "enemies.json": {
        "name": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "actor_name"),
        "note": _FieldSpec(StringClassification.SPECIAL, WritePolicy.DISPLAY_ONLY, "system"),
    },
    "weapons.json": {
        "name": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "item"),
        "description": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "item"),
        "note": _FieldSpec(StringClassification.SPECIAL, WritePolicy.DISPLAY_ONLY, "system"),
    },
    "armors.json": {
        "name": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "item"),
        "description": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "item"),
        "note": _FieldSpec(StringClassification.SPECIAL, WritePolicy.DISPLAY_ONLY, "system"),
    },
    "items.json": {
        "name": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "item"),
        "description": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "item"),
        "note": _FieldSpec(StringClassification.SPECIAL, WritePolicy.DISPLAY_ONLY, "system"),
    },
    "skills.json": {
        "name": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "skill"),
        "description": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "skill"),
        "message1": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "skill"),
        "message2": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "skill"),
        "note": _FieldSpec(StringClassification.SPECIAL, WritePolicy.DISPLAY_ONLY, "system"),
    },
    "states.json": {
        "name": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "message1": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "message2": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "message3": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "message4": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "note": _FieldSpec(StringClassification.SPECIAL, WritePolicy.DISPLAY_ONLY, "system"),
    },
    "system.json": {
        "gametitle": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "terms": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "equiptypes": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "skilltypes": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "weapontypes": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "armortypes": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "elements": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
        "currencyunit": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "system"),
    },
    "mapinfos.json": {
        "name": _FieldSpec(StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY, "ui"),
    }
}

PROTECTED_FIELDS = {
    "id",
    "code",
    "iconindex",
    "animationid",
    "traits",
    "effects",
    "params",
    "etypeid",
    "atypeid",
    "wtypeid",
    "stypeid",
    "hittyp",
    "hitType".casefold(),
    "damage",
    "formula",
    "script",
}
EVENT_TEXT_CODES = {401, 102, 105, 108, 408}
ASSET_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".ogg", ".m4a", ".wav", ".mp3")
PLACEHOLDER_RE = re.compile(r"<<\s*\d+\s*>>|\{[^{}\r\n]*\}|\[[^\[\]\r\n]*\]")
NOTE_TAG_RE = re.compile(r"^\s*<[^>\r\n]+>\s*$")
CODELIKE_RE = re.compile(
    r"(^\s*(?:if|for|while|return|var|let|const)\b)|"
    r"[\w$]+\s*\(|[=!<>]=|[+\-*/%]=?|->|\{|\}|\[|\]"
)


def normalize_source_file(source_file: str) -> str:
    return PurePath(source_file).name.casefold()


def path_to_string(path: Sequence[Any]) -> str:
    return ".".join(str(part) for part in path)


def extract_placeholders(text: str) -> list[str]:
    return [match.group(0) for match in PLACEHOLDER_RE.finditer(text)]


def category_for(source_file: str, path: Sequence[Any]) -> str:
    filename = normalize_source_file(source_file)
    last_key = str(path[-1]).casefold() if path else ""
    
    if filename in _SCHEMA_REGISTRY:
        # Check explicit schema registry first
        if last_key in _SCHEMA_REGISTRY[filename]:
            return _SCHEMA_REGISTRY[filename][last_key].category
        if filename == "system.json":
            system_arrays = {"terms", "equiptypes", "skilltypes", "weapontypes", "armortypes", "elements"}
            if not system_arrays.isdisjoint([str(p).casefold() for p in path]):
                return "system"

    if filename == "commonevents.json" or filename == "troops.json" or filename.startswith("map"):
        return "dialogue"
    return "unknown"


def is_asset_reference(text: str) -> bool:
    return text.strip().casefold().endswith(ASSET_SUFFIXES)


def classify(
    text: str,
    path: Sequence[Any],
    source_file: str,
    file_schema: object | None = None,
    *,
    event_code: int | None = None,
    inside_event_parameters: bool = False,
) -> tuple[StringClassification, WritePolicy]:
    """Classify one JSON string using file-level schema and path context.
    Returns (StringClassification, WritePolicy)."""

    if not isinstance(text, str) or not text.strip():
        return StringClassification.PROTECTED, WritePolicy.NONE
    if is_asset_reference(text):
        return StringClassification.PROTECTED, WritePolicy.NONE

    filename = normalize_source_file(source_file)
    key = str(path[-1]).casefold() if path else ""
    key_set = {str(part).casefold() for part in path if isinstance(part, str)}

    if key in PROTECTED_FIELDS or "script" in key_set:
        return StringClassification.PROTECTED, WritePolicy.NONE

    if inside_event_parameters:
        return _classify_event_parameter(path, event_code)

    if filename in _SCHEMA_REGISTRY:
        if key in _SCHEMA_REGISTRY[filename]:
            spec = _SCHEMA_REGISTRY[filename][key]
            return spec.classification, spec.write_policy
        if filename == "system.json":
            system_arrays = {"terms", "equiptypes", "skilltypes", "weapontypes", "armortypes", "elements"}
            if not system_arrays.isdisjoint(key_set):
                return StringClassification.TRANSLATABLE, WritePolicy.DISPLAY_ONLY

    if filename.startswith("plugin") or "plugin" in filename or "config" in filename:
        return StringClassification.PROTECTED, WritePolicy.NONE

    return StringClassification.UNKNOWN, WritePolicy.NONE


def _classify_event_parameter(
    path: Sequence[Any], event_code: int | None
) -> tuple[StringClassification, WritePolicy]:
    if event_code not in EVENT_TEXT_CODES:
        return StringClassification.PROTECTED, WritePolicy.NONE

    try:
        parameters_index = next(
            index for index, part in enumerate(path) if str(part).casefold() == "parameters"
        )
    except StopIteration:
        return StringClassification.PROTECTED, WritePolicy.NONE

    relative = tuple(path[parameters_index + 1 :])
    
    # Event 401, 108, 408 are dialogue/messages and safe to write back directly to the database.
    if event_code in {401, 108, 408}:
        return (
            (StringClassification.TRANSLATABLE, WritePolicy.WRITE_BACK)
            if len(relative) == 1 and relative[0] == 0
            else (StringClassification.PROTECTED, WritePolicy.NONE)
        )
    # Scrolling text
    if event_code == 105:
        return (
            (StringClassification.TRANSLATABLE, WritePolicy.WRITE_BACK)
            if len(relative) == 1 and relative[0] == 2
            else (StringClassification.PROTECTED, WritePolicy.NONE)
        )
    # Choices
    if event_code == 102:
        return (
            (StringClassification.TRANSLATABLE, WritePolicy.WRITE_BACK)
            if len(relative) == 2 and relative[0] == 0 and isinstance(relative[1], int)
            else (StringClassification.PROTECTED, WritePolicy.NONE)
        )
    return StringClassification.PROTECTED, WritePolicy.NONE


def parse_note_field(text: str) -> list[NoteFieldPart]:
    """Split an RPG Maker note field into protected tags/code and prose labels."""

    parts: list[NoteFieldPart] = []
    for line_index, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        if NOTE_TAG_RE.match(stripped) or CODELIKE_RE.search(stripped):
            parts.append(
                NoteFieldPart(
                    text=line,
                    line_index=line_index,
                    classification=StringClassification.PROTECTED,
                )
            )
            continue
        parts.append(
            NoteFieldPart(
                text=line,
                line_index=line_index,
                classification=StringClassification.TRANSLATABLE,
            )
        )
    return parts


def make_entry(
    text: str,
    source_file: str,
    path: Sequence[Any],
    classification: StringClassification,
    write_policy: WritePolicy = WritePolicy.NONE,
) -> TranslationEntry:
    return TranslationEntry(
        original_text=text,
        source_file=source_file,
        path=path_to_string((normalize_source_file(source_file), *path)),
        category=category_for(source_file, path),
        classification=classification,
        write_policy=write_policy,
        placeholders=extract_placeholders(text),
        raw_path=tuple(path),
    )


def count_by_classification(entries: Iterable[TranslationEntry]) -> dict[str, int]:
    counts = {classification.value: 0 for classification in StringClassification}
    for entry in entries:
        counts[entry.classification.value] += 1
    return counts
