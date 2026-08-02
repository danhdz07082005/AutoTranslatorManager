import os
import tempfile
import pytest
from atm.core.detectors.game_detector import GameDetector

def test_detect_unity_il2cpp():
    # Setup mock game directory for IL2CPP
    with tempfile.TemporaryDirectory() as tmpdir:
        game_exe = os.path.join(tmpdir, "MyGame.exe")
        with open(game_exe, "w") as f:
            f.write("mock binary")
            
        data_dir = os.path.join(tmpdir, "MyGame_Data")
        os.makedirs(data_dir)
        
        il2cpp_dir = os.path.join(data_dir, "il2cpp_data")
        os.makedirs(il2cpp_dir)
        
        engine = GameDetector.detect_engine(game_exe)
        assert engine == "Unity IL2CPP"

def test_detect_unity_mono():
    # Setup mock game directory for Mono
    with tempfile.TemporaryDirectory() as tmpdir:
        game_exe = os.path.join(tmpdir, "MyGame.exe")
        with open(game_exe, "w") as f:
            f.write("mock binary")
            
        data_dir = os.path.join(tmpdir, "MyGame_Data")
        os.makedirs(data_dir)
        
        # Không có folder il2cpp_data
        
        engine = GameDetector.detect_engine(game_exe)
        assert engine == "Unity Mono"

def test_detect_renpy():
    with tempfile.TemporaryDirectory() as tmpdir:
        game_exe = os.path.join(tmpdir, "MyGame.exe")
        with open(game_exe, "w") as f:
            f.write("mock binary")
            
        renpy_dir = os.path.join(tmpdir, "renpy")
        os.makedirs(renpy_dir)
        
        engine = GameDetector.detect_engine(game_exe)
        assert engine == "RenPy"
