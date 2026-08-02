from typing import Type, TypeVar, Dict, Any, Callable
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")

T = TypeVar('T')

class DIContainer:
    """
    Dependency Injection Container cực kỳ đơn giản (Singleton Pattern).
    Quản lý việc khởi tạo và cung cấp các Services/Repositories cho toàn hệ thống.
    """
    _instances: Dict[Type[Any], Any] = {}
    _factories: Dict[Type[Any], Callable[[], Any]] = {}

    @classmethod
    def register_instance(cls, interface: Type[T], instance: T) -> None:
        """Đăng ký một đối tượng đã được khởi tạo."""
        cls._instances[interface] = instance
        logger.debug(f"Registered instance for {interface.__name__}")

    @classmethod
    def register_factory(cls, interface: Type[T], factory: Callable[[], T]) -> None:
        """Đăng ký một factory function để lazy load."""
        cls._factories[interface] = factory
        logger.debug(f"Registered factory for {interface.__name__}")

    @classmethod
    def resolve(cls, interface: Type[T]) -> T:
        """Lấy một instance theo Interface. Nếu là factory, gọi factory để tạo."""
        if interface in cls._instances:
            return cls._instances[interface]
        
        if interface in cls._factories:
            instance = cls._factories[interface]()
            cls._instances[interface] = instance # Cache the instance
            logger.debug(f"Resolved factory for {interface.__name__}")
            return instance

        raise KeyError(f"Dependency {interface.__name__} not found in DI Container!")
