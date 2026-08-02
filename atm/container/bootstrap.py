from atm.container.providers import register_services, load_plugins
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

def bootstrap_app() -> None:
    """Hàm khởi tạo chạy đầu tiên khi mở ứng dụng."""
    logger.info("Initializing Auto Translator Manager...")
    
    # 1. Đăng ký dependencies
    register_services()
    logger.info("Services registered via DI Container.")
    
    # 2. Quét và load các plugin
    load_plugins()
    logger.info("Plugins loaded.")
    
    logger.info("Bootstrap complete. System ready.")
