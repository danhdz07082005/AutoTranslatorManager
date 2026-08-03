from unittest.mock import MagicMock
from atm.core.events.event_bus import EventBus, SystemEvents


def test_subscribe_and_publish():
    """Kiểm tra việc đăng ký (subscribe) và phát (publish) sự kiện."""
    mock_callback = MagicMock()
    
    # Đăng ký callback
    EventBus.subscribe(SystemEvents.GAME_STARTING, mock_callback)
    assert SystemEvents.GAME_STARTING in EventBus._subscribers
    assert len(EventBus._subscribers[SystemEvents.GAME_STARTING]) == 1

    # Phát event kèm dữ liệu
    payload = {"game_name": "Test Game"}
    EventBus.publish(SystemEvents.GAME_STARTING, payload)

    # Callback phải được gọi đúng 1 lần với payload tương ứng
    mock_callback.assert_called_once_with(payload)


def test_publish_unsubscribed_event():
    """Kiểm tra khi phát sự kiện chưa có ai đăng ký lắng nghe."""
    # Phát event chưa từng đăng ký không gây ra ngoại lệ
    EventBus.publish("UNREGISTERED_EVENT", {"data": "test"})


def test_event_bus_error_handling():
    """Kiểm tra việc xử lý lỗi trong callback của subscriber mà không làm đứt đoạn các subscriber khác."""
    def buggy_callback(data):
        raise ValueError("Lỗi cố ý trong subscriber")

    successful_callback = MagicMock()

    # Đăng ký cả 2 callback vào cùng một event
    EventBus.subscribe(SystemEvents.ERROR_OCCURRED, buggy_callback)
    EventBus.subscribe(SystemEvents.ERROR_OCCURRED, successful_callback)

    # Phát event
    EventBus.publish(SystemEvents.ERROR_OCCURRED, "Test payload")

    # Callback hợp lệ vẫn phải được triệu gọi dù callback trước đó gây ngoại lệ
    successful_callback.assert_called_once_with("Test payload")


def test_multiple_subscribers():
    """Kiểm tra nhiều subscribers nhận đủ event theo đúng thứ tự."""
    calls = []
    
    def listener_a(data):
        calls.append("A")
        
    def listener_b(data):
        calls.append("B")

    EventBus.subscribe(SystemEvents.DEPLOYMENT_FINISHED, listener_a)
    EventBus.subscribe(SystemEvents.DEPLOYMENT_FINISHED, listener_b)

    EventBus.publish(SystemEvents.DEPLOYMENT_FINISHED, None)

    assert calls == ["A", "B"]
