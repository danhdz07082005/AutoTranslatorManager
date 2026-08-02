from pydantic import BaseModel, Field

class AppSettings(BaseModel):
    """Cấu hình chung của Launcher."""
    version: int = Field(default=1, description="Version của config")
    auto_update: bool = Field(default=True, description="Tự động cập nhật payload/plugins")
    dark_mode: bool = Field(default=True, description="Giao diện nền tối")
    language: str = Field(default="vi", description="Ngôn ngữ của Launcher")

class GameProfile(BaseModel):
    """Đại diện cho một Game Profile."""
    version: int = Field(default=1)
    game_name: str = Field(..., description="Tên hiển thị của game")
    exe_path: str = Field(..., description="Đường dẫn tuyệt đối đến file chạy của game")
    engine: str = Field(default="Unity IL2CPP", description="Engine (Unity Mono, Unity IL2CPP, RenPy)")
    translator: str = Field(default="google", description="ID của translator plugin")
    input_lang: str = Field(default="ja", description="Ngôn ngữ gốc")
    output_lang: str = Field(default="vi", description="Ngôn ngữ dịch")
