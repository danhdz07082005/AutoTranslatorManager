import time
import pytest
from unittest.mock import MagicMock, patch
from atm.core.deployment.process_monitor import ProcessMonitor

@patch("atm.core.deployment.process_monitor.subprocess.Popen")
@patch("atm.core.deployment.process_monitor.psutil.Process")
def test_process_monitor_stop_kills_tree(mock_psutil_process, mock_popen):
    """
    Test rằng stop() của ProcessMonitor sẽ gọi kill() trên cả tiến trình con 
    (children) và tiến trình cha (parent).
    """
    monitor = ProcessMonitor()
    
    # Mock subprocess
    mock_process = MagicMock()
    mock_process.pid = 1234
    mock_popen.return_value = mock_process
    monitor.process = mock_process
    
    # Mock psutil
    mock_parent = MagicMock()
    mock_child1 = MagicMock()
    mock_child2 = MagicMock()
    
    mock_parent.children.return_value = [mock_child1, mock_child2]
    mock_psutil_process.return_value = mock_parent
    
    # Act
    monitor.stop()
    
    # Assert
    # Check that children are killed first
    mock_child1.kill.assert_called_once()
    mock_child2.kill.assert_called_once()
    
    # Check that parent is killed
    mock_parent.kill.assert_called_once()

@patch("atm.core.deployment.process_monitor.subprocess.Popen")
@patch("atm.core.deployment.process_monitor.psutil.Process")
def test_process_monitor_start_and_monitor_cleanup(mock_psutil_process, mock_popen):
    """
    Test vòng lặp monitor tự kết thúc khi toàn bộ tree chết.
    """
    monitor = ProcessMonitor()
    
    # Giả lập chạy
    mock_process = MagicMock()
    mock_process.pid = 1234
    mock_popen.return_value = mock_process
    
    mock_parent = MagicMock()
    mock_parent.is_running.return_value = False # Giả lập tree đã chết ngay
    mock_parent.children.return_value = []
    mock_psutil_process.return_value = mock_parent
    
    callback_called = False
    def mock_callback():
        nonlocal callback_called
        callback_called = True
        
    # Start monitor (Nó sẽ sleep 2 giây trong thread)
    success = monitor.start_and_monitor("dummy.exe", "dummy_dir", mock_callback)
    
    assert success is True
    assert monitor.is_monitoring is True
    
    # Wait for thread to finish (2 seconds sleep + execution time)
    time.sleep(2.5)
    
    assert callback_called is True
    assert monitor.is_monitoring is False
