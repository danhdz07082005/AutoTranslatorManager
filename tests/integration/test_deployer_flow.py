import os
from unittest.mock import MagicMock
from atm.core.deployment.game_deployer import GameDeployer
from atm.core.events.event_bus import EventBus, SystemEvents


def test_deploy_and_launch_missing_payload(sample_game_profile, tmp_path):
    """
    Kiểm tra luồng deploy_and_launch khi thư mục payload (BepInEx) bị thiếu:
    - Sự kiện GAME_STARTING được phát.
    - Phát hiện thiếu payload dir -> ngắt triển khai và phát sự kiện ERROR_OCCURRED.
    - Không copy file hay chạy tiến trình game.
    """
    starting_events = []
    error_events = []

    def on_starting(data):
        starting_events.append(data)

    def on_error(data):
        error_events.append(data)

    bus = EventBus()
    bus.subscribe(SystemEvents.GAME_STARTING, on_starting)
    bus.subscribe(SystemEvents.ERROR_OCCURRED, on_error)

    deployer = GameDeployer(event_bus=bus)
    missing_payload_dir = str(tmp_path / "missing_payload_dir")

    # Gọi hàm triển khai với payload dir không tồn tại
    deployer.deploy_and_launch(sample_game_profile, missing_payload_dir)

    # Đảm bảo GAME_STARTING đã phát
    assert len(starting_events) == 1
    assert starting_events[0].id == sample_game_profile.id

    # Đảm bảo ERROR_OCCURRED đã phát với thông báo thiếu payload
    assert len(error_events) == 1
    assert error_events[0] == "Payload not found!"

    # Không có file nào được copy
    assert len(deployer._deployed_items) == 0


def test_deploy_and_launch_success_and_cleanup_flow(sample_game_profile, tmp_path):
    """
    Kiểm tra luồng deploy thành công khi payload tồn tại, sau đó giả lập game kết thúc 
    để kiểm tra tự động dọn rác (cleanup).
    """
    # 1. Chuẩn bị thư mục game và payload giả
    game_dir = tmp_path / "MyTestGame"
    game_dir.mkdir()
    game_exe = game_dir / "Game.exe"
    game_exe.touch()

    sample_game_profile.exe_path = str(game_exe)

    payload_dir = tmp_path / "payloads" / "bepinex"
    payload_dir.mkdir(parents=True)
    (payload_dir / "winhttp.dll").write_text("fake dll", encoding="utf-8")
    
    bepinex_folder = payload_dir / "BepInEx"
    bepinex_folder.mkdir()
    (bepinex_folder / "config.cfg").write_text("fake config", encoding="utf-8")

    # Lắng nghe các event
    events_triggered = []
    bus = EventBus()
    bus.subscribe(SystemEvents.GAME_STARTING, lambda d: events_triggered.append("STARTING"))
    bus.subscribe(SystemEvents.DEPLOYMENT_FINISHED, lambda d: events_triggered.append("DEPLOYED"))
    bus.subscribe(SystemEvents.GAME_EXITED, lambda d: events_triggered.append("EXITED"))
    bus.subscribe(SystemEvents.CLEANUP_FINISHED, lambda d: events_triggered.append("CLEANED"))

    deployer = GameDeployer(event_bus=bus)
    # Giả lập monitor.start_and_monitor trả về True mà không chạy tiến trình thật
    deployer.monitor.start_and_monitor = MagicMock(return_value=True)

    # Chạy deploy_and_launch
    deployer.deploy_and_launch(sample_game_profile, str(payload_dir))

    # Kiểm tra event triển khai thành công
    assert "STARTING" in events_triggered
    assert "DEPLOYED" in events_triggered

    # Kiểm tra các file đã được copy vào game_dir
    assert (game_dir / "winhttp.dll").exists()
    assert (game_dir / "BepInEx" / "config.cfg").exists()
    assert (game_dir / "ATM_IS_RUNNING.txt").exists()

    # Giả lập tiến trình game thoát -> kích hoạt callback dọn rác _on_game_exited
    deployer._on_game_exited()

    # Kiểm tra event dọn rác đã phát
    assert "EXITED" in events_triggered
    assert "CLEANED" in events_triggered

    # Đảm bảo các file copy tạm thời đã bị xóa sạch sẽ khỏi game_dir
    assert not (game_dir / "winhttp.dll").exists()
    assert not (game_dir / "BepInEx").exists()
    assert not (game_dir / "ATM_IS_RUNNING.txt").exists()
