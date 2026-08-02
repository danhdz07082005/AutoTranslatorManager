from typing import Callable, Any, Dict, List
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

class EventBus:
    """
    Event Bus trung tâm để giao tiếp giữa các thành phần hệ thống.
    Giúp giảm coupling giữa UI và Core Logic.
    """
    _subscribers: Dict[str, List[Callable[[Any], None]]] = {}

    @classmethod
    def subscribe(cls, event_type: str, callback: Callable[[Any], None]) -> None:
        """Đăng ký lắng nghe một event."""
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to event: {event_type}")

    @classmethod
    def publish(cls, event_type: str, data: Any = None) -> None:
        """Phát một event kèm dữ liệu."""
        if event_type in cls._subscribers:
            logger.info(f"Publishing event: {event_type}")
            for callback in cls._subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")

# Các hằng số Event
class SystemEvents:
    GAME_STARTING = "GAME_STARTING"
    DEPLOYMENT_FINISHED = "DEPLOYMENT_FINISHED"
    GAME_EXITED = "GAME_EXITED"
    CLEANUP_FINISHED = "CLEANUP_FINISHED"
    TRANSLATION_ACTIVE = "TRANSLATION_ACTIVE"
    ERROR_OCCURRED = "ERROR_OCCURRED"
