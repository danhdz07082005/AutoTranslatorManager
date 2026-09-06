# Installation & Setup Guide / Hướng Dẫn Cài Đặt

[ **[Tiếng Việt](#-tiếng-việt)** | **[English](#-english)** ]

---

## 🇻🇳 Tiếng Việt

### 1. Dành cho Người dùng phổ thông (Gamer)
Không cần cài đặt Python, không cần dòng lệnh phức tạp. Mọi thứ đã được đóng gói sẵn trong một file `.exe` duy nhất:

1. Truy cập mục **[Releases](https://github.com/danhdz07082005/AutoTranslatorManager/releases)** của repository.
2. Tải về file thực thi `AutoTranslator.exe` mới nhất.
3. Đặt file vào một thư mục riêng (ví dụ: `D:\Tools\AutoTranslator\`) và click đúp để chạy.
4. Trình duyệt mặc định sẽ tự động mở trang quản trị tại `http://127.0.0.1:XXXXX`.
5. Bấm **Thêm Game**, chọn file chạy của game và nhấn **Bắt đầu Dịch** (hoặc **Chơi & Dịch**).

> **Lưu ý Windows SmartScreen:** Vì ứng dụng nguồn mở chưa ký chứng chỉ số đắt tiền, Windows có thể hiển thị thông báo *Unknown Publisher*. Bạn chỉ cần bấm **More info** -> **Run anyway**.

---

### 2. Dành cho Lập trình viên (Developer)
Nếu bạn muốn chạy trực tiếp từ mã nguồn hoặc tham gia phát triển:

#### Yêu cầu hệ thống:
- Hệ điều hành: Windows 10/11 (64-bit).
- Python: Phiên bản 3.10, 3.11 hoặc 3.12 (khuyến nghị 3.12).
- Git.

#### Các bước cài đặt:
1. **Clone repository:**
   ```bash
   git clone https://github.com/danhdz07082005/AutoTranslatorManager.git
   cd AutoTranslatorManager
   ```

2. **Khởi tạo môi trường ảo (Virtual Environment):**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Cài đặt các thư viện phụ thuộc:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   *Hoặc cài đặt chế độ phát triển đầy đủ (bao gồm test & build):*
   ```bash
   pip install -e .[dev]
   ```

4. **Khởi chạy ứng dụng:**
   ```bash
   python run_app.py
   ```

5. **Chạy kiểm thử (Automated Tests):**
   ```bash
   python -m pytest
   ```

---

## 🇬🇧 English

### 1. For Gamers & End-Users
No Python installation or terminal commands required. Everything is pre-bundled into a single standalone executable:

1. Visit the **[Releases](https://github.com/danhdz07082005/AutoTranslatorManager/releases)** section.
2. Download the latest `AutoTranslator.exe`.
3. Move the binary into a dedicated folder (e.g., `D:\Tools\AutoTranslator\`) and double-click to launch.
4. Your default browser will automatically open `http://127.0.0.1:XXXXX`.
5. Click **Add Game**, select your game's executable, and hit **Start** (or **Play & Translate**).

> **Windows SmartScreen Notice:** Since this open-source build lacks an expensive code-signing certificate, Windows may flag it as an *Unknown Publisher*. Simply click **More info** -> **Run anyway**.

---

### 2. For Developers & Contributors
To run from source or contribute to ATM V2:

#### Prerequisites:
- OS: Windows 10/11 (64-bit).
- Python 3.10, 3.11, or 3.12 (3.12 recommended).
- Git installed.

#### Setup Steps:
1. **Clone the repository:**
   ```bash
   git clone https://github.com/danhdz07082005/AutoTranslatorManager.git
   cd AutoTranslatorManager
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   *Or install full development & test tools:*
   ```bash
   pip install -e .[dev]
   ```

4. **Run the application:**
   ```bash
   python run_app.py
   ```

5. **Run test suite:**
   ```bash
   python -m pytest
   ```

