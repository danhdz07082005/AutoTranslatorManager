import os
import re

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


def get_html_content():
    """Đọc file index.html từ đường dẫn tương đối dự án."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    html_path = os.path.join(base_dir, "atm", "ui", "web", "index.html")
    assert os.path.exists(html_path), f"File index.html không tồn tại tại {html_path}"
    
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


def test_html_file_exists():
    """Kiểm tra file index.html tồn tại và không rỗng."""
    content = get_html_content()
    assert len(content) > 0


def test_html_structure_elements():
    """
    Kiểm tra index.html chứa đầy đủ các phần tử giao diện chính:
    - class nav-links
    - id games-container
    - id add-game-btn
    - id toast
    """
    content = get_html_content()

    if HAS_BS4:
        soup = BeautifulSoup(content, "html.parser")
        
        # 1. Kiểm tra nav-links
        nav_links = soup.find(class_="nav-links")
        assert nav_links is not None, "Không tìm thấy element có class 'nav-links'"
        
        # 2. Kiểm tra games-container
        games_container = soup.find(id="games-container")
        assert games_container is not None, "Không tìm thấy element có id 'games-container'"
        
        # 3. Kiểm tra add-game-btn
        add_game_btn = soup.find(id="add-game-btn")
        assert add_game_btn is not None, "Không tìm thấy element có id 'add-game-btn'"
        
        # 4. Kiểm tra toast
        toast = soup.find(id="toast")
        assert toast is not None, "Không tìm thấy element có id 'toast'"

    # Luôn kiểm tra thêm bằng Regex để đảm bảo độ tin cậy độc lập với thư viện
    assert re.search(r'class=["\'].*?\bnav-links\b.*?["\']', content), "Regex: Thiếu class 'nav-links'"
    assert re.search(r'id=["\']games-container["\']', content), "Regex: Thiếu id 'games-container'"
    assert re.search(r'id=["\']add-game-btn["\']', content), "Regex: Thiếu id 'add-game-btn'"
    assert re.search(r'id=["\']toast["\']', content), "Regex: Thiếu id 'toast'"


def test_html_views_sections():
    """Kiểm tra index.html chứa các view section: library-view, marketplace-view, settings-view."""
    content = get_html_content()
    
    if HAS_BS4:
        soup = BeautifulSoup(content, "html.parser")
        assert soup.find(id="library-view") is not None
        assert soup.find(id="marketplace-view") is not None
        assert soup.find(id="settings-view") is not None

    assert re.search(r'id=["\']library-view["\']', content)
    assert re.search(r'id=["\']marketplace-view["\']', content)
    assert re.search(r'id=["\']settings-view["\']', content)
