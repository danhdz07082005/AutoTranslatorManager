import os
import re

def get_js_files():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    js_dir = os.path.join(base_dir, "atm", "ui", "web", "js")
    
    js_files = []
    if os.path.exists(js_dir):
        for f in os.listdir(js_dir):
            if f.endswith('.js'):
                js_files.append(os.path.join(js_dir, f))
    return js_files

def test_no_innerhtml_for_dynamic_data():
    """
    Đảm bảo không sử dụng innerHTML cho các data động. 
    Chỉ cho phép innerHTML cho static icons (ví dụ svg icon).
    """
    js_files = get_js_files()
    assert len(js_files) > 0, "Không tìm thấy file JS nào"
    
    violations = []
    for fpath in js_files:
        with open(fpath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                # Nếu có dùng innerHTML với string interpolation chứa biến (game.xxx, item.xxx, etc.)
                if '.innerHTML' in line and '${' in line:
                    # Chấp nhận ngoại lệ nếu chỉ là SVG
                    if '<svg' in line and 'game.' not in line:
                        continue
                    violations.append(f"{os.path.basename(fpath)}:{i+1} -> {line.strip()}")

    # Trong games.js có một chỗ empty state dùng innerHTML nhưng nó tĩnh, không có data động.
    # Trong games.js lúc tạo game card, các phần tử động như title, path đều dùng textContent.
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
        
    assert 'textContent = game.game_name' in content, "Thiếu textContent cho game_name"
    assert 'textContent = game.exe_path' in content, "Thiếu textContent cho exe_path"
