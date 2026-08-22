from __future__ import annotations

from collections.abc import Sequence

from atm.core.translation.pipeline import (
    TranslatableString,
    TranslationOrigin,
    TranslationPipeline,
)


class ContextCache:
    def __init__(self, values=None):
        self.values = values or {}
        self.get_calls = []
        self.set_calls = []
        self.saved = False

    def get(self, source_lang, target_lang, text, *, category="unknown"):
        self.get_calls.append((source_lang, target_lang, text, category))
        return self.values.get((source_lang, target_lang, text, category))

    def set_batch(
        self, source_lang, target_lang, texts, translated_texts, *, category="unknown"
    ):
        self.set_calls.append(
            (source_lang, target_lang, list(texts), list(translated_texts), category)
        )

    def save_to_disk(self):
        self.saved = True


class ContextTranslator:
    def __init__(self, translations):
        self.translations = translations
        self.calls = []

    def translate_batch(
        self, texts: Sequence[str], target_lang="vi", source_lang="auto", *, category="unknown", **kwargs
    ):
        self.calls.append((list(texts), target_lang, source_lang, category))
        return [self.translations[text] for text in texts]


def test_pipeline_normalizes_dedupes_and_uses_glossary_cache_and_api():
    writes = []
    cache = ContextCache(
        {("en", "vi", "Cached", "ui"): "Đã lưu"}
    )
    translator = ContextTranslator({"Café": "Cà phê"})
    pipeline = TranslationPipeline(
        translator,
        cache=cache,
        glossary={" Glossed ": "Thuật ngữ"},
    )

    result = pipeline.run(
        lambda: [
            TranslatableString(
                "  Cafe\u0301\n",
                path=["System.json", "title"],
                category="ui",
                writeback=writes.append,
            ),
            TranslatableString(
                "Café",
                path=["Map001.json", 0],
                category="ui",
                writeback=writes.append,
            ),
            TranslatableString("Cached", path=["System.json", "currency"], category="ui", writeback=writes.append),
            TranslatableString("Glossed", path=["Items.json", 1, "name"], category="ui", writeback=writes.append),
        ],
        source_lang="en",
        target_lang="vi",
    )

    assert result.stats.extracted == 4
    assert result.stats.normalized == 4
    assert result.stats.unique == 3
    assert result.stats.duplicate_entries == 1
    assert result.stats.cache_hits == 1
    assert result.stats.glossary_hits == 1
    assert result.stats.api_calls == 1
    assert result.stats.api_strings == 1
    assert result.stats.validation_rejected == 0
    assert translator.calls == [(["Café"], "vi", "en", "ui")]
    assert writes == ["  Cà phê\n", "Cà phê", "Đã lưu", "Thuật ngữ"]
    assert cache.set_calls == [
        ("en", "vi", ["Café"], ["Cà phê"], "ui")
    ]
    assert cache.saved is True
    assert all(item.accepted for item in result.results)


def test_pipeline_rejects_empty_ellipsis_and_broken_protected_tokens_without_writeback():
    writes = []
    translator = ContextTranslator(
        {
            "Hello <<0>> <<1>><<2>>": "Xin chào <<0>> <<1>>",
            "Blank": "   ",
            "Dots": "...",
            "Safe <<0>><<1>><<2>>": "An toàn <<0>><<1>><<2>>",
        }
    )
    pipeline = TranslationPipeline(translator)

    result = pipeline.run(
        [
            TranslatableString("Hello [player] {i}<<0>>", path=(0,), category="dialogue", writeback=writes.append),
            TranslatableString("Blank", path=(1,), category="dialogue", writeback=writes.append),
            TranslatableString("Dots", path=(2,), category="dialogue", writeback=writes.append),
            TranslatableString("Safe {b}[name]<<1>>", path=(3,), category="dialogue", writeback=writes.append),
        ]
    )

    assert result.stats.validation_rejected == 3
    assert result.stats.validation_rejected_entries == 3
    assert result.stats.written == 1
    assert writes == ["An toàn {b}[name]<<1>>"]
    assert [item.accepted for item in result.results] == [False, False, False, True]
    assert result.results[0].validation.reason == "protected tag/placeholder mismatch"
    assert result.results[1].validation.reason == "translation is empty"
    assert result.results[2].validation.reason == "translation contains only an ellipsis"
    assert result.results[3].origin is TranslationOrigin.API


class LegacyCache:
    """Intentionally has the pre-context cache signature."""

    def __init__(self):
        self.set_calls = []

    def get(self, source_lang, target_lang, text, **kwargs):
        return None

    def set_batch(self, source_lang, target_lang, texts, translated_texts, **kwargs):
        self.set_calls.append((source_lang, target_lang, list(texts), list(translated_texts)))


class LegacyTranslator:
    """Intentionally has the pre-context translator signature."""

    def __init__(self):
        self.calls = []

    def translate_batch(self, texts, target_lang="vi", source_lang="auto", **kwargs):
        self.calls.append((list(texts), target_lang, source_lang))
        return [f"vi:{text}" for text in texts]


class RecordingMemory:
    def __init__(self):
        self.remembered = []

    def remember(
        self,
        source_text,
        translation,
        source_lang,
        target_lang,
        category="unknown",
        **kwargs,
    ):
        self.remembered.append(
            (source_text, translation, source_lang, target_lang, category, kwargs)
        )


def test_pipeline_keeps_categories_separate_with_legacy_dependencies_and_only_remembers_accepted_text():
    cache = LegacyCache()
    translator = LegacyTranslator()
    memory = RecordingMemory()
    pipeline = TranslationPipeline(
        translator,
        cache=cache,
        translation_memory=memory,
        remember_api_results=True,
    )

    result = pipeline.run(
        [
            TranslatableString("Save", path=(0,), category="ui"),
            TranslatableString("Save", path=(1,), category="dialogue"),
        ],
        source_lang="en",
        target_lang="vi",
    )

    assert result.stats.unique == 2
    assert result.stats.api_calls == 2
    assert translator.calls == [(["Save"], "vi", "en"), (["Save"], "vi", "en")]
    assert cache.set_calls == [
        ("en", "vi", ["Save"], ["vi:Save"]),
        ("en", "vi", ["Save"], ["vi:Save"]),
    ]
    assert memory.remembered == [
        ("Save", "vi:Save", "en", "vi", "ui", {}),
        (
            "Save",
            "vi:Save",
            "en",
            "vi",
            "dialogue",
            {},
        ),
    ]
    assert result.stats.translation_memory_remembered == 2


def test_pipeline_protects_tokens_before_api_and_restores_them_before_writeback():
    writes = []

    class TokenCheckingTranslator:
        def __init__(self):
            self.calls = []

        def translate_batch(self, texts, target_lang="vi", source_lang="auto", *, category="unknown", **kwargs):
            self.calls.append(list(texts))
            return ["Xin chào <<0>>, <<1>>welcome<<2>>"]

    translator = TokenCheckingTranslator()
    result = TranslationPipeline(translator).run(
        [
            TranslatableString(
                "Hello [player_name], {i}welcome{/i}",
                category="dialogue",
                writeback=writes.append,
            )
        ],
        source_lang="en",
        target_lang="vi",
    )

    assert translator.calls == [["Hello <<0>>, <<1>>welcome<<2>>"]]
    assert writes == ["Xin chào [player_name], {i}welcome{/i}"]
    assert result.stats.validation_rejected == 0


def test_pipeline_prefers_exact_translation_memory_over_cache_and_api():
    writes = []
    cache = ContextCache({("en", "vi", "Save", "ui"): "Cache Save"})

    class ExactMemory:
        def get_exact(self, source, source_lang, target_lang, category="unknown"):
            if (source, source_lang, target_lang, category) == ("Save", "en", "vi", "ui"):
                return "User Save"
            return None

    translator = ContextTranslator({"Save": "API Save"})
    result = TranslationPipeline(
        translator,
        cache=cache,
        translation_memory=ExactMemory(),
    ).run(
        [TranslatableString("Save", category="ui", writeback=writes.append)],
        source_lang="en",
        target_lang="vi",
    )

    assert writes == ["User Save"]
    assert translator.calls == []
    assert result.results[0].origin is TranslationOrigin.TRANSLATION_MEMORY


def test_pipeline_protects_glossary_terms_before_api_translation():
    writes = []

    class GlossaryCheckingTranslator:
        def __init__(self):
            self.calls = []

        def translate_batch(self, texts, target_lang="vi", source_lang="en", *, category="item", **kwargs):
            self.calls.append(list(texts))
            return ["<<0>> toa sáng cho <<1>>"]

    translator = GlossaryCheckingTranslator()
    TranslationPipeline(
        translator,
        glossary={"Holy Sword": "Thánh Kiếm"},
    ).run(
        [
            TranslatableString(
                "Holy Sword shines for [actor]",
                category="item",
                writeback=writes.append,
            )
        ],
        source_lang="en",
        target_lang="vi",
    )

    assert translator.calls == [["<<0>> shines for <<1>>"]]
    assert writes == ["Thánh Kiếm toa sáng cho [actor]"]
