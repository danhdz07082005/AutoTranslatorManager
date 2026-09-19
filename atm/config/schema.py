import uuid
from typing import Literal
from pydantic import BaseModel, Field

class AppSettings(BaseModel):
    """Cấu hình chung của Launcher."""
    version: int = Field(default=1, description="Version của config")
    auto_update: bool = Field(default=True, description="Tự động cập nhật payload/plugins")
    dark_mode: bool = Field(default=True, description="Giao diện nền tối")
    ui_language: Literal["vi", "en"] = Field(default="vi", description="Ngôn ngữ của Launcher")
    deepl_api_key: str = Field(default="", description="API Key cho DeepL (nếu có)")

    # Multi-AI / LLM Translation Hub Configuration
    gemini_api_key: str = Field(default="", description="Google Gemini API Key")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Gemini Model")
    gemini_base_url: str = Field(default="", description="Gemini Custom Base URL (optional)")

    deepseek_api_key: str = Field(default="", description="DeepSeek API Key")
    deepseek_model: str = Field(default="deepseek-chat", description="DeepSeek Model (deepseek-chat, deepseek-reasoner)")
    deepseek_base_url: str = Field(default="", description="DeepSeek Custom Base URL (optional)")

    openai_api_key: str = Field(default="", description="OpenAI API Key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI Model (gpt-4o-mini, gpt-4o)")
    openai_base_url: str = Field(default="", description="OpenAI Custom Base URL (optional)")

    claude_api_key: str = Field(default="", description="Anthropic Claude API Key")
    claude_model: str = Field(default="claude-3-7-sonnet-20250219", description="Claude Model")
    claude_base_url: str = Field(default="", description="Claude Custom Base URL (optional)")

    kimi_api_key: str = Field(default="", description="Kimi / Moonshot API Key")
    kimi_model: str = Field(default="moonshot-v1-8k", description="Kimi Model")
    kimi_base_url: str = Field(default="", description="Kimi Custom Base URL (optional)")

    custom_llm_api_key: str = Field(default="", description="Custom / Local LLM API Key")
    custom_llm_base_url: str = Field(default="http://localhost:11434/v1", description="Custom LLM Base URL (e.g. Ollama, LM Studio, OpenRouter)")
    custom_llm_model: str = Field(default="", description="Custom LLM Model Name (e.g. qwen2.5:7b, llama3.1:8b)")

    translation_memory_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Translation-memory fuzzy suggestion threshold",
    )


class GameProfile(BaseModel):
    """Đại diện cho một Game Profile."""
    version: int = Field(default=1)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID")
    game_name: str = Field(..., description="Tên hiển thị của game")
    exe_path: str = Field(..., description="Đường dẫn tuyệt đối đến file chạy của game")
    engine: str = Field(default="Unity IL2CPP", description="Engine (Unity Mono, Unity IL2CPP, RenPy)")
    translator: str = Field(default="google", description="ID của translator plugin")
    input_lang: str = Field(default="ja", description="Ngôn ngữ gốc")
    output_lang: str = Field(default="vi", description="Ngôn ngữ dịch")
    is_deleted: bool = Field(default=False, description="Soft delete flag")
    glossary: dict = Field(default_factory=dict, description="Từ điển cá nhân (Original -> Translated)")
