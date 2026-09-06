# Plugin Development Guide / Hướng Dẫn Phát Triển Plugin

[ **[Tiếng Việt](#-tiếng-việt)** | **[English](#-english)** ]

---

## 🇻🇳 Tiếng Việt

Kiến trúc của Auto Translator Manager (ATM V2) được thiết kế theo mô hình **Modular Plugin-based Architecture**. Bất kỳ ai cũng có thể tự tạo và tích hợp một bộ dịch thuật mới (ví dụ: Google, DeepL, Claude, OpenAI, Gemini, Local LLM) chỉ trong vài phút.

### 1. Cấu trúc thư mục Plugin
Mỗi plugin dịch thuật là một thư mục con nằm tại:
`atm/plugins/translators/{plugin_id}/`

Một plugin hợp lệ bắt buộc phải có 2 file:
1. `manifest.json`: Chứa siêu dữ liệu (metadata), phiên bản, tác giả và cấu hình plugin.
2. `plugin.py`: Chứa mã nguồn Python thực thi kế thừa từ `BaseTranslator`.

---

### 2. Định dạng file `manifest.json`
```json
{
  "id": "my_custom_translator",
  "name": "My Custom AI Translator",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Bộ dịch thuật tùy chỉnh sử dụng mô hình AI / API bên thứ ba.",
  "minimum_launcher_version": "2.0.0",
  "entry": "plugin.py",
  "class": "MyTranslatorClass",
  "checksum": ""
}
```

#### Giải thích các trường:
* `id`: Định danh duy nhất của plugin (viết thường, dùng dấu gạch dưới `_`).
* `name`: Tên hiển thị trên giao diện người dùng.
* `version`: Phiên bản tuân thủ Semantic Versioning (SemVer: `x.y.z`).
* `entry`: Tên file mã nguồn chứa class plugin (mặc định: `plugin.py`).
* `class`: Tên class Python kế thừa `BaseTranslator`.
* `minimum_launcher_version`: Phiên bản ATM tối thiểu tương thích.

---

### 3. Hiện thực file `plugin.py`
Plugin cần kế thừa `BaseTranslator` từ `atm.plugins.translators.base_translator`:

```python
from typing import Dict, Any
from atm.plugins.translators.base_translator import BaseTranslator

class MyTranslatorClass(BaseTranslator):
    def __init__(self, config: Dict[str, Any] = None) -> None:
        super().__init__(config)
        self.api_key = self.config.get("api_key", "")
        self.endpoint = self.config.get("endpoint", "https://api.example.com/v1/translate")

    @property
    def plugin_id(self) -> str:
        """Trả về ID duy nhất khớp với ID khai báo trong manifest.json."""
        return "my_custom_translator"

    def check_connection(self) -> bool:
        """Kiểm tra tính khả dụng của dịch vụ trước khi bắt đầu phiên dịch."""
        try:
            # Thực hiện ping hoặc kiểm tra trạng thái mạng
            return True
        except Exception:
            return False

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Thực hiện dịch một chuỗi văn bản.
        
        Args:
            text: Chuỗi văn bản gốc cần dịch.
            source_lang: Mã ngôn ngữ nguồn (ví dụ: 'ja', 'en', 'auto').
            target_lang: Mã ngôn ngữ đích (ví dụ: 'vi', 'en').
            
        Returns:
            str: Văn bản đã được dịch thuật.
        """
        if not text or not text.strip():
            return text

        # TODO: Triển khai logic gọi API hoặc gọi Local Model
        translated_text = f"[Dịch]: {text}"
        return translated_text
```

---

### 4. Kiểm thử Plugin cục bộ
1. Đặt thư mục plugin vào `atm/plugins/translators/my_custom_translator/`.
2. Khởi động ATM: `python run_app.py`.
3. Kiểm tra log khởi động (`logs/launcher.log`) để xác nhận plugin đã được DI Container nạp thành công.

---

## 🇬🇧 English

The ATM V2 framework embraces a **Modular Plugin-based Architecture**. Developers can easily integrate custom translation engines (e.g., Google, DeepL, Anthropic Claude, OpenAI ChatGPT, Gemini, or Local LLMs) with minimal boilerplate.

### 1. Plugin Directory Structure
Each translator plugin resides in its own folder under:
`atm/plugins/translators/{plugin_id}/`

A valid plugin requires two essential files:
1. `manifest.json`: Metadata, versioning, author, and class entrypoint specifications.
2. `plugin.py`: Python implementation subclassing `BaseTranslator`.

---

### 2. `manifest.json` Specification
```json
{
  "id": "my_custom_translator",
  "name": "My Custom AI Translator",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Custom translation plugin powered by third-party APIs or local models.",
  "minimum_launcher_version": "2.0.0",
  "entry": "plugin.py",
  "class": "MyTranslatorClass",
  "checksum": ""
}
```

---

### 3. Implementing `plugin.py`
Subclass `BaseTranslator` located at `atm.plugins.translators.base_translator`:

```python
from typing import Dict, Any
from atm.plugins.translators.base_translator import BaseTranslator

class MyTranslatorClass(BaseTranslator):
    def __init__(self, config: Dict[str, Any] = None) -> None:
        super().__init__(config)
        self.api_key = self.config.get("api_key", "")
        self.endpoint = self.config.get("endpoint", "https://api.example.com/v1/translate")

    @property
    def plugin_id(self) -> str:
        """Returns the unique plugin identifier matching manifest.json."""
        return "my_custom_translator"

    def check_connection(self) -> bool:
        """Verifies service connectivity before batch translation starts."""
        try:
            # Perform health check or test request
            return True
        except Exception:
            return False

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translates a single string.
        
        Args:
            text: Source text to translate.
            source_lang: Source language code (e.g., 'ja', 'en', 'auto').
            target_lang: Target language code (e.g., 'vi', 'en').
            
        Returns:
            str: Translated text string.
        """
        if not text or not text.strip():
            return text

        # Implement your API/LLM request logic here
        translated_text = f"[Translated]: {text}"
        return translated_text
```

---

### 4. Local Testing & Verification
1. Place your plugin directory in `atm/plugins/translators/my_custom_translator/`.
2. Launch the application: `python run_app.py`.
3. Check `logs/launcher.log` to ensure the plugin has been successfully registered by the Dependency Injection Container.

