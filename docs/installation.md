# Installation Guide

## 1. Dành cho Người dùng phổ thông (Gamer)
Chỉ cần làm 3 bước đơn giản:
1. Vào mục [Releases](../../releases).
2. Tải file `AutoTranslator.exe` mới nhất.
3. Chạy file exe, trỏ đường dẫn tới game của bạn và bấm **Start**.
Không cần cài đặt Python, không cần cài thư viện. Mọi thứ đã được đóng gói sẵn!

## 2. Dành cho Lập trình viên (Developer)
Nếu bạn muốn vọc vạch mã nguồn hoặc phát triển tính năng mới:
1. **Cài đặt Python 3.12+**.
2. **Clone dự án:**
   ```bash
   git clone https://github.com/danhdz07082005/AutoTranslatorManager.git
   cd AutoTranslatorManager
   ```
3. **Cài đặt Dependency:**
   ```bash
   pip install -r requirements.txt
   ```
   *Hoặc nếu bạn dùng `pyproject.toml` chuẩn:*
   ```bash
   pip install -e .[dev]
   ```
4. **Chạy dự án:**
   ```bash
   python atm/main.py
   ```
