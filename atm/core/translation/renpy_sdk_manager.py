"""Manages automatic download, verification, and caching of Ren'Py SDKs."""

import hashlib
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")


class RenPySDKManager:
    """Manages downloading, verifying, and extracting Ren'Py SDKs."""

    KNOWN_SDKS = {
        "8.2.1": {
            "url": "https://www.renpy.org/dl/8.2.1/renpy-8.2.1-sdk.zip",
            "sha256": "8f8b3b3a6c17e6530a6b8c9d4e5f7a2d480ebf4c54b2b6470cf59c4038a8e323"
        }
    }

    def __init__(self, cache_dir: Path | str | None = None, default_version: str = "8.2.1"):
        if cache_dir is None:
            from atm.utils.paths import get_app_data_dir
            cache_dir = Path(get_app_data_dir()) / "sdk_cache"
        self.cache_dir = Path(cache_dir)
        self.default_version = default_version
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error("Failed to create SDK cache directory: %s", e)

    def _verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        if not expected_sha256:
            return True
        sha256_hash = hashlib.sha256()
        try:
            with file_path.open("rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest() == expected_sha256
        except OSError as e:
            logger.error("Failed to read file for checksum verification: %s", e)
            return False

    def get_sdk_path(self, version: Optional[str] = None) -> Optional[Path]:
        """Return the path to the extracted SDK, downloading it if necessary."""
        version = version or self.default_version
        sdk_info = self.KNOWN_SDKS.get(version)
        if not sdk_info:
            logger.error("Unknown Ren'Py SDK version: %s", version)
            return None

        url = sdk_info["url"]
        expected_sha256 = sdk_info.get("sha256", "")

        zip_path = self.cache_dir / f"renpy-{version}-sdk.zip"
        extract_dir = self.cache_dir / f"renpy-{version}-sdk"

        if extract_dir.is_dir() and (extract_dir / "renpy.sh").is_file():
            return extract_dir

        if zip_path.is_file():
            if self._verify_checksum(zip_path, expected_sha256):
                logger.info("Verified existing SDK archive for version %s", version)
            else:
                logger.warning("Checksum mismatch for %s, deleting and re-downloading...", zip_path)
                try:
                    zip_path.unlink()
                except OSError as e:
                    logger.error("Failed to delete corrupted SDK archive: %s", e)
                    return None

        if not zip_path.is_file():
            logger.info("Downloading Ren'Py SDK %s from %s...", version, url)
            for attempt in range(1, 4):
                try:
                    urllib.request.urlretrieve(url, zip_path)
                    if self._verify_checksum(zip_path, expected_sha256):
                        logger.info("Download and verification successful.")
                        break
                    else:
                        logger.error("Downloaded file failed checksum verification.")
                        zip_path.unlink()
                except Exception as e:
                    logger.error("Download attempt %d failed: %s", attempt, e)
                    if attempt == 3:
                        logger.error("Failed to download SDK after 3 attempts.")
                        return None
            else:
                return None

        logger.info("Extracting SDK to %s...", extract_dir)
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.cache_dir)
        except Exception as e:
            logger.error("Failed to extract SDK: %s", e)
            return None

        return extract_dir
