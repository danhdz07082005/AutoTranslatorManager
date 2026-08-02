import os
import shutil
import tempfile
import time
import pytest
from atm.config.schema import GameProfile
from atm.core.deployment.game_deployer import GameDeployer
from atm.utils.file_system import copy_payload, cleanup_items

def test_temporary_deploy_and_cleanup():
    """
    E2E Test mô phỏng toàn bộ luồng:
    1. Tạo thư mục Game giả lập
    2. Tạo thư mục Payload giả lập
    3. Chạy lệnh Deploy (copy payload)
    4. Kiểm tra file đã được chép
    5. Cleanup và xác nhận thư mục game sạch sẽ như ban đầu.
    """
    # Setup
    temp_game_dir = tempfile.mkdtemp(prefix="mock_game_")
    temp_payload_dir = tempfile.mkdtemp(prefix="mock_payload_")
    
    # Tạo fake game exe
    fake_exe = os.path.join(temp_game_dir, "Game.exe")
    with open(fake_exe, "w") as f:
        f.write("mock binary")
        
    # Tạo fake payload
    payload_file = os.path.join(temp_payload_dir, "winhttp.dll")
    with open(payload_file, "w") as f:
        f.write("mock dll")
        
    payload_dir = os.path.join(temp_payload_dir, "BepInEx")
    os.makedirs(payload_dir)
    with open(os.path.join(payload_dir, "config.ini"), "w") as f:
        f.write("mock config")
        
    # Deploy
    deployer = GameDeployer()
    deployed_items = copy_payload(temp_payload_dir, temp_game_dir)
    
    # Verify Deploy
    assert len(deployed_items) == 2, "Payload must have 2 items (dll and folder)"
    assert os.path.exists(os.path.join(temp_game_dir, "winhttp.dll"))
    assert os.path.exists(os.path.join(temp_game_dir, "BepInEx", "config.ini"))
    
    # Verify Cleanup
    cleanup_items(deployed_items)
    
    assert not os.path.exists(os.path.join(temp_game_dir, "winhttp.dll"))
    assert not os.path.exists(os.path.join(temp_game_dir, "BepInEx"))
    assert os.path.exists(fake_exe), "Original game files MUST NOT be deleted"
    
    # Teardown
    shutil.rmtree(temp_game_dir)
    shutil.rmtree(temp_payload_dir)
