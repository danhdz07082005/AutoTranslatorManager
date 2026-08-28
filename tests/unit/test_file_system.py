import os
from atm.utils.file_system import copy_payload, cleanup_items


def test_copy_payload(tmp_path):
    """Kiểm tra việc copy toàn bộ nội dung từ src_dir sang dest_dir."""
    src_dir = tmp_path / "source"
    dest_dir = tmp_path / "destination"
    src_dir.mkdir()
    dest_dir.mkdir()

    # Tạo các file và thư mục mẫu trong source
    file1 = src_dir / "plugin.dll"
    file1.write_text("dll content", encoding="utf-8")

    sub_folder = src_dir / "BepInEx"
    sub_folder.mkdir()
    file2 = sub_folder / "config.ini"
    file2.write_text("config content", encoding="utf-8")

    # Thực hiện copy
    copied_items = copy_payload(str(src_dir), str(dest_dir))

    # Kiểm tra kết quả copy
    copied_file1 = dest_dir / "plugin.dll"
    copied_folder = dest_dir / "BepInEx"
    copied_file2 = copied_folder / "config.ini"

    assert copied_file1.exists()
    assert copied_file1.read_text(encoding="utf-8") == "dll content"
    assert copied_folder.exists()
    assert copied_file2.exists()
    assert copied_file2.read_text(encoding="utf-8") == "config content"

    # Kiểm tra danh sách đường dẫn trả về
    assert str(copied_file1) in copied_items.copied_items
    assert str(copied_folder) in copied_items.copied_items


def test_copy_payload_skip_existing(tmp_path):
    """Kiểm tra copy_payload không ghi đè nếu file/folder đã tồn tại ở đích."""
    src_dir = tmp_path / "source"
    dest_dir = tmp_path / "destination"
    src_dir.mkdir()
    dest_dir.mkdir()

    # Tạo file ở source
    file_src = src_dir / "data.txt"
    file_src.write_text("new content", encoding="utf-8")

    # Tạo file trùng tên ở dest với nội dung cũ
    file_dest = dest_dir / "data.txt"
    file_dest.write_text("original user content", encoding="utf-8")

    copied_items = copy_payload(str(src_dir), str(dest_dir))

    # File không bị ghi đè và không nằm trong danh sách copied_items
    assert file_dest.read_text(encoding="utf-8") == "original user content"
    assert str(file_dest) not in copied_items.copied_items


def test_cleanup_items(tmp_path):
    """Kiểm tra dọn dẹp (xóa) các file và folder dựa trên danh sách truyền vào."""
    # Tạo các file và folder cần dọn dẹp
    temp_file = tmp_path / "temp_file.txt"
    temp_file.write_text("to be deleted", encoding="utf-8")

    temp_dir = tmp_path / "temp_dir"
    temp_dir.mkdir()
    (temp_dir / "inner.txt").write_text("inner content", encoding="utf-8")

    items_to_clean = [str(temp_file), str(temp_dir)]

    # Thực hiện dọn dẹp
    cleanup_items(items_to_clean)

    # Kiểm tra file và thư mục đã bị xóa hoàn toàn
    assert not temp_file.exists()
    assert not temp_dir.exists()


def test_cleanup_items_non_existent():
    """Kiểm tra cleanup_items không gây ra lỗi khi đường dẫn không tồn tại."""
    # Truyền vào đường dẫn ảo
    cleanup_items(["C:/NonExistentFolder/temp.txt", "/invalid/path/folder"])
