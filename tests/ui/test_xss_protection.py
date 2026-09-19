import os
import re

def get_js_files():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    js_dir = os.path.join(base_dir, "atm", "ui", "web", "js")
    
    js_files = []
    if os.path.exists(js_dir):
        for root, dirs, files in os.walk(js_dir):
            for f in files:
                if f.endswith('.js'):
                    js_files.append(os.path.join(root, f))
    return js_files

def test_no_innerhtml_for_dynamic_data():
    """
    Đảm bảo không sử dụng innerHTML cho các data động (kể cả multi-line template literals). 
    Chỉ cho phép innerHTML cho static icons (ví dụ svg icon) hoặc static markup rỗng.
    """
    js_files = get_js_files()
    assert len(js_files) > 0, "Không tìm thấy file JS nào"
    
    violations = []
    template_pattern = re.compile(r'\.innerHTML\s*=\s*`([^`]+)`', re.DOTALL)
    
    for fpath in js_files:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # Multi-line template literals check
        for match in template_pattern.finditer(content):
            matched_text = match.group(1)
            if '${' in matched_text:
                violations.append(f"{os.path.basename(fpath)} -> innerHTML template contains interpolation: {matched_text[:80].strip()}...")

        # Single line checks
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if '.innerHTML' in line and '${' in line:
                if '<svg' in line and not any(var in line for var in ('game.', 'item.', 'g.', 'profile.', 'data.')):
                    continue
                violations.append(f"{os.path.basename(fpath)}:{i+1} -> {line.strip()}")

    assert not violations, f"Phát hiện việc sử dụng innerHTML tiềm ẩn rủi ro XSS:\n" + "\n".join(violations)

def test_dom_api_usage():
    """
    Kiểm tra xem file games.js có sử dụng textContent thay vì innerHTML cho game info không.
    """
    js_files = get_js_files()
    games_js = [f for f in js_files if "games.js" in f]
    assert len(games_js) == 1
    
    with open(games_js[0], "r", encoding="utf-8") as f:
        content = f.read()
        
    assert '.textContent =' in content, "Thiếu textContent"
