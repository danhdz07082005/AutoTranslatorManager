from __future__ import annotations

from atm.core.translation.translation_memory import TranslationMemory
from atm.storage.repositories.translation_memory_repository import (
    TranslationMemoryRepository,
)


def test_translation_memory_suggests_only_similar_same_context_entries(tmp_path):
    repository = TranslationMemoryRepository(tmp_path / "memory.json")
    memory = TranslationMemory(repository)
    memory.remember("Attack Power", "Sức mạnh tấn công", "en", "vi", "ui")
    memory.remember("Attack Power", "Tấn công", "en", "vi", "dialogue")

    suggestions = memory.suggest(
        "Attack Powers", "en", "vi", "ui", threshold=0.85
    )

    assert len(suggestions) == 1
    assert suggestions[0].translated_text == "Sức mạnh tấn công"
    assert suggestions[0].similarity >= 0.85


def test_translation_memory_never_applies_or_persists_a_suggestion_without_remember(tmp_path):
    repository = TranslationMemoryRepository(tmp_path / "memory.json")
    memory = TranslationMemory(repository)

    assert memory.suggest("Attack Power", "en", "vi", "ui") == []
    assert repository.load()["entries"] == []


def test_translation_memory_persists_user_confirmed_entries(tmp_path):
    repository = TranslationMemoryRepository(tmp_path / "memory.json")
    memory = TranslationMemory(repository)
    memory.remember("Magic Sword", "Kiếm ma thuật", "en", "vi", "item")

    reloaded = TranslationMemory(repository)
    suggestions = reloaded.suggest("Magic Swords", "en", "vi", "item")

    assert suggestions[0].translated_text == "Kiếm ma thuật"


def test_translation_memory_exact_lookup_prefers_user_confirmed_entries(tmp_path):
    repository = TranslationMemoryRepository(tmp_path / "memory.json")
    memory = TranslationMemory(repository)
    memory.remember(
        "Save",
        "Lưu tự động",
        "en",
        "vi",
        "ui",
        source="api",
        confidence="auto",
    )
    memory.remember(
        "Save",
        "Lưu",
        "en",
        "vi",
        "ui",
        source="user",
        confidence="confirmed",
    )

    assert memory.get_exact("Save", "en", "vi", "ui") == "Lưu"
