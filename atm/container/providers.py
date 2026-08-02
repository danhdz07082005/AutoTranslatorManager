from atm.container.container import DIContainer

def register_services() -> None:
    """Đăng ký tất cả các Repositories, Services và Core Utilities vào Container."""
    # Sẽ đăng ký các Repository ở đây
    # DIContainer.register_factory(IProfileRepository, lambda: JsonProfileRepository())
    
    # Sẽ đăng ký các Service ở đây
    # DIContainer.register_factory(IGameDeployer, lambda: GameDeployer())
    pass

def load_plugins() -> None:
    """Quét thư mục plugins/ và nạp vào hệ thống qua PluginManager."""
    # Tương lai sẽ duyệt folder và load dynamic
    pass
