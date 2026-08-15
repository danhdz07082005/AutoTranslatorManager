# Auto Translator Manager (ATM)

*(English version below)*

Một siêu công cụ giúp bạn dịch mượt mà các tựa game (Unity, RPG Maker, RenPy) với sức mạnh của **Google Translate** và **DeepL**, đi kèm với giao diện Web cực kỳ hiện đại.

Điểm đặc biệt nhất của ATM là nó **hoàn toàn không làm rác thư mục game gốc của bạn**. Tool sẽ tự động "tiêm" (inject) bộ dịch khi bạn bấm chơi, và dọn dẹp sạch sẽ khi bạn tắt game!

## 🌟 Tính năng nổi bật

| Tính năng | Mô tả |
|---|---|
| **Đa Engine** | Unity Mono, Unity IL2CPP, RPG Maker (VX/MV/MZ), RenPy |
| **Dịch Offline** | RPG Maker & RenPy: Quét file kịch bản → Dịch → Ghi lại → Chạy game |
| **Dịch Realtime** | Unity: Tiêm BepInEx + XUnity.AutoTranslator, dịch khi chơi |
| **Bộ nhớ đệm (Cache)** | Dịch 1 lần, lưu mãi mãi. Tự động giới hạn 50K entries/cặp ngôn ngữ |
| **Từ điển cá nhân (Glossary)** | Bảo vệ tên riêng khỏi bị dịch sai (vd: "Sakura" giữ nguyên) |
| **Giao diện Web** | Dark/Light mode, responsive, điều khiển mọi thứ từ trình duyệt |
| **Huỷ dịch giữa chừng** | Bấm Stop bất cứ lúc nào khi đang dịch offline |

## 🚀 Hướng Dẫn Sử Dụng Nhanh

1. **Tải về:** Lấy file `AutoTranslatorManager-Windows.zip` mới nhất tại trang [Releases](../../releases).
2. **Khởi chạy:** Giải nén và chạy `AutoTranslatorManager.exe` (không cần cài Python).
3. **Thêm Game:** Bấm **"Thêm Game Mới"** → Trỏ đến file `.exe` của game.
4. **Cấu hình:** Chọn ngôn ngữ nguồn/đích, công cụ dịch (Google/DeepL).
5. **Chơi:** Bấm **Start Translation**. Game sẽ tự dịch và mở lên!

## 🔑 DeepL API Key (Tuỳ chọn)

Mặc định ATM dùng Google Translate (miễn phí, không cần key). Muốn chất lượng cao hơn? Dùng DeepL:

1. Đăng ký tại [DeepL API Free](https://www.deepl.com/pro-api) (500K ký tự/tháng miễn phí).
2. Vào **Account → Account Summary** → Copy **Authentication Key** (kết thúc bằng `:fx`).
3. Trong ATM, vào **Cài đặt ⚙️** → Dán key → **Lưu**.
4. Đổi Engine dịch sang DeepL và tận hưởng!

## 📁 Cấu trúc dự án

```
AutoTranslatorManager/
├── atm/                          # Mã nguồn chính
│   ├── main.py                   # Entry point - khởi động server
│   ├── config/                   # Schema, cấu hình
│   ├── container/                # Dependency Injection (Bootstrap)
│   ├── core/                     # Logic lõi
│   │   ├── deployment/           #   GameDeployer, ProcessMonitor
│   │   ├── detectors/            #   Nhận dạng engine game
│   │   ├── events/               #   EventBus pub/sub
│   │   └── translation/          #   Translators, Cache, RenPy/RPG offline
│   ├── storage/                  # Repositories (Profile, Settings)
│   ├── ui/                       # HTTP Server + Web UI
│   │   ├── api.py                #   Backend API handler
│   │   ├── server.py             #   HTTP routing
│   │   └── web/                  #   Frontend (HTML/CSS/JS)
│   └── utils/                    # Logger, FileSystem
├── data/                         # Runtime data (không push lên git)
│   ├── payloads/                 #   BepInEx configs cho Unity
│   ├── profiles/                 #   Game profiles (JSON)
│   └── translation_cache.json    #   Global translation cache
├── tests/                        # Unit & Integration tests
├── start.bat                     # Khởi chạy nhanh (Windows)
├── run_app.py                    # Khởi chạy bằng Python
└── requirements.txt              # Dependencies
```

## 💻 Dành cho Lập trình viên

```bash
# Clone
git clone https://github.com/danhdz07082005/AutoTranslatorManager.git
cd AutoTranslatorManager

# Cài thư viện (Python 3.10+)
pip install -r requirements.txt

# Chạy
python run_app.py
# Hoặc: start.bat
```

## 🤝 Đóng Góp
Mã nguồn mở dưới giấy phép MIT. Mọi ý tưởng đều được chào đón!

## 📄 Bảo mật
Cache, Settings, API Key đều lưu **cục bộ** trong `data/` và được `.gitignore` bảo vệ — không bao giờ bị push lên Github.

---
---

# Auto Translator Manager (ATM) - English Version

A super tool that helps you seamlessly translate games (Unity, RPG Maker, RenPy) with the power of **Google Translate** and **DeepL**, coupled with a highly modern Web UI.

The most special feature of ATM is that it **completely leaves your original game folder pristine**. The tool will automatically "inject" the translation modules when you hit play, and completely clean up after itself when you close the game!

## 🌟 Key Features

| Feature | Description |
|---|---|
| **Multi-Engine** | Unity Mono, Unity IL2CPP, RPG Maker (VX/MV/MZ), RenPy |
| **Offline Translation** | RPG Maker & RenPy: Scan scripts → Translate → Save → Run game |
| **Realtime Translation** | Unity: Inject BepInEx + XUnity.AutoTranslator, translate while playing |
| **Smart Cache** | Translate once, keep forever. Auto limits to 50K entries/language pair |
| **Personal Glossary** | Protect specific names from being mistranslated (e.g. keep "Sakura" unchanged) |
| **Web Interface** | Dark/Light mode, responsive, control everything from your browser |
| **Mid-translation Cancel** | Hit Stop at any time during offline translation |

## 🚀 Quick Start Guide

1. **Download:** Get the latest `AutoTranslatorManager-Windows.zip` from the [Releases](../../releases) page.
2. **Launch:** Unzip and run `AutoTranslatorManager.exe` (No Python required).
3. **Add Game:** Click **"Add New Game"** → Point to the game's `.exe` file.
4. **Configure:** Choose source/target languages and translator (Google/DeepL).
5. **Play:** Click **Start Translation**. The game will be translated and launched!

## 🔑 DeepL API Key (Optional)

By default, ATM uses Google Translate (free, no key needed). Want higher quality? Use DeepL:

1. Register at [DeepL API Free](https://www.deepl.com/pro-api) (500K chars/month free).
2. Go to **Account → Account Summary** → Copy your **Authentication Key** (ends with `:fx`).
3. In ATM, go to **Settings ⚙️** → Paste the key → **Save**.
4. Change the translation Engine to DeepL and enjoy!

## 💻 For Developers

```bash
# Clone
git clone https://github.com/danhdz07082005/AutoTranslatorManager.git
cd AutoTranslatorManager

# Install dependencies (Python 3.10+)
pip install -r requirements.txt

# Run
python run_app.py
# Or: start.bat
```

## 🤝 Contributing
Open source under the MIT License. All ideas are welcome!

## 📄 Privacy & Security
Cache, Settings, and API Keys are all stored **locally** in the `data/` folder and protected by `.gitignore` — they will never be pushed to Github.
