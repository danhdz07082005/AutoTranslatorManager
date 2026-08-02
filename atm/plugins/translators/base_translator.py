from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTranslator(ABC):
    """
    Interface cơ sở cho mọi Plugin dịch thuật.
    Tất cả các plugin (Google, DeepL, v.v.) phải kế thừa class này.
    """
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        self.config = config or {}

    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Thực hiện dịch một đoạn văn bản.
        
        Args:
            text: Văn bản gốc cần dịch
            source_lang: Mã ngôn ngữ gốc (vd: 'en', 'ja', 'auto')
            target_lang: Mã ngôn ngữ đích (vd: 'vi')
            
        Returns:
            str: Văn bản đã được dịch
        """
        pass

    @abstractmethod
    def check_connection(self) -> bool:
        """Kiểm tra xem dịch vụ có đang hoạt động/kết nối được không."""
        pass
        
    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Trả về ID duy nhất của plugin (phải khớp với ID trong manifest.json)."""
        pass
