# Auto Translator Manager (Tiếng Việt)

Một trình quản lý mã nguồn mở, thông minh dùng để dịch tự động các tựa game (Unity, RenPy) mà không làm rác thư mục gốc của game.

Auto Translator Manager (ATM) được thiết kế để tách biệt bộ máy dịch thuật (như XUnity.AutoTranslator) ra khỏi thư mục game của bạn. Hệ thống sẽ **tự động tiêm (inject)** bộ dịch vào game mỗi khi bạn ấn chơi, đảm bảo file game gốc của bạn sạch sẽ 100%. Nền tảng này còn có hệ thống Plugin mạnh mẽ, cho phép bạn đổi qua lại giữa các máy dịch AI (DeepL, Google, v.v.) chỉ với 1 click.

## 🚀 Hướng Dẫn Nhanh

1. **Tải về:** Lấy file `AutoTranslator.exe` mới nhất tại trang [Releases](../../releases).
2. **Khởi chạy:** Chạy trực tiếp file exe, không cần cài đặt Python.
3. **Thêm Game:** Chọn file chạy (`.exe`) của tựa game bạn muốn dịch.
4. **Chơi ngay:** Bấm nút "Start" và tận hưởng game đã được dịch tự động!

## 📚 Tài Liệu Hướng Dẫn

Để xem chi tiết hơn, vui lòng tham khảo các thư mục `docs/`:

- [Hướng dẫn Cài đặt](docs/installation.md)
- [Tổng quan Kiến trúc Hệ thống](docs/architecture.md)
- [Hướng dẫn Tạo Plugin Mới](docs/plugin-development.md)
- [Các câu hỏi thường gặp (FAQ)](docs/faq.md)

## 🛠️ Công Nghệ Sử Dụng

- **Python 3.12+**
- **Web UI (HTML/CSS/JS)** (Giao diện web hiện đại, hỗ trợ Light/Dark Mode).
- **Trình quản lý Engine dịch thuật** (Hỗ trợ Google Translate, DeepL API).
- **Pytest** (Tự động kiểm thử).
- **Ruff, Black, MyPy** (Quản lý chất lượng mã nguồn).

## 🤝 Tham Gia Đóng Góp

Mã nguồn mở tuyệt vời là nhờ sự đóng góp của cộng đồng. Mọi ý tưởng và dòng code của bạn đều được **chào đón nồng nhiệt**. 
Vui lòng đọc file [PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) trước khi gửi bản vá.

---

# Auto Translator Manager (English)

A smart, open-source centralized launcher for auto-translating games (Unity, RenPy) without polluting game directories.

Auto Translator Manager (ATM) is designed to separate the translation engine (like XUnity.AutoTranslator) from your game directory. It dynamically injects the translation runtime into the game only when you play, ensuring your game files remain 100% clean. It features a robust plugin system, allowing you to seamlessly swap between translation engines (DeepL, Google, etc.).

## 🚀 Quick Start

1. **Download:** Grab the latest `AutoTranslator.exe` from the [Releases](../../releases) page.
2. **Launch:** Run the executable. No Python installation required.
3. **Add Game:** Point the launcher to your game's `.exe` file.
4. **Play:** Click "Start" and enjoy your auto-translated game!

## 📚 Documentation

For detailed guides, please refer to the `docs/` folder:

- [Installation Guide](docs/installation.md)
- [Architecture Overview](docs/architecture.md)
- [Plugin Development Guide](docs/plugin-development.md)
- [Frequently Asked Questions (FAQ)](docs/faq.md)

## 🛠️ Built With

- **Python 3.12+**
- **CustomTkinter** for a modern, dark-themed UI.
- **Pytest** for end-to-end testing.
- **Ruff, Black, MyPy** for code quality.

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**. 

Please read our [PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) for details on our code of conduct, and the process for submitting pull requests to us.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
