import os
import re
import pytest

def get_i18n_js_content():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    js_path = os.path.join(base_dir, "atm", "ui", "web", "js", "core", "i18n.js")
    with open(js_path, "r", encoding="utf-8") as f:
        return f.read()

def parse_keys_for_lang(content, lang_code):
    """Trích xuất danh sách các key cho một ngôn ngữ cụ thể."""
    if lang_code == 'vi':
        parts = content.split("'vi': {")
        if len(parts) < 2:
            return set()
        block = parts[1].split("'en': {")[0]
    elif lang_code == 'en':
        parts = content.split("'en': {")
        if len(parts) < 2:
            return set()
        # Takes content up to closing of dict
        block = parts[1].split("};\n\n    let currentLang")[0]
    else:
        return set()

    keys = re.findall(r'["\']([a-zA-Z0-9_\.]+)["\']\s*:', block)
    return set(keys)

def test_i18n_completeness():
    content = get_i18n_js_content()
    vi_keys = parse_keys_for_lang(content, "vi")
    en_keys = parse_keys_for_lang(content, "en")
    
    assert len(vi_keys) > 0, "Không tìm thấy keys của tiếng Việt"
    assert len(en_keys) > 0, "Không tìm thấy keys của tiếng Anh"
    
    missing_in_en = vi_keys - en_keys
    missing_in_vi = en_keys - vi_keys
    
    error_msgs = []
    if missing_in_en:
        error_msgs.append(f"Tiếng Anh thiếu các keys sau: {missing_in_en}")
    if missing_in_vi:
        error_msgs.append(f"Tiếng Việt thiếu các keys sau: {missing_in_vi}")
        
    assert not error_msgs, "\n".join(error_msgs)
