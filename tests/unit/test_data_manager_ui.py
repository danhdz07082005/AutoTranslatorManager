import os
import re

def test_data_js_integrity():
    """Kiểm tra tính toàn vẹn của atm/ui/web/js/features/data.js."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_js_path = os.path.join(base_dir, "atm", "ui", "web", "js", "features", "data.js")
    
    assert os.path.exists(data_js_path), "File data.js không tồn tại"
    
    with open(data_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Chắc chắn không còn hàm ảo loadDataStats gây ReferenceError
    assert "loadDataStats" not in content, "data.js vẫn còn tham chiếu đến hàm không tồn tại loadDataStats"

    # 2. Kiểm tra lang:changed được kết nối chính xác tới window.ATM.Data.refresh
    assert "lang:changed" in content, "data.js thiếu sự kiện lang:changed"
    assert "window.ATM.Data.refresh(true)" in content, "lang:changed phải gọi window.ATM.Data.refresh(true)"

    # 3. Kiểm tra không có code bị bỏ rơi sau })();
    content_stripped = content.strip()
    assert content_stripped.endswith("})();"), "data.js có code zombie/dead code nằm ngoài IIFE"

    # 4. Kiểm tra việc tạo DOM an toàn bằng createElement và textContent
    assert "document.createElement('div')" in content
    assert "titleDiv.textContent =" in content
    assert "folderDiv.textContent =" in content
    assert "row.appendChild(infoDiv)" in content
    assert "row.appendChild(actionsDiv)" in content

    # 5. Kiểm tra nút bấm dùng Outline Button với SVG inline
    assert "btn-secondary btn-clear-keep" in content
    assert "btn-delete btn-clear-all" in content
    assert "<svg" in content
