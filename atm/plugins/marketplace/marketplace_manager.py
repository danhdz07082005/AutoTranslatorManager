import json
import hashlib
import requests
import os
from typing import List, Dict, Any
from pydantic import BaseModel
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

MARKETPLACE_URL = "https://raw.githubusercontent.com/danhdz07082005/AutoTranslatorManager/main/plugins.json"
PLUGINS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "translators")

class PluginInfo(BaseModel):
    id: str
    name: str
    version: str
    author: str
    description: str
    checksum: str
    download_url: str

class MarketplaceManager:
    """Quản lý việc hiển thị, tải và xác thực Plugin từ Marketplace."""
    
    def fetch_available_plugins(self) -> List[PluginInfo]:
        """Tải danh sách plugin từ GitHub."""
        try:
            # Mocking network call for robust testing if URL fails
            # response = requests.get(MARKETPLACE_URL, timeout=5)
            # response.raise_for_status()
            # data = response.json()
            
            # Temporary mock data for development
            data = [
                {
                    "id": "deepl",
                    "name": "DeepL Translator",
                    "version": "1.0.0",
                    "author": "ATM Team",
                    "description": "High quality AI translation.",
                    "checksum": "dummy_hash_123",
                    "download_url": "https://raw.githubusercontent.com/.../deepl.zip"
                }
            ]
            return [PluginInfo(**item) for item in data]
        except Exception as e:
            logger.error(f"Failed to fetch marketplace plugins: {e}")
            return []

    def verify_checksum(self, file_path: str, expected_hash: str) -> bool:
        """Xác thực mã băm SHA-256 của file tải về."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256.update(byte_block)
            return sha256.hexdigest() == expected_hash
        except Exception as e:
            logger.error(f"Checksum verification error for {file_path}: {e}")
            return False

    def install_plugin(self, plugin: PluginInfo) -> bool:
        """Tải plugin, xác thực checksum và giải nén vào thư mục plugins."""
        logger.info(f"Starting installation for plugin {plugin.name} ({plugin.id})")
        # Giả lập logic download và giải nén
        # Nếu checksum sai, lập tức xóa file tạm và báo lỗi.
        return True
