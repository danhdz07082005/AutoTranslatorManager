import os
from pathlib import Path

out_file = Path("D:/game/l/gvnvh/gvngv2/4/5_system_flow.md")

content = """# BÍ KÍP VÕ CÔNG: AUTO TRANSLATOR MANAGER (Phiên bản Tối thượng)

Tài liệu này mô tả chi tiết đến từng ngóc ngách hệ thống, từ các API, luồng dịch của từng Engine, cho đến các "cơ chế cứu thương" (fallback & recovery) để đảm bảo hệ thống bất tử trước mọi lỗi lầm.

---

## 1. TỔNG QUAN KIẾN TRÚC
- **Frontend (Giao diện):** Sử dụng thuần HTML/JS/CSS (Vanilla JS + Bootstrap). Giao tiếp với Backend qua HTTP Fetch API (AJAX). Hoàn toàn không dùng framework nặng.
- **Backend Server:** Viết bằng Python nguyên bản, sử dụng `http.server`. Chứa một Custom Router để điều hướng các URL Requests vào Class `BackendApi`.
- **Core Processing:** 
  - `JobManager`: Hàng đợi xử lý đa luồng (Thread pool) cho các tác vụ nặng (như dịch API hàng ngàn dòng JSON offline).
  - `ProcessMonitor`: Giám sát cây tiến trình (Process Tree) của Game để biết khi nào Game tắt/sập.
  - `GameDeployer`: Bác sĩ phẫu thuật - tiêm mã độc (payload) vào Game để dịch real-time và dọn dẹp sau khi mổ.
- **Database:** JSON tĩnh lưu ở thư mục `/data/` (`games.json`, `config.json`, `translation_cache.json`).

---

## 2. LUỒNG KHỞI ĐỘNG (STARTUP FLOW)
1. User chạy `start.bat`. Python kích hoạt `main.py`.
2. `bootstrap_app()` khởi tạo các thư mục thiết yếu (`data/`, `logs/`, `data/translations/synced_logs/`).
3. Khởi tạo `BackendApi` và `JobManager` (quét tìm các Job bị treo ở lần chạy trước để khôi phục - **cơ chế cứu thương 1**).
4. Khởi tạo Socket để xin hệ điều hành một **Port ngẫu nhiên an toàn**, chống xung đột với các app khác. Set biến môi trường `ATM_SERVER_PORT`.
5. Bật HTTP Server chạy ngầm dưới background (Daemon Thread).
6. Gọi lệnh mở trình duyệt mặc định: `http://127.0.0.1:<port>`.
7. **Màn hình Hello (Splash Screen):** UI tải lên `index.html`, một lớp phủ CSS Animation hiện chữ chào mừng. Bộ đếm `setTimeout(..., 3000)` đếm ngược đúng 3 giây thì Fade Out và gỡ lớp phủ.
8. Frontend bắn API `GET /api/games` và `GET /api/settings` để lấy dữ liệu render danh sách các game.

---

## 3. CÁC API & ENDPOINTS CHI TIẾT

### 3.1. Hệ thống & Settings
- **`GET /api/languages`**: Lấy danh sách ngôn ngữ hỗ trợ (ja, vi, en, zh-TW, zh-CN...).
- **`GET /api/settings`**: Trả về nội dung `config.json`.
- **`POST /api/settings/update`**: Cập nhật settings. Body: `{"deepl_api_key": "...", "log_level": "INFO"}`.

### 3.2. Quản lý Game
- **`GET /api/games`**: Lấy danh sách game.
- **`POST /api/games/add`**: Kích hoạt hàm `tkinter.filedialog` dưới Backend để mở cửa sổ chọn file `.exe`. Nhận diện Engine qua `GameDetector` (Quét cấu trúc thư mục _Data, www, renpy...). Trả về thông tự Game Profile.
- **`POST /api/games/<game_id>/update`**: Lưu settings riêng cho từng game. Body: `{"input_lang": "auto", "output_lang": "vi", "translator": "google"}`.
- **`DELETE /api/games/<game_id>`**: Xoá game khỏi database.

### 3.3. Start, Stop, Play (Real-time Translation)
- **`POST /api/games/<game_id>/start`**: Chơi game và kích hoạt dịch tự động (Tiêm Payload).
- **`POST /api/games/<game_id>/play`**: Chơi game Vanilla (không tiêm Payload).
- **`POST /api/games/<game_id>/stop`**: Buộc dừng tiến trình Game. Kích hoạt dọn dẹp Payload.
- **`GET /api/games/<game_id>/status`**: Polling trạng thái. Return: `{"status": "running/idle/stopped", "log": ["..."]}`.

### 3.4. Offline Extract/Translate (RPGMaker / Hệ JSON)
- **`GET /api/games/<game_id>/coverage`**: Trả về thống kê tiến độ dịch (Tổng số file, số ký tự text, lượng đã dịch, %).
- **`POST /api/games/<game_id>/extract`**: Tạo Job bóc tách Text JSON. Return: `{"job_id": "<uuid>"}`.
- **`POST /api/games/<game_id>/patch`**: Tạo Job dịch Text qua API Google/DeepL rồi nén ngược vào Game. Return: `{"job_id": "<uuid>"}`.
- **`GET /api/jobs/<job_id>`**: Polling tiến độ Job. Return: `{"status": "Running", "current": 10, "total": 100, "log": "..."}`.
- **`POST /api/jobs/<job_id>/cancel`**: Hủy Job bằng CancellationToken.

### 3.5. Thuật ngữ & Translation Memory
- **`GET /api/data/cache`**: Query: `?q=&page=&limit=`. Phân trang lấy text.
- **`POST /api/data/cache/update`**: Chỉnh sửa bản dịch. Body: `{"game_id", "key", "value"}`.
- **`GET /api/data/stats`**: Thống kê số lượng bản dịch.
- **`POST /api/data/glossary/import/preview`**: Đọc file CSV/JSON/TXT gửi lên từ Base64 để cho người dùng xem trước.
- **`POST /api/data/glossary/import/apply`**: Chấp nhận Preview và hợp nhất (merge) vào Từ điển Thuật ngữ.

---

## 4. CHI TIẾT CÁC LUỒNG DỊCH THEO ENGINE (UNITY, RENPY, RPG MAKER)

### 4.1. Luồng Game Unity (XUnity AutoTranslator)
**Cơ chế tiêm Payload & Hoạt động:**
1. Khởi động Game qua `GameDeployer`.
2. ATM copy toàn bộ `resources/payloads/bepinex_mono` (hoặc `il2cpp`) vào thư mục gốc của Game.
3. Sinh file `AutoTranslatorConfig.ini` với thuật toán cấu hình **chuẩn mực (Inspire từ DichTrucTiep)**:
   - Sử dụng cổng RPC `Endpoint=GoogleTranslate` cực kỳ ổn định.
   - Set cứng `FromLanguage=auto` để tắt bộ lọc tiếng Nhật của XUnity, bắt và dịch được cả tiếng Anh, tiếng Trung.
   - Ghi block `[TextFrameworks]` bật TẤT CẢ các hook: `EnableUGUI`, `EnableIMGUI`, `EnableNGUI`, `EnableFairyGUI`... (Chống lại căn bệnh "Mù chữ" cho các UI lạ).
   - Bật `EnableBatching=True` kết hợp `IgnoreWhitespaceInDialogue=True` và `MinDialogueChars=20`. Điều này giúp hệ thống bỏ qua những ký tự lẻ tẻ rác UI, gom các câu hội thoại dài lại đẩy lên API Google cùng lúc => **Tốc độ dịch trả về dưới 3 giây, cực vip.**
4. BepInEx khởi động cùng game, hook vào bộ nhớ render chữ (`SetCharArray`), chặn text, ném lên Google, nhận kết quả và chèn đè lại lên màn hình.

### 4.2. Luồng Game RenPy (Python Script Injection)
**Cơ chế tiêm Payload & Hoạt động:**
1. Khởi động Game qua `GameDeployer`.
2. ATM phát hiện game RenPy, tiến hành copy các file mã nguồn Python script `transconfig.rpy` và `realtimetrans.rpy` vào thư mục `game/` của trò chơi.
3. Vì RenPy biên dịch `.rpy` thành `.rpyc` lúc runtime, hệ thống ATM chủ động xoá các file rác `.rpyc` cũ trước khi tiêm bản mới vào.
4. Khi chạy, script `realtimetrans.rpy` sẽ hook trực tiếp vào cơ chế Screen và Character Say của RenPy, lấy chuỗi text, gửi qua Python request lên Google, và trả lại màn hình.

### 4.3. Luồng Game RPG Maker MV/MZ (Offline Parsing)
**Cơ chế Bóc tách (Extract) & Dịch (Patch):**
1. RPG Maker lưu thoại dưới dạng hàng trăm file `.json` (Map001.json, CommonEvents.json...).
2. Dịch Real-time sẽ làm lag game vì trình duyệt (NW.js) phải liên tục render DOM. Do đó, ATM dùng luồng **Offline Pipeline**.
3. **Extract:** Quét toàn bộ thư mục `www/data`, dùng regex/key-mapping bóc các chuỗi Text sự kiện ra một file trung gian `TranslationCache`.
4. **Patch:** Đẩy các chuỗi Text này lên API `TranslatorManager`. Hỗ trợ xử lý đa luồng Concurrency, gọi API DeepL/Google Batching. Dịch xong, tiêm lại giá trị mới đè lên các file JSON gốc. Khởi động lại game là 100% tiếng Việt. (Hiện tại Extractor và Injector đang là Mock/Dummy chuẩn bị cho Phase 2 hoàn thiện).

---

## 5. HỆ THỐNG CÁC "CƠ CHẾ CỨU THƯƠNG" (FALLBACKS & RECOVERY)
Đây là phần cốt lõi giúp ATM trở nên "bất tử", phục hồi hệ thống khi có bất kỳ sai sót nào:

**1. Cứu thương API Bị Ban (IP Rate Limit Fallback):**
- **Vấn đề:** Google Translate (cổng GTX `GoogleTranslateV2`) thỉnh thoảng block IP nếu gửi quá nhiều request ngắn trong 1 giây (như hiệu ứng gõ phím).
- **Cơ chế ATM:** ATM sinh ra cấu hình có `FallbackEndpoint=GoogleTranslate` (cổng chính) và `FallbackEndpoint=GoogleTranslateV2` (dự phòng). Khi một cổng bị ban, XUnity AutoTranslator tự động đảo qua cổng dự phòng để không gián đoạn game. Tránh trường hợp IP bị block là chết đứng.

**2. Cứu thương UI Game Crash (Font Fallback Removal):**
- **Vấn đề:** Game Unity xài TextMeshPro nếu bị ép xài font Arial qua cấu hình `FallbackFontTextMeshPro=arial` mà game đó chưa nướng (baked) sẵn file font Arial dạng asset, UI game sẽ bị crash, đỏ màn hình.
- **Cơ chế ATM:** Đã loại bỏ việc ép font cho TextMeshPro, để hệ thống tự tìm font của game hoặc sử dụng bộ Fallback mặc định của Engine. (Chỉ override font thường bằng Arial).

**3. Cứu thương Sập Game & Giữ Data (Data Sync Fallback):**
- **Vấn đề:** Game bị Crash đột ngột, văng ra desktop. Hoặc User bấm Alt+F4.
- **Cơ chế ATM:** Module `ProcessMonitor` liên tục bám theo cây tiến trình. Kể cả văng game đột ngột, Callback `_on_game_exited` vẫn được gọi.
  - ATM sẽ tự động dọn sạch rác BepInEx ra khỏi game (để chống lỗi vặt cho lần mở sau).
  - **Quan trọng:** ATM vẫn nhanh tay chép trộm (Backup) file `LogOutput.log` và file lịch sử dịch `_AutoGeneratedTranslations.txt` lưu về thư mục `data/translations/synced_logs/` rồi merge vào CSDL. Mất game nhưng KHÔNG mất dữ liệu!

**4. Cứu thương Mất Điện (Job Queue Recovery):**
- **Vấn đề:** Đang dịch RPG Maker offline (chạy Job Patch 100,000 dòng text), bỗng dưng mất điện hoặc lỡ tắt Console (cửa sổ đen).
- **Cơ chế ATM:** Bất kỳ Job nào đang chạy đều lưu trạng thái `PENDING` xuống `data/jobs.json`. Khi bật ứng dụng lại, hàm `_recover_jobs()` của `BackendApi` quét database và tự động load lại tiến trình đang dở dang, đánh dấu `FAILED` hoặc chạy tiếp.

**5. Cứu thương Tình Trạng "Mù Chữ" Đa Ngôn Ngữ:**
- **Vấn đề:** Các bản dịch cũ thường ngáo ngơ nếu game có giao diện Tiếng Anh nhưng user để Language = Auto. (Do bộ lọc XUnity tự khóa).
- **Cơ chế ATM:** Sửa đổi logic Hardcode ép `auto` thành `auto` (chứ không ép về `ja`), đánh bật mọi chướng ngại vật về Text Framework (bật IMGUI, NGUI...). Game nào cũng bắt chữ và dịch được, bất chấp Engine viết bằng bộ công cụ UI cổ xưa hay hiện đại.
"""

with open(out_file, "w", encoding="utf-8") as f:
    f.write(content)
print("Done!")
