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

def test_all_referenced_keys_exist_in_i18n():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ui_web_dir = os.path.join(base_dir, "atm", "ui", "web")
    content = get_i18n_js_content()
    vi_keys = parse_keys_for_lang(content, "vi")
    
    referenced_keys = set()
    for root, dirs, files in os.walk(ui_web_dir):
        for f in files:
            if f.endswith('.html') or (f.endswith('.js') and f != 'i18n.js'):
                fpath = os.path.join(root, f)
                with open(fpath, 'r', encoding='utf-8') as fh:
                    txt = fh.read()
                    # Find t('key') or t("key")
                    for k in re.findall(r"\bt\(\s*['\"]([^'\"]+)['\"]", txt):
                        # ignore dynamic or template vars if any
                        if not k.startswith('${'):
                            referenced_keys.add(k)
                    # Find data-i18n="key", data-i18n-title="key", data-i18n-placeholder="key"
                    for k in re.findall(r"data-i18n(?:-[a-z]+)?=['\"]([^'\"]+)['\"]", txt):
                        referenced_keys.add(k)

    missing_keys = referenced_keys - vi_keys
    # Ignore dynamic prefix keys if any, e.g. status.
    unmatched = [k for k in missing_keys if not any(k.startswith(p) for p in ['status.'])]
    assert not unmatched, f"The following keys are referenced in UI but missing in i18n: {unmatched}"

