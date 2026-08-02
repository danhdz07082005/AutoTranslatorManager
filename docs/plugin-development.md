# Plugin Development Guide

Hệ thống của ATM (Auto Translator Manager) được thiết kế xoay quanh kiến trúc Plugin. Bất cứ ai cũng có thể tự viết một Plugin dịch thuật mới (Vd: Claude, Gemini) chỉ trong 5 phút.

## 1. Cấu trúc một Plugin
Một plugin hợp lệ cần được đặt trong thư mục `atm/plugins/translators/tên_plugin/` và bao gồm 2 file:
1. `manifest.json` (Chứa siêu dữ liệu - metadata)
2. `plugin.py` (Chứa logic Python)

## 2. File `manifest.json`
Bắt buộc phải có các trường sau để chống mã độc và phiên bản lỗi:
```json
{
    "id": "my_custom_translator",
    "name": "My Custom Translator",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "Mô tả plugin",
    "minimum_launcher_version": "1.0.0",
    "entry": "plugin.py",
    "class": "MyTranslatorClass",
    "checksum": "" 
}
```

## 3. File `plugin.py`
Phải kế thừa class `BaseTranslator`:
```python
from atm.plugins.translators.base_translator import BaseTranslator

class MyTranslatorClass(BaseTranslator):
    @property
    def plugin_id(self) -> str:
        return "my_custom_translator"
        
    def check_connection(self) -> bool:
        return True
        
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        # Code logic dịch thuật ở đây
        return "Bản dịch của: " + text
```

## 4. Kiểm duyệt và chia sẻ
Để đưa plugin lên **Plugin Marketplace**, bạn hãy gửi Pull Request tới file `plugins.json` của repository chính. Chúng tôi sẽ verify mã nguồn và tạo checksum.
