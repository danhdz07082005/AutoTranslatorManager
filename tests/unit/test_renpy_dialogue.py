"""Tests for RenPy dialogue block parsing and writing.

Covers the new DialogueEntry parser that handles ``translate <lang> <label>:``
blocks (character dialogue and narration), complementing the existing old/new
string pair tests.
"""

from pathlib import Path

from atm.core.translation.renpy_tl_generator import (
    DialogueEntry,
    RenPyTLGenerator,
)


# ---------------------------------------------------------------------------
# Fixtures — realistic RenPy template content
# ---------------------------------------------------------------------------

TEMPLATE_MIXED = """\
translate vi strings:

    old "Save"
    new "Save"

    old "Load"
    new "Load"

translate vi start_abc12345:

    # e "Hello, world!"
    e "Hello, world!"

translate vi start_def67890:

    # "This is narration."
    "This is narration."

translate vi start_ghi11111:

    # myla "Good night."
    myla "Good night."
"""

TEMPLATE_WITH_TAGS = """\
translate vi gallery_aaa00001:

    # "{font=fonts/Poppins-Light.ttf}You pushed her off.{/font}"
    "{font=fonts/Poppins-Light.ttf}You pushed her off.{/font}"

translate vi gallery_bbb00002:

    # mc "{i}Wait{/i}. Are those bruises?"
    mc "{i}Wait{/i}. Are those bruises?"
"""

TEMPLATE_EMPTY_AND_CODE = """\
translate vi python:

    pass

translate vi strings:

    old "Skip"
    new "Skip"

translate vi real_dialogue_ccc:

    # rean "Important line"
    rean "Important line"
"""


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

def test_parse_dialogue_blocks_extracts_character_and_narration(tmp_path: Path):
    """Parser must extract both character dialogue (e, myla) and narration."""
    project = tmp_path / "Project"
    tl = project / "game" / "tl" / "vi"
    tl.mkdir(parents=True)
    (tl / "script.rpy").write_text(TEMPLATE_MIXED, encoding="utf-8")

    gen = RenPyTLGenerator(project, "vi")
    entries = gen.parse_dialogue_blocks()

    assert len(entries) == 3

    # Character dialogue with prefix
    assert entries[0].character_prefix == "e "
    assert entries[0].text == "Hello, world!"

    # Narration (no prefix)
    assert entries[1].character_prefix == ""
    assert entries[1].text == "This is narration."

    # Another character
    assert entries[2].character_prefix == "myla "
    assert entries[2].text == "Good night."


def test_parse_dialogue_blocks_preserves_renpy_tags(tmp_path: Path):
    """Tags like {font=...}, {i}, {/i} must be part of the extracted text."""
    project = tmp_path / "Project"
    tl = project / "game" / "tl" / "vi"
    tl.mkdir(parents=True)
    (tl / "gallery.rpy").write_text(TEMPLATE_WITH_TAGS, encoding="utf-8")

    gen = RenPyTLGenerator(project, "vi")
    entries = gen.parse_dialogue_blocks()

    assert len(entries) == 2
    assert entries[0].text == "{font=fonts/Poppins-Light.ttf}You pushed her off.{/font}"
    assert entries[0].character_prefix == ""
    assert entries[1].text == "{i}Wait{/i}. Are those bruises?"
    assert entries[1].character_prefix == "mc "


def test_parse_dialogue_skips_strings_and_python_blocks(tmp_path: Path):
    """Blocks named 'strings' and 'python' must NOT produce dialogue entries."""
    project = tmp_path / "Project"
    tl = project / "game" / "tl" / "vi"
    tl.mkdir(parents=True)
    (tl / "mixed.rpy").write_text(TEMPLATE_EMPTY_AND_CODE, encoding="utf-8")

    gen = RenPyTLGenerator(project, "vi")
    entries = gen.parse_dialogue_blocks()

    # Only the real dialogue block, not 'python' or 'strings'
    assert len(entries) == 1
    assert entries[0].character_prefix == "rean "
    assert entries[0].text == "Important line"


def test_parse_dialogue_does_not_interfere_with_old_new_parser(tmp_path: Path):
    """old/new parser must still work correctly alongside dialogue parser."""
    project = tmp_path / "Project"
    tl = project / "game" / "tl" / "vi"
    tl.mkdir(parents=True)
    (tl / "script.rpy").write_text(TEMPLATE_MIXED, encoding="utf-8")

    gen = RenPyTLGenerator(project, "vi")

    old_new_entries = gen.parse_templates()
    dialogue_entries = gen.parse_dialogue_blocks()

    assert len(old_new_entries) == 2  # Save, Load
    assert len(dialogue_entries) == 3  # 3 dialogue blocks
    # No overlap
    old_new_texts = {e.old for e in old_new_entries}
    dialogue_texts = {e.text for e in dialogue_entries}
    assert old_new_texts.isdisjoint(dialogue_texts)


# ---------------------------------------------------------------------------
# Writer tests
# ---------------------------------------------------------------------------

def test_write_dialogue_replaces_active_line_preserving_prefix(tmp_path: Path):
    """Writer must replace dialogue text and keep character prefix + indent."""
    project = tmp_path / "Project"
    tl = project / "game" / "tl" / "vi"
    tl.mkdir(parents=True)
    template = tl / "script.rpy"
    template.write_text(TEMPLATE_MIXED, encoding="utf-8")

    gen = RenPyTLGenerator(project, "vi")
    written = gen.write_dialogue_translations({
        "Hello, world!": "Xin chào, thế giới!",
        "This is narration.": "Đây là lời dẫn truyện.",
        "Good night.": "Chúc ngủ ngon.",
    })

    assert written == 3
    content = template.read_text(encoding="utf-8")

    # Translated lines must be present with correct prefix
    assert 'e "Xin chào, thế giới!"' in content
    assert '"Đây là lời dẫn truyện."' in content
    assert 'myla "Chúc ngủ ngon."' in content

    # Original comment lines must be untouched
    assert '# e "Hello, world!"' in content
    assert '# "This is narration."' in content
    assert '# myla "Good night."' in content


def test_write_dialogue_preserves_renpy_tags_in_translation(tmp_path: Path):
    """Writer must correctly encode tags when writing translated dialogue."""
    project = tmp_path / "Project"
    tl = project / "game" / "tl" / "vi"
    tl.mkdir(parents=True)
    template = tl / "gallery.rpy"
    template.write_text(TEMPLATE_WITH_TAGS, encoding="utf-8")

    gen = RenPyTLGenerator(project, "vi")
    written = gen.write_dialogue_translations({
        "{font=fonts/Poppins-Light.ttf}You pushed her off.{/font}":
            "{font=fonts/Poppins-Light.ttf}Anh đẩy cô ấy ra.{/font}",
        "{i}Wait{/i}. Are those bruises?":
            "{i}Khoan{/i}. Đó có phải là vết bầm?",
    })

    assert written == 2
    content = template.read_text(encoding="utf-8")
    assert "{font=fonts/Poppins-Light.ttf}Anh đẩy cô ấy ra.{/font}" in content
    assert 'mc "{i}Khoan{/i}. Đó có phải là vết bầm?"' in content


def test_write_dialogue_skips_unchanged_text(tmp_path: Path):
    """Writer must NOT rewrite a line if the translation is identical to source."""
    project = tmp_path / "Project"
    tl = project / "game" / "tl" / "vi"
    tl.mkdir(parents=True)
    template = tl / "script.rpy"
    template.write_text(TEMPLATE_MIXED, encoding="utf-8")

    gen = RenPyTLGenerator(project, "vi")
    written = gen.write_dialogue_translations({
        "Hello, world!": "Hello, world!",  # same — should skip
    })

    assert written == 0


def test_old_new_and_dialogue_write_are_independent(tmp_path: Path):
    """Writing old/new and dialogue translations must not corrupt each other."""
    project = tmp_path / "Project"
    tl = project / "game" / "tl" / "vi"
    tl.mkdir(parents=True)
    template = tl / "script.rpy"
    template.write_text(TEMPLATE_MIXED, encoding="utf-8")

    gen = RenPyTLGenerator(project, "vi")

    # Write old/new first
    gen.write_translations({"Save": "Lưu", "Load": "Tải"})
    # Then write dialogue
    gen.write_dialogue_translations({"Hello, world!": "Xin chào!"})

    content = template.read_text(encoding="utf-8")
    assert 'new "Lưu"' in content
    assert 'new "Tải"' in content
    assert 'e "Xin chào!"' in content
    # Old/new entries should still parse correctly
    entries = gen.parse_templates()
    assert any(e.new == "Lưu" for e in entries)
