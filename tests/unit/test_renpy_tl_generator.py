from pathlib import Path
from types import SimpleNamespace

from atm.core.translation.renpy_tl_generator import RenPyTLGenerator
from atm.core.translation.renpy_translator import RenPyTranslator


def test_renpy_template_parser_and_writer_touch_only_tl_files(tmp_path: Path):
    project = tmp_path / "Project"
    game = project / "game"
    tl = game / "tl" / "vi"
    tl.mkdir(parents=True)
    source = game / "script.rpy"
    source.write_text('label start:\n    e "Hello [player_name]"\n', encoding="utf-8")
    template = tl / "script.rpy"
    template.write_text(
        'translate vi start_hash:\n'
        '    old "Hello [player_name]"\n'
        '    new "Hello [player_name]"\n',
        encoding="utf-8",
    )

    generator = RenPyTLGenerator(project, "vi")
    entries = generator.parse_templates()

    assert len(entries) == 1
    assert entries[0].old == "Hello [player_name]"
    assert generator.write_translations({"Hello [player_name]": "Xin chào [player_name]"}) == 1
    assert 'new "Xin chào [player_name]"' in template.read_text(encoding="utf-8")
    assert source.read_text(encoding="utf-8") == 'label start:\n    e "Hello [player_name]"\n'


def test_renpy_translator_uses_pipeline_token_protection(tmp_path: Path):
    project = tmp_path / "Project"
    game = project / "game"
    tl = game / "tl" / "vi"
    tl.mkdir(parents=True)
    exe = project / "Game.exe"
    exe.write_text("", encoding="utf-8")
    template = tl / "script.rpy"
    template.write_text(
        'translate vi start_hash:\n'
        '    old "Hello [player_name], {i}welcome{/i}"\n'
        '    new "Hello [player_name], {i}welcome{/i}"\n',
        encoding="utf-8",
    )

    class FakeTranslator:
        cache = None

        def __init__(self):
            self.calls = []

        def translate_batch(self, texts, target_lang="vi", source_lang="en", *, category="dialogue", **kwargs):
            self.calls.append(list(texts))
            return ["Xin chào <<0>>, <<1>>welcome<<2>>"]

    fake = FakeTranslator()
    translator = RenPyTranslator(
        settings=SimpleNamespace(deepl_api_key=""),
        translator_factory=lambda profile, settings: fake,
        translation_memory=False,
        cache=False,
    )
    profile = SimpleNamespace(
        exe_path=str(exe),
        translator="google",
        input_lang="en",
        output_lang="vi",
        glossary={},
    )

    assert translator.translate_game(profile) is True
    assert fake.calls == [["Hello <<0>>, <<1>>welcome<<2>>"]]
    assert 'new "Xin chào [player_name], {i}welcome{/i}"' in template.read_text(
        encoding="utf-8"
    )
