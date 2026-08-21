import os
import re
import pytest

def get_i18n_js_content():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    js_path = os.path.join(base_dir, "atm", "ui", "web", "js", "i18n.js")
    with open(js_path, "r", encoding="utf-8") as f:
        return f.read()

def parse_keys_for_lang(content, lang_code):
    """Trích xuất danh sách các key cho một ngôn ngữ cụ thể bằng regex đơn giản."""
    # Tìm block của ngôn ngữ đó, ví dụ: vi: { ... }
    # Cách đơn giản: lấy tất cả các chuỗi "key": "value"
    pattern = rf"{lang_code}:\s*{{([^}}]+)}}"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return set()
    
    block = match.group(1)
    # Lấy các keys, ví dụ "menu.library"
    keys = re.findall(r'"([^"]+)":', block)
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
