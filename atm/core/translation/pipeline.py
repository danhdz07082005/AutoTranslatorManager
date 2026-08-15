"""Engine-agnostic translation pipeline.

The game-specific translators are responsible for finding text and for knowing how
to write it back.  This module owns the shared, safety-sensitive work in between:
normalisation, context-aware deduplication, cache/glossary lookup, translation,
validation, and optional write-back.

It deliberately depends only on small protocols instead of concrete cache or
translator classes.  That keeps it usable by both the RPG Maker JSON visitor and
the Ren'Py TL-file workflow, and makes it easy to test without network or disk
access.
"""

from __future__ import annotations

from collections import Counter, OrderedDict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
import inspect
import logging
import re
from typing import Any, Protocol, TypeAlias, runtime_checkable
import unicodedata

from atm.utils.logger import get_logger


logger = get_logger(__name__, "launcher.log")

PathPart: TypeAlias = str | int
TranslationPath: TypeAlias = tuple[PathPart, ...]
EntryWriteback: TypeAlias = Callable[[str], None]
PipelineWriter: TypeAlias = Callable[["TranslatableString", str], None]


def _coerce_path(path: Sequence[PathPart] | PathPart | None) -> TranslationPath:
    """Return a stable tuple path while accepting convenient extractor inputs."""

    if path is None:
        return ()
    if isinstance(path, (str, int)):
        return (path,)
    return tuple(path)


def _normalise_category(category: object) -> str:
    if category is None:
        return "unknown"
    value = str(category).strip()
    return value or "unknown"


@dataclass(frozen=True, slots=True)
class TranslatableString:
    """One extracted string and the information needed to write it back.

    ``path`` is intentionally engine-neutral: RPG Maker can use a JSON path,
    while Ren'Py can use a file/line path.  An extractor may either attach a
    one-argument ``writeback`` callback here, or a caller may pass one shared
    writer to :meth:`TranslationPipeline.run`.
    """

    text: str
    path: TranslationPath = ()
    category: str = "unknown"
    metadata: Mapping[str, Any] = field(
        default_factory=dict, compare=False, repr=False
    )
    writeback: EntryWriteback | None = field(
        default=None, compare=False, repr=False
    )

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("TranslatableString.text must be a string")
        if self.writeback is not None and not callable(self.writeback):
            raise TypeError("TranslatableString.writeback must be callable")
        object.__setattr__(self, "path", _coerce_path(self.path))
        object.__setattr__(self, "category", _normalise_category(self.category))
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


# A friendly alias for adapters which use the more generic term "entry".
TranslationEntry = TranslatableString


@dataclass(frozen=True, slots=True)
class NormalizedString:
    """A source string after NFC normalisation and boundary-whitespace trimming."""

    entry: TranslatableString
    text: str
    leading_whitespace: str
    trailing_whitespace: str

    @property
    def category(self) -> str:
        return self.entry.category

    @property
    def key(self) -> tuple[str, str]:
        return (self.text, self.category)

    def restore_boundary_whitespace(self, translated: str) -> str:
        """Restore only source boundary whitespace after a normalized translation."""

        return (
            self.leading_whitespace
            + normalize_text(translated)
            + self.trailing_whitespace
        )


@dataclass(frozen=True, slots=True)
class DeduplicatedText:
    """One normalized/contextual source text and every location using it."""

    text: str
    category: str
    occurrences: tuple[NormalizedString, ...]

    @property
    def key(self) -> tuple[str, str]:
        return (self.text, self.category)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """The result of checking a proposed translation before it is written."""

    is_valid: bool
    reason: str | None = None
    source_tokens: tuple[str, ...] = ()
    translated_tokens: tuple[str, ...] = ()


class TranslationOrigin(str, Enum):
    GLOSSARY = "glossary"
    TRANSLATION_MEMORY = "translation_memory"
    CACHE = "cache"
    API = "api"


@dataclass(frozen=True, slots=True)
class TranslationResult:
    """The decision for one original occurrence.

    ``translated_text`` is ``None`` for a rejected result.  This makes an
    unsafe result hard to accidentally write back; ``final_text`` is provided
    only for reporting/UI purposes and returns the untouched source on failure.
    """

    entry: TranslatableString
    normalized_source: str
    translated_text: str | None
    origin: TranslationOrigin | None
    validation: ValidationResult

    @property
    def accepted(self) -> bool:
        return self.validation.is_valid and self.translated_text is not None

    @property
    def final_text(self) -> str:
        return self.translated_text if self.accepted else self.entry.text


@dataclass(slots=True)
class PipelineStats:
    """Counters reported once per pipeline run.

    Group-level counters (for example ``cache_hits`` and
    ``validation_rejected``) reflect deduplicated source/context pairs.  The
    matching ``*_entries`` counters expose how many original write locations
    were affected.
    """

    extracted: int = 0
    normalized: int = 0
    skipped_empty: int = 0
    unique: int = 0
    duplicate_entries: int = 0
    glossary_hits: int = 0
    cache_hits: int = 0
    api_calls: int = 0
    api_strings: int = 0
    api_errors: int = 0
    accepted: int = 0
    accepted_entries: int = 0
    validation_rejected: int = 0
    validation_rejected_entries: int = 0
    written: int = 0
    writeback_failures: int = 0
    cache_write_failures: int = 0
    translation_memory_remembered: int = 0
    translation_memory_failures: int = 0


@dataclass(frozen=True, slots=True)
class PipelineResult:
    results: tuple[TranslationResult, ...]
    stats: PipelineStats
    groups: tuple[DeduplicatedText, ...]

    @property
    def items(self) -> tuple[TranslationResult, ...]:
        """Alias that reads naturally for callers iterating pipeline output."""

        return self.results

    @property
    def accepted_results(self) -> tuple[TranslationResult, ...]:
        return tuple(result for result in self.results if result.accepted)


@runtime_checkable
class TextExtractor(Protocol):
    def extract(self) -> Iterable[TranslatableString]: ...


@runtime_checkable
class BatchTranslator(Protocol):
    def translate_batch(
        self,
        texts: Sequence[str],
        target_lang: str = "vi",
        source_lang: str = "auto",
        *,
        category: str = "unknown",
    ) -> Sequence[str | None]: ...


@runtime_checkable
class TranslationCacheBackend(Protocol):
    def get(
        self,
        source_lang: str,
        target_lang: str,
        text: str,
        *,
        category: str = "unknown",
    ) -> str | None: ...

    def set_batch(
        self,
        source_lang: str,
        target_lang: str,
        texts: Sequence[str],
        translated_texts: Sequence[str],
        *,
        category: str = "unknown",
    ) -> None: ...


@runtime_checkable
class TranslationMemory(Protocol):
    """Optional persistence hook for accepted exact translations.

    The pipeline never requests suggestions from this protocol.  Fuzzy matches
    must stay a UI/user-confirmed concern rather than an automatic write-back.
    """

    def remember(
        self,
        source_text: str,
        translation: str,
        source_lang: str,
        target_lang: str,
        category: str = "unknown",
    ) -> None: ...


_PROTECTED_TOKEN_RE = re.compile(
    r"<<\s*(?P<placeholder>\d+)\s*>>|\{[^{}\r\n]*\}|\[[^\[\]\r\n]*\]"
)
_ELLIPSIS_ONLY_RE = re.compile(r"(?:(?:\.{3})|…)+$")
_CACHE_MISS = object()
_GLOSSARY_MISS = object()
_API_PLACEHOLDER_RE = re.compile(r"<<\s*(\d+)\s*>>")


def normalize_text(text: str) -> str:
    """Use NFC and trim boundary whitespace for stable cache/dedupe keys."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return unicodedata.normalize("NFC", text).strip()


def protected_tokens(text: str) -> tuple[str, ...]:
    """Return Ren'Py/RPG-Maker placeholders and tags that must survive translation."""

    tokens: list[str] = []
    for match in _PROTECTED_TOKEN_RE.finditer(unicodedata.normalize("NFC", text)):
        placeholder = match.group("placeholder")
        # Whitespace within a numbered placeholder is not semantically relevant.
        tokens.append(f"<<{placeholder}>>" if placeholder is not None else match.group(0))
    return tuple(tokens)


def protect_translation_tokens(text: str) -> tuple[str, dict[str, str]]:
    """Replace engine placeholders/tags before text is sent to an API."""

    replacements: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        placeholder = f"<<{len(replacements)}>>"
        replacements[placeholder] = match.group(0)
        return placeholder

    return _PROTECTED_TOKEN_RE.sub(replace, text), replacements


def restore_translation_tokens(text: object, replacements: Mapping[str, str]) -> object:
    if not isinstance(text, str) or not replacements:
        return text

    def replace(match: re.Match[str]) -> str:
        placeholder = f"<<{match.group(1)}>>"
        return replacements.get(placeholder, match.group(0))

    return _API_PLACEHOLDER_RE.sub(replace, text)


def protect_glossary_terms(
    text: str, glossary_terms: Mapping[str, object]
) -> tuple[str, dict[str, str]]:
    """Protect configured glossary terms inside a sentence before API translation."""

    replacements: dict[str, str] = {}
    protected = text
    for term, translation in sorted(glossary_terms.items(), key=lambda item: len(item[0]), reverse=True):
        if not term or term == text or not isinstance(translation, str):
            continue
        pattern = re.compile(re.escape(term))

        def replace(match: re.Match[str]) -> str:
            placeholder = f"<<{9000 + len(replacements)}>>"
            replacements[placeholder] = translation
            return placeholder

        protected = pattern.sub(replace, protected)
    return protected, replacements


def restore_glossary_terms(text: object, replacements: Mapping[str, str]) -> object:
    if not isinstance(text, str) or not replacements:
        return text

    def replace(match: re.Match[str]) -> str:
        placeholder = f"<<{match.group(1)}>>"
        return replacements.get(placeholder, match.group(0))

    return _API_PLACEHOLDER_RE.sub(replace, text)


def validate_translation(source: str, translated: object) -> ValidationResult:
    """Validate a translation without attempting to repair it.

    The conservative policy is intentional: an invalid API/cache response is
    more dangerous than a source-language line left visible in a game.
    """

    source_tokens = protected_tokens(source)
    if translated is None:
        return ValidationResult(False, "translation is None", source_tokens)
    if not isinstance(translated, str):
        return ValidationResult(
            False,
            "translation is not a string",
            source_tokens,
        )

    candidate = unicodedata.normalize("NFC", translated)
    stripped = candidate.strip()
    if not stripped:
        return ValidationResult(False, "translation is empty", source_tokens)

    compact = re.sub(r"\s+", "", stripped)
    if _ELLIPSIS_ONLY_RE.fullmatch(compact):
        return ValidationResult(False, "translation contains only an ellipsis", source_tokens)

    translated_tokens = protected_tokens(candidate)
    if Counter(source_tokens) != Counter(translated_tokens):
        return ValidationResult(
            False,
            "protected tag/placeholder mismatch",
            source_tokens,
            translated_tokens,
        )

    return ValidationResult(True, source_tokens=source_tokens, translated_tokens=translated_tokens)


class TranslationPipeline:
    """Reusable Extract → Normalize → Dedupe → Translate → Validate → Write-back flow.

    ``cache`` and ``translator`` can be the existing ``TranslationCache`` and
    ``BaseTranslator`` instances.  Both the old three-argument cache API and a
    newer context-aware ``category`` API are supported during migration.
    """

    def __init__(
        self,
        translator: BatchTranslator | Callable[..., Sequence[str | None]] | None,
        *,
        cache: TranslationCacheBackend | object | None = None,
        glossary: Mapping[object, object] | None = None,
        translation_memory: TranslationMemory | object | None = None,
        remember_api_results: bool = False,
        log: logging.Logger | None = None,
    ) -> None:
        self.translator = translator
        self.cache = cache
        self.glossary = glossary or {}
        self.translation_memory = translation_memory
        self.remember_api_results = remember_api_results
        self.log = log or logger

    def extract(
        self,
        entries_or_extractor: Iterable[object]
        | TextExtractor
        | Callable[[], Iterable[object]]
        | TranslatableString,
    ) -> tuple[TranslatableString, ...]:
        """Materialize extractor output into the common entry data class."""

        source: object = entries_or_extractor
        extractor = getattr(source, "extract", None)
        if callable(extractor):
            source = extractor()
        elif callable(source):
            source = source()

        if isinstance(source, (TranslatableString, str)):
            raw_entries: Iterable[object] = (source,)
        elif isinstance(source, Mapping) and ("text" in source or "old" in source):
            raw_entries = (source,)
        else:
            try:
                raw_entries = iter(source)  # type: ignore[arg-type]
            except TypeError as exc:
                raise TypeError(
                    "entries_or_extractor must yield translatable entries"
                ) from exc

        return tuple(
            self._coerce_entry(raw_entry, index)
            for index, raw_entry in enumerate(raw_entries)
        )

    @staticmethod
    def normalize(entries: Iterable[TranslatableString]) -> tuple[NormalizedString, ...]:
        normalized: list[NormalizedString] = []
        for entry in entries:
            full_text = unicodedata.normalize("NFC", entry.text)
            core_text = full_text.strip()
            if not core_text:
                continue
            leading = full_text[: len(full_text) - len(full_text.lstrip())]
            trailing = full_text[len(full_text.rstrip()) :]
            normalized.append(
                NormalizedString(
                    entry=entry,
                    text=core_text,
                    leading_whitespace=leading,
                    trailing_whitespace=trailing,
                )
            )
        return tuple(normalized)

    @staticmethod
    def deduplicate(entries: Iterable[NormalizedString]) -> tuple[DeduplicatedText, ...]:
        grouped: OrderedDict[tuple[str, str], list[NormalizedString]] = OrderedDict()
        for entry in entries:
            grouped.setdefault(entry.key, []).append(entry)
        return tuple(
            DeduplicatedText(text, category, tuple(occurrences))
            for (text, category), occurrences in grouped.items()
        )

    def run(
        self,
        entries_or_extractor: Iterable[object]
        | TextExtractor
        | Callable[[], Iterable[object]]
        | TranslatableString,
        *,
        source_lang: str = "auto",
        target_lang: str = "vi",
        glossary: Mapping[object, object] | None = None,
        writer: PipelineWriter | object | None = None,
    ) -> PipelineResult:
        """Run all stages and write only translations that pass validation."""

        extracted = self.extract(entries_or_extractor)
        stats = PipelineStats(extracted=len(extracted))
        normalized = self.normalize(extracted)
        stats.normalized = len(normalized)
        stats.skipped_empty = stats.extracted - stats.normalized
        groups = self.deduplicate(normalized)
        stats.unique = len(groups)
        stats.duplicate_entries = stats.normalized - stats.unique

        source_lang = source_lang or "auto"
        target_lang = target_lang or "vi"
        active_glossary = self._normalise_glossary(
            self.glossary if glossary is None else glossary
        )
        candidates = self._resolve_candidates(
            groups,
            source_lang=source_lang,
            target_lang=target_lang,
            glossary=active_glossary,
            stats=stats,
        )

        results: list[TranslationResult] = []
        cache_writes: OrderedDict[str, list[tuple[str, str]]] = OrderedDict()
        for group in groups:
            candidate, origin = candidates.get(group.key, (None, None))
            validation = validate_translation(group.text, candidate)
            if not validation.is_valid:
                stats.validation_rejected += 1
                stats.validation_rejected_entries += len(group.occurrences)
                self.log.warning(
                    "Rejected %s translation for category=%s at %s location(s): %s",
                    origin.value if origin is not None else "missing",
                    group.category,
                    len(group.occurrences),
                    validation.reason,
                )
                results.extend(
                    TranslationResult(
                        entry=occurrence.entry,
                        normalized_source=group.text,
                        translated_text=None,
                        origin=origin,
                        validation=validation,
                    )
                    for occurrence in group.occurrences
                )
                continue

            # Validation guarantees ``candidate`` is a non-empty string here.
            assert isinstance(candidate, str)
            normalized_translation = normalize_text(candidate)
            stats.accepted += 1
            stats.accepted_entries += len(group.occurrences)
            if origin is TranslationOrigin.API:
                cache_writes.setdefault(group.category, []).append(
                    (group.text, normalized_translation)
                )
            if origin is TranslationOrigin.API and self.remember_api_results:
                self._remember_translation(
                    group,
                    normalized_translation,
                    source_lang,
                    target_lang,
                    stats,
                )

            for occurrence in group.occurrences:
                translated_text = occurrence.restore_boundary_whitespace(
                    normalized_translation
                )
                result = TranslationResult(
                    entry=occurrence.entry,
                    normalized_source=group.text,
                    translated_text=translated_text,
                    origin=origin,
                    validation=validation,
                )
                results.append(result)
                self._write_if_requested(result, writer, stats)

        self._write_cache(
            cache_writes,
            source_lang=source_lang,
            target_lang=target_lang,
            stats=stats,
        )
        self._log_stats(stats)
        return PipelineResult(tuple(results), stats, groups)

    def process(self, *args: Any, **kwargs: Any) -> PipelineResult:
        """Alias for callers that prefer ``process`` over ``run``."""

        return self.run(*args, **kwargs)

    def _coerce_entry(self, raw_entry: object, index: int) -> TranslatableString:
        if isinstance(raw_entry, TranslatableString):
            return raw_entry
        if isinstance(raw_entry, str):
            return TranslatableString(raw_entry, path=(index,))

        if isinstance(raw_entry, Mapping):
            text = raw_entry.get("text", raw_entry.get("old"))
            path = raw_entry.get("path", (index,))
            category = raw_entry.get("category", "unknown")
            metadata = raw_entry.get("metadata", {})
            writeback = raw_entry.get("writeback")
        else:
            text = getattr(raw_entry, "text", getattr(raw_entry, "old", None))
            path = getattr(raw_entry, "path", (index,))
            category = getattr(raw_entry, "category", "unknown")
            metadata = getattr(raw_entry, "metadata", {})
            writeback = getattr(raw_entry, "writeback", None)

        if not isinstance(text, str):
            raise TypeError(
                "extracted entries must be strings or expose a string text/old attribute"
            )
        if not isinstance(metadata, Mapping):
            metadata = {}
        return TranslatableString(
            text=text,
            path=path,
            category=category,
            metadata=metadata,
            writeback=writeback,
        )

    def _resolve_candidates(
        self,
        groups: Sequence[DeduplicatedText],
        *,
        source_lang: str,
        target_lang: str,
        glossary: tuple[dict[str, object], dict[tuple[str, str], object]],
        stats: PipelineStats,
    ) -> dict[tuple[str, str], tuple[object, TranslationOrigin | None]]:
        candidates: dict[tuple[str, str], tuple[object, TranslationOrigin | None]] = {}
        unresolved: list[DeduplicatedText] = []
        generic_glossary, contextual_glossary = glossary

        for group in groups:
            glossary_value = contextual_glossary.get(group.key, _GLOSSARY_MISS)
            if glossary_value is _GLOSSARY_MISS:
                glossary_value = generic_glossary.get(group.text, _GLOSSARY_MISS)
            if glossary_value is not _GLOSSARY_MISS:
                stats.glossary_hits += 1
                candidates[group.key] = (glossary_value, TranslationOrigin.GLOSSARY)
                continue

            memory_value = self._memory_get_exact(
                source_lang, target_lang, group.text, group.category
            )
            if memory_value is not _CACHE_MISS:
                candidates[group.key] = (
                    memory_value,
                    TranslationOrigin.TRANSLATION_MEMORY,
                )
                continue

            cached_value = self._cache_get(
                source_lang, target_lang, group.text, group.category
            )
            if cached_value is not _CACHE_MISS:
                stats.cache_hits += 1
                candidates[group.key] = (cached_value, TranslationOrigin.CACHE)
                continue
            unresolved.append(group)

        if not unresolved:
            return candidates

        by_category: OrderedDict[str, list[DeduplicatedText]] = OrderedDict()
        for group in unresolved:
            by_category.setdefault(group.category, []).append(group)

        for category, category_groups in by_category.items():
            source_texts = [group.text for group in category_groups]
            stats.api_calls += 1
            stats.api_strings += len(source_texts)
            translated = self._translate_batch(
                source_texts,
                source_lang=source_lang,
                target_lang=target_lang,
                category=category,
                stats=stats,
                glossary_terms=generic_glossary,
            )
            for group, translation in zip(category_groups, translated):
                candidates[group.key] = (translation, TranslationOrigin.API)

        return candidates

    def _translate_batch(
        self,
        texts: Sequence[str],
        *,
        source_lang: str,
        target_lang: str,
        category: str,
        stats: PipelineStats,
        glossary_terms: Mapping[str, object] | None = None,
    ) -> list[object]:
        if self.translator is None:
            self.log.warning(
                "No translator configured for %d text(s) in category=%s",
                len(texts),
                category,
            )
            return [None] * len(texts)

        method = getattr(self.translator, "translate_batch", self.translator)
        if not callable(method):
            self.log.error("Configured translator does not expose translate_batch")
            stats.api_errors += 1
            return [None] * len(texts)

        protected_texts: list[str] = []
        token_maps: list[dict[str, str]] = []
        glossary_maps: list[dict[str, str]] = []
        for text in texts:
            glossary_protected, glossary_replacements = protect_glossary_terms(
                text, glossary_terms or {}
            )
            protected, replacements = protect_translation_tokens(glossary_protected)
            protected_texts.append(protected)
            token_maps.append(replacements)
            glossary_maps.append(glossary_replacements)

        try:
            raw_result = method(
                protected_texts,
                target_lang=target_lang,
                source_lang=source_lang,
                category=category,
            )
        except Exception as exc:  # API failures must not cause unsafe write-back.
            stats.api_errors += 1
            self.log.error(
                "Translation API failed for category=%s (%d text(s)): %s",
                category,
                len(texts),
                exc,
            )
            return [None] * len(texts)

        if isinstance(raw_result, Mapping):
            return [
                restore_glossary_terms(
                    restore_translation_tokens(raw_result.get(text), token_maps[index]),
                    glossary_maps[index],
                )
                for index, text in enumerate(protected_texts)
            ]
        if isinstance(raw_result, (str, bytes)):
            self.log.warning(
                "Translator returned a scalar instead of %d results for category=%s",
                len(texts),
                category,
            )
            return [None] * len(texts)
        try:
            results = list(raw_result)
        except TypeError:
            self.log.warning(
                "Translator returned a non-iterable result for category=%s", category
            )
            return [None] * len(texts)

        if len(results) != len(texts):
            self.log.warning(
                "Translator result count mismatch for category=%s: expected %d, got %d",
                category,
                len(texts),
                len(results),
            )
        aligned_results = (results + [None] * len(texts))[: len(texts)]
        return [
            restore_glossary_terms(
                restore_translation_tokens(result, token_maps[index]),
                glossary_maps[index],
            )
            for index, result in enumerate(aligned_results)
        ]

    def _cache_get(
        self, source_lang: str, target_lang: str, text: str, category: str
    ) -> object:
        if self.cache is None:
            return _CACHE_MISS
        get = getattr(self.cache, "get", None)
        if not callable(get):
            self.log.warning("Configured cache does not expose get")
            return _CACHE_MISS
        try:
            value = get(source_lang, target_lang, text, category=category)
        except Exception as exc:
            self.log.warning("Cache lookup failed for category=%s: %s", category, exc)
            return _CACHE_MISS
        return _CACHE_MISS if value is None else value

    def _memory_get_exact(
        self, source_lang: str, target_lang: str, text: str, category: str
    ) -> object:
        if self.translation_memory is None:
            return _CACHE_MISS
        get_exact = getattr(self.translation_memory, "get_exact", None)
        if not callable(get_exact):
            return _CACHE_MISS
        try:
            value = get_exact(text, source_lang, target_lang, category=category)
        except Exception as exc:
            self.log.warning("Translation-memory lookup failed for category=%s: %s", category, exc)
            return _CACHE_MISS
        return _CACHE_MISS if value is None else value

    def _write_cache(
        self,
        writes: Mapping[str, Sequence[tuple[str, str]]],
        *,
        source_lang: str,
        target_lang: str,
        stats: PipelineStats,
    ) -> None:
        if self.cache is None or not writes:
            return

        set_batch = getattr(self.cache, "set_batch", None)
        if callable(set_batch):
            for category, values in writes.items():
                texts = [text for text, _ in values]
                translations = [translation for _, translation in values]
                try:
                    set_batch(source_lang, target_lang, texts, translations, category=category)
                    wrote_any = True
                except Exception as exc:
                    stats.cache_write_failures += len(values)
                    self.log.warning("Cache write failed for category=%s: %s", category, exc)
        else:
            self.log.warning("Configured cache does not expose set_batch")
            return

        save = getattr(self.cache, "save_to_disk", None)
        if wrote_any and callable(save):
            try:
                save()
            except Exception as exc:
                stats.cache_write_failures += 1
                self.log.warning("Cache save failed: %s", exc)

    def _write_if_requested(
        self,
        result: TranslationResult,
        writer: PipelineWriter | object | None,
        stats: PipelineStats,
    ) -> None:
        if not result.accepted:
            return

        try:
            if writer is not None:
                callback = getattr(writer, "write", writer)
                if not callable(callback):
                    raise TypeError("writer must be callable or expose write(entry, text)")
                callback(result.entry, result.translated_text)
            elif result.entry.writeback is not None:
                result.entry.writeback(result.translated_text)  # type: ignore[arg-type]
            else:
                return
        except Exception as exc:
            stats.writeback_failures += 1
            self.log.error("Write-back failed at path=%s: %s", result.entry.path, exc)
        else:
            stats.written += 1

    def _remember_translation(
        self,
        group: DeduplicatedText,
        translation: str,
        source_lang: str,
        target_lang: str,
        stats: PipelineStats,
    ) -> None:
        if self.translation_memory is None:
            return
        remember = getattr(self.translation_memory, "remember", None)
        if not callable(remember):
            self.log.warning("Translation memory does not expose remember")
            stats.translation_memory_failures += 1
            return
        try:
            remember(group.text, translation, source_lang, target_lang, category=group.category)
        except Exception as exc:
            stats.translation_memory_failures += 1
            self.log.warning("Translation-memory write failed: %s", exc)
        else:
            stats.translation_memory_remembered += 1

    @staticmethod
    def _normalise_glossary(
        glossary: Mapping[object, object] | None,
    ) -> tuple[dict[str, object], dict[tuple[str, str], object]]:
        generic: dict[str, object] = {}
        contextual: dict[tuple[str, str], object] = {}
        if not glossary:
            return generic, contextual

        for key, value in glossary.items():
            if isinstance(key, tuple) and len(key) == 2 and isinstance(key[0], str):
                normalized_key = normalize_text(key[0])
                if normalized_key:
                    contextual[(normalized_key, _normalise_category(key[1]))] = value
            elif isinstance(key, str):
                normalized_key = normalize_text(key)
                if normalized_key:
                    generic[normalized_key] = value
        return generic, contextual

    def _log_stats(self, stats: PipelineStats) -> None:
        self.log.info(
            "Translation pipeline: extracted=%d normalized=%d unique=%d "
            "duplicates=%d glossary_hits=%d cache_hits=%d api_calls=%d "
            "api_strings=%d validation_rejected=%d rejected_entries=%d "
            "written=%d",
            stats.extracted,
            stats.normalized,
            stats.unique,
            stats.duplicate_entries,
            stats.glossary_hits,
            stats.cache_hits,
            stats.api_calls,
            stats.api_strings,
            stats.validation_rejected,
            stats.validation_rejected_entries,
            stats.written,
        )
