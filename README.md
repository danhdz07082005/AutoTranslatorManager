# Auto Translator Manager (Tiếng Việt)

Một siêu công cụ giúp bạn dịch mượt mà các tựa game (Unity, RPG Maker, RenPy) với sức mạnh của **Google Translate** và **DeepL**, đi kèm với giao diện Web cực kỳ hiện đại. 

Điểm đặc biệt nhất của Auto Translator Manager (ATM) là nó **hoàn toàn không làm rác thư mục game gốc của bạn**. Tool sẽ tự động "tiêm" (inject) bộ dịch khi bạn bấm chơi, và dọn dẹp sạch sẽ không để lại một dấu vết nào khi bạn tắt game!

## 🌟 Các tính năng nổi bật
- **Hỗ trợ Đa Engine:** Tương thích hoàn hảo với các tựa game Unity (Mono/IL2CPP), RPG Maker (VX, MV, MZ) và RenPy.
- **Trình chỉnh sửa Dịch thuật (Grid Editor):** Chỉnh sửa tay các đoạn dịch sai trực tiếp trên giao diện lưới siêu nhẹ. Sửa xong là vào game cập nhật luôn!
- **Từ điển Cá nhân (Glossary):** Gặp tên riêng (như "Sakura") bị dịch bậy? Chỉ cần thêm vào Từ điển, hệ thống sẽ bảo vệ từ đó vĩnh viễn.
- **Bộ nhớ đệm thông minh (Cache):** Dịch một lần, lưu lại dùng mãi mãi. Giúp bạn không bị tốn dung lượng API và load game cực nhanh ở các lần sau.
- **Dịch thời gian thực (RenPy Real-time):** Hỗ trợ Hook Real-time cho RenPy, vào game là dịch, không cần chờ Decompile.
- **Giao diện Web siêu mượt:** Có chế độ Light/Dark Mode, tuỳ biến màu sắc giao diện theo sở thích của bạn.

---

## 🚀 Hướng Dẫn Sử Dụng Nhanh (Dành cho người chơi)

1. **Tải về:** Lấy file `AutoTranslatorManager-Windows.zip` mới nhất tại trang [Releases](../../releases) trên Github.
2. **Khởi chạy:** Giải nén và chạy trực tiếp file `AutoTranslatorManager.exe`. (Không cần cài đặt Python hay bất kỳ phần mềm nào khác).
3. **Thêm Game:** Bấm nút **"Thêm Game Mới"** và trỏ đến file `.exe` của tựa game bạn muốn dịch.
4. **Chơi ngay:** Chọn ngôn ngữ (ví dụ: Nhật -> Việt), chọn công cụ dịch (Google / DeepL), và bấm **"Start"**. Game sẽ tự mở lên và chữ sẽ tự động hoá thành Tiếng Việt!

---

## 🔑 Hướng dẫn lấy API Key của DeepL (Khuyên dùng)
Phần mềm mặc định dùng Google Translate (Hoàn toàn miễn phí, không cần key). Nhưng nếu bạn muốn văn bản dịch có cảm xúc, sát nghĩa và mượt mà hơn, hãy dùng DeepL. 

**Cách lấy DeepL API Key miễn phí (500.000 ký tự / tháng):**
1. Truy cập trang đăng ký chính thức của DeepL: [DeepL API Free](https://www.deepl.com/pro-api).
2. Nhấn nút **Sign up for free** và tạo tài khoản. *(DeepL có thể yêu cầu bạn nhập thông tin thẻ Visa/Mastercard để chống bot spam tạo tài khoản rác. Đừng lo, họ sẽ không trừ tiền của bạn đâu).*
3. Sau khi đăng nhập thành công, nhấn vào biểu tượng Avatar góc trên bên phải -> Chọn **Account** (Tài khoản) -> Chuyển sang tab **Account Summary**.
4. Cuộn xuống dưới cùng trang, bạn sẽ thấy dòng **Authentication Key for DeepL API** (Một đoạn mã dài kết thúc bằng `:fx`).
5. Copy đoạn mã đó.
6. Mở phần mềm Auto Translator Manager, nhấn vào nút **Cài đặt** ⚙️ góc trên bên phải.
7. Dán Key vào ô **DeepL API Key** và bấm **Lưu thay đổi**.
8. Bùm! Bây giờ bạn chỉ việc ra ngoài màn hình chính, đổi Engine dịch sang DeepL và tận hưởng bản dịch chất lượng cao!

---

## 💻 Dành cho Lập trình viên (Developers)

Nếu bạn muốn chỉnh sửa, chạy mã nguồn trực tiếp hoặc tham gia đóng góp:

1. **Clone mã nguồn:**
   ```bash
   git clone https://github.com/danhdz07082005/AutoTranslatorManager.git
   ```
2. **Cài đặt thư viện:**
   Dự án yêu cầu Python 3.10+.
   ```bash
   pip install -r requirements.txt
   ```
3. **Khởi chạy:**
   ```bash
   python run_app.py
   # Hoặc click đúp vào file start.bat
   ```

## 🤝 Tham Gia Đóng Góp
Mã nguồn mở tuyệt vời là nhờ sự đóng góp của cộng đồng. Mọi ý tưởng (Bổ sung thêm engine, tối ưu code...) của bạn đều được **chào đón nồng nhiệt**. 

## 📄 Bản quyền
Dự án được phân phối dưới giấy phép MIT License. Mọi cấu hình cá nhân, Cache dịch thuật và API Key của bạn đều được lưu trữ hoàn toàn cục bộ trên máy bạn (`data/config.json`) và tuyệt đối an toàn.
