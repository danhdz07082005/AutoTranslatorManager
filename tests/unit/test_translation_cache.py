from __future__ import annotations

from atm.core.translation.cache_manager import TranslationCache
from atm.core.translation.translators import BaseTranslator
from atm.storage.repositories.translation_cache_repository import (
    TranslationCacheRepository,
)


class RecordingTranslator(BaseTranslator):
    def __init__(self, cache: TranslationCache) -> None:
        self.cache = cache
        self.calls: list[tuple[str, list[str]]] = []

    def _do_translate_batch(self, texts, target_lang, source_lang):
        self.calls.append(("active", list(texts)))
        return [f"vi:{text}" for text in texts]

    def translate_batch(self, texts, target_lang="vi", source_lang="auto", category="unknown"):
        self.calls.append((category, list(texts)))
        return super().translate_batch(texts, target_lang, source_lang, category)


def test_legacy_cache_migrates_into_unknown_context(tmp_path):
    repository = TranslationCacheRepository(tmp_path / "translation_cache.json")
    repository.save({"en": {"vi": {"Hello": "Xin chào"}}})

    cache = TranslationCache(repository)

    assert cache.get("en", "vi", "Hello", "unknown") == "Xin chào"
    assert cache.get("en", "vi", "Hello", "dialogue") is None

    persisted = repository.load()
    assert persisted["schema_version"] == 2
    assert persisted["entries"]["en"]["vi"]["unknown"]["Hello"] == "Xin chào"


def test_cache_keeps_same_text_separate_by_category(tmp_path):
    cache = TranslationCache(TranslationCacheRepository(tmp_path / "cache.json"))

    cache.set("en", "vi", "Save", "Lưu", "ui")
    cache.set("en", "vi", "Save", "Cứu", "dialogue")

    assert cache.get("en", "vi", "Save", "ui") == "Lưu"
    assert cache.get("en", "vi", "Save", "dialogue") == "Cứu"
    assert cache.get("en", "vi", "Save", "unknown") is None


def test_global_user_dictionary_entry_applies_to_each_known_category(tmp_path):
    cache = TranslationCache(TranslationCacheRepository(tmp_path / "cache.json"))

    cache.set("en", "vi", "Holy Sword", "Thánh Kiếm", "global")

    assert cache.get("en", "vi", "Holy Sword", "item") == "Thánh Kiếm"
    assert cache.get("en", "vi", "Holy Sword", "dialogue") == "Thánh Kiếm"


def test_categorized_translation_never_mixes_semantic_batches(tmp_path):
    cache = TranslationCache(TranslationCacheRepository(tmp_path / "cache.json"))
    translator = RecordingTranslator(cache)

    results = translator.translate_categorized(
        [("Yes", "ui"), ("A long line", "dialogue"), ("No", "ui")],
        source_lang="en",
        target_lang="vi",
    )

    assert results == ["vi:Yes", "vi:A long line", "vi:No"]
    semantic_calls = [call for call in translator.calls if call[0] != "active"]
    assert semantic_calls == [("ui", ["Yes", "No"]), ("dialogue", ["A long line"])]
    assert cache.get("en", "vi", "Yes", "ui") == "vi:Yes"
