# Tài liệu Toàn diện - AutoTranslatorManager (V11)

## 1. Tổng quan dự án

**AutoTranslatorManager (ATM)** là một giải pháp quản lý dịch thuật tự động (auto-translate) cho các tựa game (chủ yếu là Visual Novel và RPG) tập trung, an toàn và sạch sẽ. Dự án dành cho người chơi muốn tự dịch game nước ngoài sang tiếng Việt, và cả những người biên dịch game muốn quản lý nhiều game cùng lúc mà không làm "ô nhiễm" thư mục gốc của game.

**Vấn đề giải quyết:** 
Các công cụ dịch thuật truyền thống thường yêu cầu người dùng copy rất nhiều file patch (BepInEx, Autotranslator, overlay) trực tiếp vào thư mục game. Điều này gây ra:
- Rác thư mục game.
- Dễ xung đột phiên bản giữa các game.
- Rất khó gỡ cài đặt (uninstall) bản dịch.
- Dễ làm vỡ logic game (ví dụ: RPG Maker nếu dịch tên biến/chỉ số sẽ làm vỡ script).

**Giải pháp của ATM:**
- **Centralized Payload:** Giữ tất cả file patch, bộ dịch, và file cấu hình ở một thư mục an toàn của ATM (data/payloads).
- **Just-In-Time (JIT) Deployment:** Chỉ khi người dùng bấm "Chạy Game", ATM mới copy (deploy) các file patch này vào thư mục game, và tự động thu dọn (cleanup) lại sạch sẽ ngay khi game tắt.
- **Phân loại Thông minh (Classification):** Cơ chế chống hỏng logic game thông minh bằng cách phân loại chuỗi văn bản (`TRANSLATABLE`, `PROTECTED`, `SPECIAL`, v.v.) và chỉ dịch những phần hiển thị cho người chơi (như hộp thoại hội thoại), giữ nguyên các key/id dùng trong hệ thống.
- **Hỗ trợ Đa Engine:** 
  - **Unity (Mono / IL2CPP):** Dùng cơ chế Real-time hooks thông qua XUnity.AutoTranslator (BepInEx).
  - **RPG Maker (MV/MZ):** Cơ chế Offline Translation + In-memory Patching + Overlay. Text an toàn (`WRITE_BACK`) ghi thẳng vào database; text nguy hiểm (`DISPLAY_ONLY`) dùng Overlay.
  - **Ren'Py:** Cơ chế Offline Patching, dùng trực tiếp Ren'Py SDK để xuất template và dịch.

## 2. Kiến trúc & Cấu trúc thư mục

ATM được thiết kế theo kiến trúc **Modular Monolith** kết hợp với kiến trúc **Event-Driven**, phân tách rõ ràng giữa giao diện người dùng và logic xử lý cốt lõi.

### Các Layer:
1. **Presentation / UI (`atm/ui/`)**: Cung cấp giao diện Web (HTML/JS/CSS) giao tiếp với Backend qua HTTP API (Flask/Werkzeug).
2. **Core Logic (`atm/core/`)**: Nơi chứa trí tuệ của hệ thống: Nhận diện Engine (GameDetector), Quản lý vòng đời (GameDeployer), Dịch thuật (TranslationPipeline, Classification, Translators), và Quản lý sự kiện (EventBus).
3. **Data Access / Storage (`atm/storage/`)**: Quản lý việc lưu trữ hồ sơ game (`profiles/`), bộ nhớ dịch thuật (`translation_cache`), và thiết lập hệ thống (`settings.json`).
4. **Utils / Config (`atm/utils/`, `atm/config/`)**: Chứa định dạng dữ liệu (Schema Pydantic) và các tiện ích (Logger, File system, Network).

### Toàn bộ cây thư mục thực tế

```text
AutoTranslatorManager\
├── .github\
│   └── workflows\
│       ├── build.yml                 # [Active] GitHub Action để build app qua PyInstaller
│       └── build-release.yml         # [Active] GitHub Action để build release tag
├── atm\                              # Thư mục mã nguồn chính
│   ├── config\
│   │   ├── __init__.py
│   │   └── schema.py                 # [Active] Định nghĩa cấu trúc dữ liệu (Pydantic) cho GameProfile, Settings.
│   ├── container\
│   │   ├── __init__.py
│   │   └── bootstrap.py              # [Active] Khởi tạo các thư mục data ban đầu (data/profiles, data/payloads, data/logs).
│   ├── core\
│   │   ├── deployment\
│   │   │   ├── __init__.py
│   │   │   └── game_deployer.py      # [Active] Chịu trách nhiệm sao chép payload vào game, chạy game, và thu dọn (cleanup) khi game tắt.
│   │   ├── detectors\
│   │   │   ├── __init__.py
│   │   │   └── game_detector.py      # [Active] Phân tích file/thư mục game để nhận diện Engine (Unity, RPG Maker, Ren'Py, Unknown).
│   │   ├── events\
│   │   │   ├── __init__.py
│   │   │   └── event_bus.py          # [Active] Hệ thống Pub/Sub giao tiếp nội bộ giữa Deployer và API. (Instance-based Dependency Injection).
│   │   └── translation\
│   │       ├── __init__.py
│   │       ├── cache_manager.py      # [Active] Quản lý bộ nhớ đệm dịch thuật (In-memory + File IO).
│   │       ├── classification.py     # [Active] Hệ thống Schema định danh, phân loại text (TRANSLATABLE, PROTECTED) và chính sách ghi (WRITE_BACK, DISPLAY_ONLY).
│   │       ├── pipeline.py           # [Active] Trái tim của quá trình dịch offline (Extract -> Normalize -> API -> Cache).
│   │       ├── renpy_sdk_manager.py  # [Active] Tự động tải, check SHA256 và giải nén Ren'Py SDK chính hãng.
│   │       ├── renpy_tl_generator.py # [Active] Gọi Ren'Py SDK tạo template `tl/`, bóc tách tag và chèn bản dịch.
│   │       ├── renpy_translator.py   # [Active] Kịch bản điều phối dịch Ren'Py (dùng SDK -> Pipeline -> Template).
│   │       ├── rpgmaker_translator.py# [Active] Đọc/ghi JSON của RPG Maker, dùng recursive visitor để dịch và tạo ATM_Overlay.js.
│   │       ├── translation_memory.py # [Active] Tính năng bộ nhớ dịch (TM) với heuristic/fuzzy matching (thực thi nhưng có thể chưa public UI).
│   │       └── translators.py        # [Active] Wrapper gọi API Google/DeepL/Sugoi, chia lô (batching) và xử lý Rate Limit.
│   ├── storage\
│   │   ├── repositories\
│   │   │   ├── __init__.py
│   │   │   ├── profile_repository.py # [Active] Đọc/ghi file `.json` của từng GameProfile tại `data/profiles`.
│   │   │   └── settings_repository.py# [Active] Đọc/ghi cấu hình toàn hệ thống `settings.json`.
│   ├── ui\
│   │   ├── __init__.py
│   │   ├── api.py                    # [Active] Backend HTTP API cung cấp các endpoints cho Web Frontend.
│   │   ├── server.py                 # [Active] Bọc API bằng BaseHTTPRequestHandler của Python để tạo HTTP Server nhẹ.
│   │   └── web\
│   │       ├── index.html            # [Active] File giao diện trang chủ chính thức.
│   │       ├── script.js             # [Active] Logic client-side, gọi fetch API đến Backend, xử lý render UI.
│   │       └── style.css             # [Active] Chứa style/CSS giao diện (vibrant, dark mode, animations).
│   ├── utils\
│   │   ├── __init__.py
│   │   ├── file_system.py            # [Active] Các hàm helper để copy file an toàn, ignore error khi cleanup.
│   │   ├── logger.py                 # [Active] Hệ thống ghi log đa luồng ra Console và file.
│   │   └── network.py                # [Active] Các hàm tiện ích mạng (nếu có sử dụng tải payload).
│   └── main.py                       # [Active] Entry point 1: Chạy trực tiếp qua Python.
├── data\                             # [Runtime] Thư mục chứa dữ liệu người dùng (tự sinh ra).
│   ├── profiles\                     # Nơi chứa các file `<uuid>.json`.
│   ├── payloads\                     # Chứa BepInEx, patch files.
│   ├── sdk_cache\                    # Chứa RenPy SDK.
│   └── translation_cache.json        # Cache dịch lưu chung.
├── tests\                            # [Build-only] Chứa Unit test và Integration test của dự án.
├── pyproject.toml                    # [Active] Cấu hình dự án (dependencies, version, tools settings).
├── README.md                         # [Active] Tài liệu giới thiệu.
├── requirements.txt                  # [Active] Danh sách thư viện Python (requests, pydantic, pywebview).
└── run_app.py                        # [Active] Entry point 2: Dùng cho PyInstaller đóng gói thành exe.
```

## 3. Workflow tổng (Từ lúc mở đến lúc chơi)

### Kịch bản thêm và chạy game:

1. **Người dùng mở phần mềm**
   - File `run_app.py` / `main.py` chạy lên.
   - `bootstrap_app()` tạo các thư mục cấu trúc ở `data/` nếu chưa có.
   - Một HTTP Server nội bộ (`server.py`) lắng nghe ở một cổng ngẫu nhiên.
   - Trình duyệt mặc định tự động mở trang Web `http://127.0.0.1:<port>`.

2. **Bấm nút "Thêm Game" (Add Game)**
   - UI gọi API `/api/games` (POST).
   - Backend sử dụng `tkinter.filedialog.askopenfilename` để người dùng chọn file `.exe` (Windows) hoặc `.sh` (Linux).
   - `GameDetector.detect_engine()` quét thư mục game để tìm dấu hiệu (ví dụ có `GameAssembly.dll` -> Unity IL2CPP, có `www/data` -> RPG Maker MV).
   - Sinh một ID (UUID) mới, lưu thành file JSON trong `data/profiles/`.
   - UI cập nhật danh sách hiển thị tựa game mới với Engine tương ứng.

3. **Cấu hình Dịch thuật**
   - Người dùng bấm vào nút "Cấu hình" (hình bánh răng) của Game đó.
   - Bảng tuỳ chọn hiện ra, cho phép chọn `Language (From - To)` và `Dịch vụ dịch (Google, DeepL...)`.
   - UI gọi API update, `ProfileRepository` lưu lại.

4. **Bấm "Chạy Game" (Real-time - Unity)**
   - API gọi tới `GameDeployer.deploy_and_launch()`.
   - **Pre-launch:** Deployer vào thư mục `data/payloads/<Engine_Name>`, copy toàn bộ (thường là BepInEx, XUnity.AutoTranslator) vào thư mục game đích. Ghi file cờ `ATM_IS_RUNNING.txt`.
   - **Launch:** Gọi `subprocess.Popen` chạy file exe của game. Game khởi chạy và BepInEx tự động load plugin dịch realtime.
   - **Monitoring:** Một luồng (Thread) chạy ngầm để chờ tiến trình game tắt (`proc.wait()`). UI lúc này hiện trạng thái "Đang chạy".

5. **Tắt Game & Thu dọn (Cleanup)**
   - Người chơi thoát game.
   - Luồng Monitoring phát hiện tiến trình đã tắt. Trigger hàm `_on_game_exited()`.
   - Gọi `cleanup_items()`: Dựa vào danh sách các file đã copy ở bước 4, tiến hành xoá sạch các file đó khỏi thư mục game, chỉ giữ lại file save/log mà game tự sinh ra (không xoá file gốc). Trả lại thư mục game nguyên vẹn 100%.

6. **Dịch Game (Offline - RPG Maker / Ren'Py)**
   - Với Engine Offline, người dùng bấm nút "Dịch Game" thay vì "Chạy".
   - API gọi tới Translator tương ứng (VD: `RPGMakerTranslator`).
   - Hệ thống quét file game, bóc tách chữ, đưa qua `TranslationPipeline`, trả kết quả và tạo file Overlay/Patch.
   - Mất từ 2 - 10 phút. UI hiện Progress Bar. Dịch xong, trạng thái chuyển thành "Đã Dịch". Chạy game (chỉ cần chạy exe bình thường).

## 4. Chi tiết theo từng Engine

### 4.1 Unity (Mono / IL2CPP)
- **Phát hiện:** Có thư mục `*_Data`, có `MonoBleedingEdge` / `Managed` (Mono) hoặc `il2cpp_data` / `GameAssembly.dll` (IL2CPP).
- **Trích xuất & Dịch:** Không làm offline.
- **Cơ chế:** Real-time via BepInEx & XUnity.AutoTranslator. Dựa hoàn toàn vào bước "Chạy Game" (JIT Deployment).
- **Rủi ro:** Một số game có hệ thống Anti-Cheat sẽ không cho BepInEx chạy. Các game Unity render text bằng texture (không phải TextMeshPro/UGUI) sẽ không dịch được.

### 4.2 RPG Maker (MV / MZ)
- **Phát hiện:** Có thư mục `www/data` (MV) hoặc thư mục chứa các file `Map001.json`, `System.json` (MZ).
- **Trích xuất:** Quét toàn bộ thư mục chứa `.json` database. Dùng đệ quy (`recursive_visitor`) để vào từng Node của JSON.
- **Phân loại & Ghi kết quả:** Dựa vào `classification.py`:
  - `WRITE_BACK`: Text hiển thị như hội thoại (ví dụ: Event Code 401). Sẽ được dịch và ghi trực tiếp vào file JSON của game (dĩ nhiên file gốc được backup).
  - `DISPLAY_ONLY`: Text nhạy cảm như Tên nhân vật, Tên vũ khí (nếu ghi thẳng vào db, Script game gọi tên biến đó sẽ sập). Text này sẽ được dịch và ném vào một file Overlay (`translation_overlay.json`).
  - Ghi một Plugin `ATM_Overlay.js` vào thư mục plugins của game, inject vào `DataManager._databaseFiles` và chèn hook vào hàm `Window_Base.prototype.drawTextEx` để game tự tráo từ (replace) khi hiển thị lên màn hình.
- **Rủi ro:** Bản vá Javascript (Overlay) có thể xung đột nếu game xài UI mod quá nặng hoặc ghi đè toàn bộ class `Window_Base`.

### 4.3 Ren'Py
- **Phát hiện:** Có thư mục `game/`, file `renpy.exe` hoặc thư mục `renpy/`.
- **Trích xuất:** Tải SDK Ren'Py chuẩn mạng về, dùng tính năng `Translate` nguyên bản của Ren'Py (`renpy.sh <game> translate <lang>`) để ép engine tự bóc tách text tạo file `.rpy`.
- **Phân loại:** Các thẻ tag Ren'Py như `[player_name]`, `{color=#f00}` được nhận diện qua Regex và đánh dấu là PROTECTED token (ví dụ: `<ATM_TK_0>`) để Google Translate không dịch sai lệch cú pháp.
- **Ghi kết quả:** Dịch xong, fill các đoạn dịch vào thẻ `new` trong file `.rpy`. Game khởi động sẽ tự ưu tiên file này.
- **Rủi ro:** Cần tải SDK rất nặng nếu chưa có cache. Tính tương thích với các game Ren'Py mod source code sâu có thể gặp sự cố.

## 5. Pipeline dịch thuật (Translation Pipeline)

Với các cơ chế dịch Offline (RPG Maker, Ren'Py), logic cốt lõi chạy qua `TranslationPipeline` (trong `pipeline.py`).
1. **Receive:** Nhận 1 lô text.
2. **Normalize:** Dọn rác, trim khoảng trắng. Bỏ qua các chuỗi chỉ có số hoặc dấu chấm lửng (`...`).
3. **Glossary/Token Protect:** (IMPLEMENTED BUT UNDOCUMENTED IN UI) Bọc các từ khóa thuật ngữ, tag hệ thống thành token ẩn (VD: `_ATM1_`).
4. **Cache Lookup:** Tra cứu trong `TranslationCache`. Nếu đã có, lấy ra luôn.
5. **API Batched Request:** Các chuỗi chưa có trong cache được gom thành 1 mảng. Gọi `BaseTranslator` (Google, DeepL...). API dịch toàn bộ.
6. **Token Restore:** Dịch xong, tráo ngược `_ATM1_` thành từ khoá / tag ban đầu.
7. **Round-trip Validate:** Kiểm tra an toàn: Có bị mất dấu ngoặc ngọn `< >` không? Nếu mất (API dịch hỏng syntax), loại bỏ bản dịch, giữ nguyên chữ gốc.
8. **Cache Save:** Lưu các bản dịch thành công vào JSON cache.

## 6. Hệ thống lưu trữ bản dịch (Cache)

- **TranslationCache (`data/translation_cache.json`)**: Dùng làm kho lưu trữ toàn cục cho các bản dịch. Tăng tốc độ nếu dịch lại game hoặc dịch game mới có câu giống game cũ. Cấu trúc JSON key-value.
- **Translation Memory (User TM)**: Có code logic trong `translation_memory.py` hỗ trợ Fuzzy matching và Persist confirmed entries. (IMPLEMENTED IN CORE, BUT UNDOCUMENTED/NO UI).
- **Thứ tự tra cứu**: Exact Memory Cache -> API Translation -> Cache Save.

## 7. UI/UX (Màn hình & Tính năng)

Toàn bộ giao diện là một trang Single Page Application (Web HTML/JS/CSS).

### Màn hình chính (Dashboard)
- **Tiêu đề:** Tên ứng dụng "Auto Translator Manager" lớn.
- **Nút "Thêm Game Mới" (Add New Game):** 
  - Mở Dialog chọn file `.exe`.
  - Kết quả: Thẻ game mới (Card) hiện ra trong danh sách. Nếu bạn bấm Cancel ở Dialog, không có gì xảy ra.
- **Danh sách Game (Games Grid):** Hiển thị các ô thẻ trò chơi.

### Thẻ Game (Game Card)
Mỗi thẻ game có các thành phần sau:
- **Tên Game:** Click vào để đổi tên.
- **Badge Engine:** Hiển thị (Unity IL2CPP, RPG Maker, ...).
- **Nút Hành Động Chính:**
  - **Dành cho Real-time (Unity):** Có nút **"Play (Translate)"**. Khi bấm -> gọi GameDeployer. Nút chuyển sang "Stop" màu đỏ. Nếu bấm Stop -> Buộc tắt game và dọn dẹp.
  - **Dành cho Offline (RPG/Ren'Py):** Có nút **"Translate"**. Khi bấm -> Bắt đầu chạy pipeline dịch. Hiển thị Progress Bar. Dịch xong, nút biến thành "Play" (Chạy game bình thường, không deploy realtime payload).
- **Nút Options (Bánh răng):** Click để mở Modal Cấu hình của riêng game đó.
- **Nút Xóa (Thùng rác):** Xoá GameProfile. Xoá thẻ khỏi danh sách. Không xoá dữ liệu ổ cứng của game.

### Cửa sổ Modal Cấu Hình Game (Settings Modal)
- **Tên game:** Ô input text sửa tên hiển thị.
- **Target Language (Output):** Dropdown chọn ngôn ngữ đích (Ví dụ: Vietnamese `vi`, English `en`). Mặc định là `vi`.
- **Source Language (Input):** Dropdown chọn ngôn ngữ nguồn (Thường để Auto Detect, hoặc `ja`, `zh`).
- **Dịch vụ dịch (Translator):** Dropdown chọn (Google Translate, DeepL API, Sugoi Offline...). Mặc định là `Google`.
- Nút **"Lưu thay đổi"**: Cập nhật vào profile `data/profiles/<id>.json`.

### Cửa sổ Modal Lịch Sử/Log (Status Toast/Log Panel)
- Góc dưới màn hình có hệ thống Toast notification, hiển thị các thông báo như "Đang dịch...", "Lỗi không tìm thấy thư mục", "Khởi chạy thành công".

## 8. Xử lý lỗi & Giới hạn

- **Lỗi thiếu Payload:** Nếu bấm Play game Unity mà thư mục `data/payloads/Unity IL2CPP` bị thiếu, hệ thống bắn ra lỗi "Payload not found" lên UI và từ chối chạy. Không gây crash hệ thống.
- **Lỗi dịch API chặn IP:** (Rate limit) Code Translator có logic tự delay `sleep` khi Google chặn (429), nhưng nếu block cứng, tiến trình sẽ báo lỗi.
- **Lỗi Ren'Py SDK:** Nếu tự tải SDK bị đứt mạng hoặc Hash SHA256 sai (file hỏng), hệ thống sẽ xoá file zip lỗi, retry 3 lần, nếu vẫn tạch sẽ báo lỗi ngừng lại (Không cho phép dùng SDK dỏm).
- **Giới hạn - Crash do Cleanup:** Đôi khi tiến trình game (đặc biệt là launcher Unity) tách ra làm nhiều tiến trình con. Nếu launcher chết sớm hơn con, ATM sẽ lầm tưởng game tắt và tiến hành dọn rác (cleanup) ngay lúc game đang chạy, gây crash game. (Fix qua ProcessMonitor nâng cao).
- **File kích thước lớn:** Database RPG Maker quá to có thể gây tràn RAM trong pipeline lúc Parse.

## 9. Trạng thái & Roadmap

- **IMPLEMENTED (Hoàn thiện):** 
  - Vòng đời Deployer (Deploy -> Launch -> Cleanup).
  - Pipeline Offline cực xịn với Classification schema, Overlay RPG Maker.
  - Tự tải Ren'Py SDK.
  - API Backend hoàn thiện bằng Flask/Werkzeug (server nhẹ).
- **PLANNED / IN-PROGRESS (Sắp làm):** 
  - Giao diện Glossary/Translation Memory (Backend đã code xong core, UI chưa gọi đến).
  - Tích hợp thêm Sugoi / Mtool APIs (đã có base class, cần implement provider).
- **NOT IMPLEMENTED:** 
  - Không hỗ trợ game Unreal Engine (chưa có detector, chưa có payload).
  - Không có auto-update phần mềm ATM.

## 10. Báo cáo tổng kết

- **Số file đã quét & Dump:** 24 file (Python, JS, HTML, CSS, Config) nằm trong source.
- **Engine thực sự hỗ trợ (Code):** 4 loại (Unity IL2CPP, Unity Mono, RPG Maker MV/MZ, Ren'Py).
- **Số lượng file Binary/Data lớn bị lược bỏ code:** Các file `.json` cache quá dài (như `translation_cache.json`) và thư mục `data/` không được dump nội dung để giữ sạch tài liệu.
- **Đánh giá tổng thể:** Kiến trúc V11 hiện tại tuân thủ nghiêm ngặt chuẩn Dependency Injection và Single Responsibility. Cơ chế an toàn (WRITE_BACK vs DISPLAY_ONLY) giải quyết được tử huyệt hỏng game của mọi công cụ AutoTranslator khác.

---
*(Tài liệu này được xuất tự động dựa trên Source Code thực tế - v11)*
