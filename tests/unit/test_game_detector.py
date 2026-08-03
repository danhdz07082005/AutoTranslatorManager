import os
from atm.core.detectors.game_detector import GameDetector


def test_detect_engine_unknown_non_existent_file():
    """Kiểm tra nhận diện file không tồn tại trả về 'Unknown'."""
    engine = GameDetector.detect_engine("C:/NonExistentPath/game.exe")
    assert engine == "Unknown"


def test_detect_engine_unity_il2cpp_with_il2cpp_folder(tmp_path):
    """Kiểm tra nhận diện Unity IL2CPP khi có thư mục il2cpp_data trong _Data."""
    game_dir = tmp_path / "MyIL2CPPGame"
    game_dir.mkdir()
    exe_path = game_dir / "Game.exe"
    exe_path.touch()

    data_dir = game_dir / "Game_Data"
    data_dir.mkdir()
    il2cpp_data = data_dir / "il2cpp_data"
    il2cpp_data.mkdir()

    engine = GameDetector.detect_engine(str(exe_path))
    assert engine == "Unity IL2CPP"


def test_detect_engine_unity_il2cpp_with_game_assembly_dll(tmp_path):
    """Kiểm tra nhận diện Unity IL2CPP khi có file GameAssembly.dll."""
    game_dir = tmp_path / "MyIL2CPPGame2"
    game_dir.mkdir()
    exe_path = game_dir / "Game.exe"
    exe_path.touch()

    data_dir = game_dir / "Game_Data"
    data_dir.mkdir()
    
    assembly_dll = game_dir / "GameAssembly.dll"
    assembly_dll.touch()

    engine = GameDetector.detect_engine(str(exe_path))
    assert engine == "Unity IL2CPP"


def test_detect_engine_unity_mono(tmp_path):
    """Kiểm tra nhận diện Unity Mono khi có thư mục _Data nhưng không có IL2CPP data."""
    game_dir = tmp_path / "MyMonoGame"
    game_dir.mkdir()
    exe_path = game_dir / "Game.exe"
    exe_path.touch()

    data_dir = game_dir / "Game_Data"
    data_dir.mkdir()

    engine = GameDetector.detect_engine(str(exe_path))
    assert engine == "Unity Mono"


def test_detect_engine_renpy_with_renpy_folder(tmp_path):
    """Kiểm tra nhận diện RenPy khi có thư mục 'renpy'."""
    game_dir = tmp_path / "MyRenPyGame"
    game_dir.mkdir()
    exe_path = game_dir / "Game.exe"
    exe_path.touch()

    renpy_dir = game_dir / "renpy"
    renpy_dir.mkdir()

    engine = GameDetector.detect_engine(str(exe_path))
    assert engine == "RenPy"


def test_detect_engine_renpy_with_script_rpyc(tmp_path):
    """Kiểm tra nhận diện RenPy khi có file 'game/script.rpyc'."""
    game_dir = tmp_path / "MyRenPyGame2"
    game_dir.mkdir()
    exe_path = game_dir / "Game.exe"
    exe_path.touch()

    game_subdir = game_dir / "game"
    game_subdir.mkdir()
    script_file = game_subdir / "script.rpyc"
    script_file.touch()

    engine = GameDetector.detect_engine(str(exe_path))
    assert engine == "RenPy"


def test_detect_engine_unknown_other_game(tmp_path):
    """Kiểm tra nhận diện game không phải Unity hay RenPy trả về 'Unknown'."""
    game_dir = tmp_path / "CustomEngineGame"
    game_dir.mkdir()
    exe_path = game_dir / "Game.exe"
    exe_path.touch()

    engine = GameDetector.detect_engine(str(exe_path))
    assert engine == "Unknown"
