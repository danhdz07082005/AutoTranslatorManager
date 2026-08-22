from pathlib import Path
from types import SimpleNamespace

from atm.core.translation.classification import (
    StringClassification,
    classify,
    parse_note_field,
)
from atm.core.translation.rpgmaker_translator import RPGMakerTranslator


def _translator_without_settings() -> RPGMakerTranslator:
    return RPGMakerTranslator.__new__(RPGMakerTranslator)


def test_classification_uses_file_schema_not_key_name_only():
    assert (
        classify("Potion", ["data", 1, "name"], "Items.json")[0]
        is StringClassification.TRANSLATABLE
    )
    assert (
        classify("Potion", ["plugins", 0, "name"], "PluginConfig.json")[0]
        is StringClassification.PROTECTED
    )
    assert (
        classify("Mystery", ["unknown", "name"], "CustomData.json")[0]
        is StringClassification.UNKNOWN
    )


def test_recursive_visitor_selects_schema_display_fields_and_text_events():
    data = [
        None,
        {
            "id": 1,
            "name": "Potion",
            "description": "Restores HP.",
            "message1": "Used Potion!",
            "note": "<SkillCost:100>\nDamage Formula:\na.atk * 2",
            "iconIndex": 64,
        },
    ]

    entries = list(
        _translator_without_settings().visit(data, source_file="Items.json")
    )

    assert [entry.text for entry in entries] == [
        "Potion",
        "Restores HP.",
        "Damage Formula:",
    ]
    assert entries[0].category == "item"
    assert entries[0].path == "items.json.1.name"
    assert entries[-1].path == "Items.1.note.__note_line__.1"


def test_recursive_visitor_handles_rpgmaker_choices_without_scripts():
    data = {
        "list": [
            {"code": 401, "parameters": ["Welcome, hero!"]},
            {"code": 102, "parameters": [["Yes", "No"], 0, 1, 2, 0]},
            {"code": 105, "parameters": [2, False, "Scrolling text"]},
            {"code": 355, "parameters": ["$gameParty.gainGold(100)"]},
        ],
    }

    entries = list(
        _translator_without_settings().visit(data, source_file="Map001.json")
    )

    assert [entry.text for entry in entries] == [
        "Welcome, hero!",
        "Yes",
        "No",
        "Scrolling text",
    ]
    assert entries[1].raw_path == ("list", 1, "parameters", 0, 0)
    assert all(entry.category == "dialogue" for entry in entries)


def test_parse_note_field_keeps_tags_and_code_protected():
    parts = parse_note_field("<SkillCost:100>\nDamage Formula:\na.atk * 2")

    assert [part.classification for part in parts] == [
        StringClassification.PROTECTED,
        StringClassification.TRANSLATABLE,
        StringClassification.PROTECTED,
    ]
    assert parts[1].text == "Damage Formula:"


def test_rpgmaker_overlay_keeps_original_data_unchanged(tmp_path: Path):
    game_dir = tmp_path / "Game"
    data_dir = game_dir / "data"
    data_dir.mkdir(parents=True)
    exe_path = game_dir / "Game.exe"
    exe_path.write_text("", encoding="utf-8")
    item_json = '[null, {"id": 1, "name": "Potion", "description": "Restores HP."}]'
    (data_dir / "Items.json").write_text(item_json, encoding="utf-8")

    class FakeTranslator:
        cache = None

        def translate_batch(self, texts, target_lang="vi", source_lang="en", *, category="unknown", **kwargs):
            return [f"vi:{text}" for text in texts]

    translator = RPGMakerTranslator(
        settings=SimpleNamespace(deepl_api_key=""),
        translator_factory=lambda profile, settings: FakeTranslator(),
        translation_memory=False,
        cache=False,
    )
    profile = SimpleNamespace(
        exe_path=str(exe_path),
        translator="google",
        input_lang="en",
        output_lang="vi",
        glossary={},
    )

    assert translator.translate_game(profile) is True
    assert (data_dir / "Items.json").read_text(encoding="utf-8") == item_json
    overlay = (data_dir / "translation_overlay.json").read_text(encoding="utf-8")
    assert '"items.json.1.name"' in overlay
    assert '"translation": "vi:Potion"' in overlay
    assert (game_dir / "js" / "plugins" / "ATM_Overlay.js").exists()
