# PROMPT: Nâng cấp AutoTranslatorManager (ATM) — Fix sót text, vỡ cú pháp & vỡ logic game

## Bối cảnh dự án

Dự án AutoTranslatorManager (ATM) là phần mềm dịch game tự động, kiến trúc Modular Monolith với 4 layer: Presentation (FastAPI), Business Logic (Core), Data Access (Storage/Repository), Infrastructure (rpatool, unrpyc, Google/DeepL API).

Cấu trúc thư mục hiện tại:
```
atm/
├── core/
│   ├── detectors/            # GameDetector.py
│   ├── deployment/           # GameDeployer.py (Unity DLL Injection)
│   └── translation/
│       ├── cache_manager.py       # Quản lý cache dịch (key-value hiện tại)
│       ├── renpy_translator.py    # Regex-based extraction cho RenPy
│       ├── rpgmaker_translator.py # Chỉ quét Event Code 401/102
│       ├── translators.py         # Client gọi Google Translate API
│       └── unren_tools/
├── ui/ (api.py, server.py, web/)
├── storage/ (profile_repository.py, settings_repository.py)
├── utils/
└── config/ (Pydantic Schemas)
```

**Ba lớp vấn đề đang gặp (theo mức độ nghiêm trọng):**
1. **Sót text:** `rpgmaker_translator.py` chỉ duyệt Event Command Code `401`/`102` → bỏ sót toàn bộ text trong `Actors.json`, `Weapons.json`, `Skills.json`...
2. **Vỡ cú pháp:** `renpy_translator.py` dùng Regex + placeholder tự chế → vỡ với pattern phức tạp (`_("...")`, `{i}...{/i}`, interpolation `[var]`, conditional expression).
3. **Vỡ logic game (lớp nguy hiểm nhất, dễ bị bỏ qua nhất):** một số string vừa là text hiển thị, vừa là identifier/key mà code dùng để tra cứu hoặc so sánh (ví dụ `item.name === "Potion"` trong Script Call). Whitelist theo **tên field** (`key == "name"`) KHÔNG đủ để phân biệt việc này — vì cùng field `name` trong `Actors.json` là display text, nhưng trong `PluginConfig.json` hay `Manifest.json` lại có thể là identifier/metadata. Phải phân loại theo **schema + context của cả file**, không phải theo tên key đơn lẻ.

**Điểm mạnh cần giữ nguyên và nâng cấp thành lợi thế cạnh tranh cốt lõi:**
- Cache dịch (tăng tốc, tránh gọi lại API).
- User Glossary (ép buộc thuật ngữ, ví dụ "Holy Sword" → "Thánh Kiếm" cố định).
- User-editable, tái sử dụng qua nhiều game.
- **Sẽ nâng cấp thành 3 tầng lưu trữ riêng biệt** — xem Phase 5.

---

## Mục tiêu tổng thể

Refactor theo đúng thứ tự ưu tiên dưới đây. **Không làm nhảy cóc** — mỗi phase phải chạy được, có test, rồi mới sang phase tiếp theo. Phase 0 là nền tảng bắt buộc — mọi phase sau đều phụ thuộc vào nó.

---

## PHASE 0 — Semantic Safety & Protected Data Model (nền tảng bắt buộc, làm trước tiên)

**Mục tiêu:** Không bao giờ dịch một string mà việc thay đổi nó có khả năng phá vỡ logic game. Nguyên tắc cốt lõi: **"Không dịch vì nó là string. Chỉ dịch khi schema xác nhận string đó là display text."**

**File mới:** `atm/core/translation/classification.py`

**Yêu cầu:**

1. Định nghĩa enum phân loại cho MỌI string tìm được (áp dụng chung cho cả RPG Maker và Ren'Py):
   ```python
   class StringClassification(Enum):
       TRANSLATABLE = "translatable"  # dialogue, display name, description, UI label
       PROTECTED = "protected"        # JSON key, identifier, variable name, file path,
                                        # asset name, plugin parameter, internal ID,
                                        # script/code, lookup key, enum value, command token
       SPECIAL = "special"            # note field, formula, mixed code+prose — cần parser riêng
       UNKNOWN = "unknown"            # không xác định được — TUYỆT ĐỐI không tự động dịch
   ```

2. Định nghĩa cấu trúc dữ liệu chuẩn cho mỗi entry đi qua toàn bộ pipeline:
   ```python
   class TranslationEntry:
       original_text: str
       translated_text: str | None
       source_file: str
       path: str                       # ví dụ "Weapons.3.name"
       category: str                   # dialogue / item / skill / ui / actor_name / system
       classification: StringClassification
       placeholders: list[str]         # token đã tách ra, xem Phase 2 mục bổ sung
       validation_status: str          # pending / passed / rejected
   ```

3. **Phân loại phải dựa trên schema của TỪNG LOẠI FILE, không phải tên key đơn lẻ.** Xây dựng 1 bảng schema tường minh cho từng file RPG Maker, ví dụ:
   ```
   Actors.json / Classes.json / Enemies.json / Weapons.json / Armors.json / Items.json / Skills.json / States.json:
       name        → TRANSLATABLE
       description → TRANSLATABLE
       nickname    → TRANSLATABLE
       profile     → TRANSLATABLE
       message1-4  → TRANSLATABLE
       note        → SPECIAL (xem Phase 1 mục note)
       id, iconIndex, animationId, traits, effects, params  → PROTECTED

   System.json:
       gameTitle, terms.* (một số)  → TRANSLATABLE (cần review thủ công danh sách terms)
       các field cấu hình khác      → PROTECTED

   PluginConfig / bất kỳ file cấu hình plugin nào:
       mọi field "name"             → mặc định PROTECTED trừ khi có whitelist plugin cụ thể xác nhận đó là text hiển thị
   ```
   Đây chính là lý do `is_translatable(node, path)` ở bản cũ chưa đủ — hàm này cần đổi chữ ký thành `classify(node, path, source_file, file_schema)`, nhận thêm context loại file để tra đúng bảng schema, không quyết định chỉ dựa vào tên key.

4. Bất kỳ string nào không match được vào bảng schema đã định nghĩa → gán `UNKNOWN`, đưa vào danh sách **cần user xác nhận thủ công trong UI** trước khi dịch, không tự động xử lý.

**Acceptance criteria:** Chạy classification trên 1 game RPG Maker thật, xuất ra báo cáo số lượng string theo từng nhóm (TRANSLATABLE/PROTECTED/SPECIAL/UNKNOWN); review thủ công để xác nhận không có case PROTECTED nào lọt vào nhóm TRANSLATABLE.

---

## PHASE 1 — Recursive JSON Visitor cho RPG Maker (dùng Classification từ Phase 0)

**File cần sửa:** `atm/core/translation/rpgmaker_translator.py`

**Yêu cầu:**

1. Thay thế logic quét cứng theo `Code == 401 or Code == 102` bằng visitor đệ quy tổng quát, duyệt toàn bộ cấu trúc JSON bất kể độ sâu, gọi `classify()` (Phase 0) tại mỗi string tìm được thay vì tự quyết định translatable hay không:
   ```python
   def visit(node, path, source_file, schema):
       if isinstance(node, str):
           classification = classify(node, path, source_file, schema)
           if classification == StringClassification.TRANSLATABLE:
               yield TranslationEntry(original_text=node, path=path, source_file=source_file, classification=classification, ...)
           elif classification == StringClassification.SPECIAL:
               yield from handle_special_field(node, path, source_file)
           # PROTECTED và UNKNOWN không yield vào danh sách dịch tự động
       elif isinstance(node, list):
           for i, item in enumerate(node):
               yield from visit(item, path + [i], source_file, schema)
       elif isinstance(node, dict):
           for key, value in node.items():
               yield from visit(value, path + [key], source_file, schema)
   ```

2. Áp dụng lên **toàn bộ file trong thư mục `data/`**: `Actors.json`, `Classes.json`, `Enemies.json`, `Items.json`, `Weapons.json`, `Armors.json`, `Skills.json`, `States.json`, `System.json`, `Troops.json`, `MapInfos.json`, cộng với `MapXXX.json`/`CommonEvents.json` như cũ.

3. Với Code `102` (Show Choices), dịch cả mảng `choices` bên trong parameters, không chỉ câu hỏi chính.

4. **Field `note` xử lý như SPECIAL_FIELD, không chỉ "loại trừ":**
   - Viết parser riêng `parse_note_field(text)` tách phần văn xuôi (prose) ra khỏi tag cấu hình `<Tag:...>` và code công thức (`a.atk * 2`).
   - Ví dụ input:
     ```
     <SkillCost:100>
     Damage Formula:
     a.atk * 2
     ```
     Chỉ dòng `Damage Formula:` (nếu đó là label hiển thị) mới được coi là TRANSLATABLE; `<SkillCost:100>` và `a.atk * 2` luôn PROTECTED.
   - Sau khi dịch phần prose, ghép lại đúng vị trí, giữ nguyên 100% các dòng tag/code.

5. **KHÔNG ghi bản dịch đè lên `path` gốc trong file data.** Lưu vào overlay riêng `translation_overlay.json`, key = `path` chuẩn hóa (ví dụ `"Weapons.3.name"`). Viết RPG Maker Plugin (`ATM_Overlay.js`) hook vào tầng vẽ UI (`Window_Base.drawText`, `drawItemName`...) để tráo text hiển thị theo `path`, còn `$dataWeapons[3].name` trong bộ nhớ **giữ nguyên tiếng Anh vĩnh viễn** — nhờ vậy mọi logic Script Call/Conditional Branch so sánh theo tên vẫn hoạt động đúng.

6. Viết unit test cho visitor + classification: input JSON mẫu lồng nhau nhiều cấp, verify đúng phân loại theo từng loại file, verify note field tách đúng prose/code.

**Acceptance criteria:**
- Tên vũ khí/trang bị/skill xuất hiện trong danh sách dịch — điều bản cũ không làm được.
- Test bắt buộc: tạo 1 test project RPG Maker nhỏ có `Conditional Branch → Script: $gameParty.hasItem($dataItems.find(i => i.name === "Potion"))`, xác nhận sau khi dịch xong logic này **vẫn hoạt động đúng** vì giá trị `name` trong bộ nhớ không đổi.

---

## PHASE 2 — Ren'Py: chuyển từ Regex sang cơ chế Translation gốc của engine + Placeholder Protection

**File cần sửa:** `atm/core/translation/renpy_translator.py` (viết lại phần lớn workflow)

**Yêu cầu:**

1. **Không tự viết AST parser từ đầu.** Dùng chính Ren'Py SDK để sinh khung dịch tự động:
   ```
   renpy.sh <project_path> translate <language>
   ```
   Lệnh này parse AST toàn bộ script, sinh file `game/tl/<language>/*.rpy` dạng:
   ```
   translate vietnamese label_hash:
       old "Hello [player_name]"
       new "Hello [player_name]"
   ```

2. Viết module `renpy_tl_generator.py`: gọi Ren'Py SDK sinh file `tl/<lang>/`, parse các cặp `old`/`new` — đây là danh sách cần dịch, đã đảm bảo đúng cú pháp bao quanh nhờ AST.

3. **Bổ sung quan trọng — Placeholder Protection cho NỘI DUNG bên trong mỗi câu `old`:** dù AST đã đảm bảo cấu trúc code xung quanh không vỡ, bản thân chuỗi text gửi cho Google/DeepL API vẫn có thể bị dịch sai vị trí hoặc "sáng tạo" với các token bên trong câu (`[player_name]`, `{i}...{/i}`). Do đó trước khi gửi API, cần một bước tách token độc lập:
   ```
   Input:  "Hello [player_name], {i}welcome{/i}"
   Bước 1 (Protect): "Hello <<VAR_0>>, <<TAG_1>>welcome<<TAG_2>>"
   Bước 2: gửi cho API dịch — API chỉ thấy placeholder, không có cơ hội chỉnh sửa token
   Bước 3 (Restore): map <<VAR_0>> → [player_name], <<TAG_1>>/<<TAG_2>> → {i}/{/i}
   Kết quả: "Xin chào [player_name], {i}chào mừng{/i}"
   ```
   Đây là lớp bảo vệ bổ sung, độc lập với việc dùng AST hay regex — AST giải quyết vỡ cú pháp Ren'Py, Placeholder Protection giải quyết vỡ token bên trong câu dịch.

4. Sau khi có bản dịch (đã restore token), gửi qua **pipeline chung** (Phase 3) để Classify/Validate/Round-trip trước khi ghi vào `new "..."`.

5. **Không đụng vào file `.rpy` gốc** — toàn bộ bản dịch nằm trong `game/tl/<language>/`.

**Acceptance criteria:** Test với 1 game RenPy thật có `{i}`, `[player_name]`, dialogue lồng script call — sau dịch, game chạy được, tag/interpolation giữ nguyên đúng vị trí dù đã bị gửi qua API dịch.

**Rủi ro còn lại cần QA thủ công:** cơ chế `translate` gốc chỉ quét string được nhận diện là dialogue/menu/screen-text, nên code Python logic (`if class_name == "Warrior":`) thường nằm ngoài phạm vi quét — rủi ro thấp hơn RPG Maker, nhưng vẫn cần chạy thử 1 lượt game thật để chắc chắn không có literal string nào vừa hiển thị vừa dùng làm định danh logic bị quét nhầm.

---

## PHASE 3 — Pipeline chung: Transaction, Round-trip Validation, Atomic Write

**File mới:** `atm/core/translation/pipeline.py`

**Yêu cầu:**

Pipeline đầy đủ theo đúng thứ tự (thay thế hoàn toàn cách làm "dịch xong ghi đè luôn"):

```
Extract
  ↓
Classify (Phase 0)
  ↓
Protect (tách placeholder/token — Phase 2 mục 3, áp dụng cả 2 engine)
  ↓
Normalize (trim, chuẩn hóa Unicode NFC)
  ↓
Deduplicate
  ↓
Cache / Glossary lookup (Phase 5)
  ↓
Translate (gọi API cho phần chưa có trong cache)
  ↓
Restore Protected Tokens
  ↓
Validate (placeholder count khớp, không rỗng/None/chỉ dấu "...")
  ↓
Write temporary output (KHÔNG ghi vào file thật)
  ↓
Round-trip Validate (xem chi tiết bên dưới)
  ↓
PASS → Atomic Replace   |   FAIL → rollback, giữ nguyên bản gốc, log rõ lý do
```

**Round-trip Validation — bắt buộc, không phải tùy chọn:**

- **RPG Maker:** sau khi sinh `translation_overlay.json` (hoặc file data nếu có phần bắt buộc ghi trực tiếp như dialogue Event):
  1. Parse lại bằng JSON parser thật (không chỉ kiểm tra bằng mắt).
  2. Validate đúng schema đã định nghĩa ở Phase 0.
  3. Kiểm tra toàn bộ ID không bị đổi.
  4. Kiểm tra số lượng object trong mỗi file không đổi so với bản gốc.
  5. Kiểm tra mọi field đã đánh dấu PROTECTED ở Phase 0 **có giá trị y hệt bản gốc** (nếu khác → FAIL ngay, đây là chỉ dấu classification hoặc write-back có bug).
  6. Chỉ khi cả 5 bước trên PASS mới cho phép Atomic Replace.

- **Ren'Py:** sau khi sinh `game/tl/vietnamese/`:
  1. Gọi chính Ren'Py SDK compile lại project (`renpy.sh <project> lint` hoặc tương đương) để xác nhận không lỗi cú pháp.
  2. Nếu compile/lint fail → rollback toàn bộ, không ghi.
  3. Chỉ khi compile PASS mới coi bản dịch hợp lệ.

**Atomic Replace:** ghi file mới ra path tạm (`.tmp`), chỉ sau khi mọi bước validate PASS mới `os.replace()` đè lên file thật (atomic ở cấp OS) — tránh trường hợp crash giữa chừng để lại file half-written.

**Deduplicate + Log:** giữ nguyên yêu cầu cũ — gom string trùng lặp trước khi gọi API, log rõ số lượng extract/unique/cache-hit/API-call/reject ở mỗi bước.

**Acceptance criteria:** Cố tình tạo 1 case lỗi (ví dụ mock API trả về chuỗi rỗng cho 1 entry, hoặc cố tình sửa 1 PROTECTED field trong bản test) → xác nhận pipeline reject đúng entry đó, rollback, không ghi đè, và game/data gốc không bị ảnh hưởng.

---

## PHASE 4 — Semantic Batching theo category + Cache key theo context

**File cần sửa:** `atm/core/translation/translators.py`, `cache_manager.py`.

**Yêu cầu:**

1. Gắn `category` cho mỗi `TranslationEntry` (Phase 0) dựa theo `path`/`source_file`: `dialogue`, `ui`, `item`, `skill`, `actor_name`, `system`.
2. Gộp batch (~4500 ký tự / 100 câu) chỉ trong cùng category — không trộn "Yes/No/HP" (UI) với đoạn dialogue dài.
3. Cache key đổi từ `text_goc` thành `(text_goc, category)` — vì context ảnh hưởng bản dịch. Viết migration script chuyển cache cũ sang key mới (category mặc định `unknown` cho entry cũ, không invalidate toàn bộ).

**Acceptance criteria:** Dịch thử game có cả UI ngắn và dialogue dài, xác nhận không bị gộp chung batch.

---

## PHASE 5 — Tách 3 tầng lưu trữ: Cache / User Translation Memory / Protected Glossary

Đây là phần nâng cấp lợi thế cạnh tranh cốt lõi của sản phẩm — không cạnh tranh trực tiếp với Google/DeepL về chất lượng dịch máy, mà cạnh tranh bằng khả năng **giữ và tái sử dụng quyết định của người dùng** một cách có cấu trúc.

**File cần sửa:** `cache_manager.py` → tách thành 3 module riêng biệt, không gộp chung 1 bảng key-value như hiện tại.

1. **Cache** (`translation_cache.py`) — mục đích thuần túy tăng tốc, tự động, không cần user can thiệp:
   ```
   key: (text_goc, category) → value: text đã dịch (từ API, chưa qua xác nhận của user)
   ```

2. **User Translation Memory** (`user_tm.py`) — lưu quyết định đã được người dùng xác nhận/sửa, ưu tiên cao hơn Cache khi tra cứu:
   ```python
   class TMEntry:
       original: str
       translation: str
       source: Literal["user", "api"]
       confidence: Literal["confirmed", "auto"]
       last_used: datetime
   ```
   Khi tra cứu, luôn ưu tiên `TMEntry` có `source == "user"` trước, chỉ fallback về Cache/API nếu không có.

3. **Protected Glossary** (`glossary.py`) — thuật ngữ ép buộc, áp dụng **trước khi** gửi câu chứa thuật ngữ đó đi dịch (pre-processing), không phải sửa lại sau khi dịch xong:
   ```
   "Holy Sword" → "Thánh Kiếm"   (luôn luôn, không cho API tự dịch từ này)
   "HP" → "HP"                    (giữ nguyên, không dịch)
   ```
   Cách áp dụng: trước khi gửi câu vào batch dịch, quét glossary, tách thuật ngữ ra thành placeholder (dùng chung cơ chế Protect ở Phase 2/3), dịch phần còn lại, rồi thay thuật ngữ đã ép buộc vào đúng vị trí — đảm bảo Google/DeepL không có cơ hội tự ý dịch khác đi thuật ngữ đã cấu hình.

4. Thứ tự ưu tiên khi tra cứu 1 câu cần dịch: **Glossary (áp dụng cho thuật ngữ con trong câu) → User TM (khớp toàn câu) → Cache (khớp toàn câu) → gọi API**.

**Acceptance criteria:** Test case: user sửa tay 1 bản dịch trong UI và lưu lại → dịch game khác có cùng câu đó → xác nhận hệ thống lấy đúng bản dịch từ User TM (không gọi lại API, không lấy bản Cache cũ nếu 2 cái khác nhau).

---

## PHASE 6 (làm sau cùng, không gấp) — Translation Memory với Fuzzy Match

Chỉ làm sau khi Phase 0–5 đã ổn định và có test đầy đủ.

**Yêu cầu:**
1. Bổ sung layer fuzzy match riêng biệt với User TM/Cache (vốn là exact match) — dùng similarity (Levenshtein ratio hoặc cosine trên embedding nhẹ) để gợi ý bản dịch cho câu gần giống (VD "Attack Power" đã dịch → gợi ý cho "Attack Powers").
2. Ngưỡng similarity mặc định cao (>= 0.85), cho phép chỉnh trong Settings.
3. Kết quả fuzzy match chỉ là **gợi ý hiển thị cho user xác nhận trong UI**, không tự động ghi đè — vì rủi ro sai ngữ nghĩa cao hơn exact match.

---

## Ràng buộc chung cho toàn bộ refactor

- Không phá vỡ Repository pattern hiện có (`ProfileRepository`, `SettingsRepository`) — mọi thay đổi cấu trúc Cache/TM/Glossary phải đi qua repository, không đọc/ghi file trực tiếp trong logic nghiệp vụ.
- Giữ nguyên tách biệt Presentation/Core/Storage/Infrastructure layer theo DI hiện có.
- Mỗi phase khi hoàn thành phải có ít nhất 1 test case chạy được trên game thật, không chỉ unit test giả lập — đặc biệt các test liên quan đến PROTECTED field và Round-trip Validation, vì đây là loại bug chỉ lộ ra khi chạy game thật.
- Viết log chi tiết ở mỗi bước pipeline (đặc biệt bước Classify và Round-trip Validate) để debug khi có game mới phát sinh case lạ chưa từng gặp.
- UNKNOWN classification không bao giờ được tự động xử lý — luôn đưa vào hàng đợi chờ user xác nhận thủ công trong UI trước khi dịch.
