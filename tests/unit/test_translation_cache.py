import pytest
import os
from atm.core.translation.cache_manager import TranslationCache
from atm.storage.repositories.translation_cache_repository import TranslationCacheRepository


def test_legacy_cache_migrates_into_sqlite(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Create legacy JSON file
    legacy_file = data_dir / "translation_cache.json"
    repository = TranslationCacheRepository(str(legacy_file))
    repository.save({"entries": {"en": {"vi": {"default": {"Hello": "Xin cho"}}}}})

    # Should trigger migration
    cache = TranslationCache(data_dir=str(data_dir))
    
    assert cache.get("en", "vi", "Hello") == "Xin cho"
    assert (data_dir / "translation_cache.db").exists()
    assert (data_dir / "translation_cache.json.bak").exists()


def test_cache_keeps_same_text_separate_by_category(tmp_path):
    cache = TranslationCache(data_dir=str(tmp_path))
    cache.set("en", "vi", "Menu", "Thuc don", category="ui")
    cache.set("en", "vi", "Menu", "Menu man hinh", category="script")

    assert cache.get("en", "vi", "Menu", category="ui") == "Thuc don"
    assert cache.get("en", "vi", "Menu", category="script") == "Menu man hinh"


def test_global_user_dictionary_entry_applies_to_each_known_category(tmp_path):
    cache = TranslationCache(data_dir=str(tmp_path))
    cache.set("ja", "vi", "Atashi", "Toi", category=cache.MANUAL_CATEGORY)

    assert cache.get("ja", "vi", "Atashi", category="dialogue") == "Toi"
    assert cache.get("ja", "vi", "Atashi", category="ui") == "Toi"


def test_categorized_translation_never_mixes_semantic_batches(tmp_path):
    cache = TranslationCache(data_dir=str(tmp_path))
    cache.set_batch("en", "vi", ["One", "Two"], ["Mot", "Hai"], category="numbers")

    assert cache.get("en", "vi", "One", category="numbers") == "Mot"
    assert cache.get("en", "vi", "One", category="letters") is None
