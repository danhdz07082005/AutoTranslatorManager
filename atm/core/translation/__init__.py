from atm.core.translation.translators import (
    GoogleTranslator,
    DeepLTranslator,
    LLMTranslator,
    BaseTranslator,
)
from atm.core.translation.rpgmaker_translator import RPGMakerTranslator

def get_translator(translator_id: str, settings, profile=None) -> BaseTranslator:
    """Factory creating appropriate translator engine based on ID and settings."""
    tid = (translator_id or "google").lower()

    if tid == "deepl":
        key = getattr(settings, "deepl_api_key", "") if settings else ""
        return DeepLTranslator(key)

    if tid in ("gemini", "deepseek", "openai", "claude", "kimi", "custom_llm"):
        glossary = getattr(profile, "glossary", {}) if profile else {}
        if tid == "gemini":
            return LLMTranslator(
                provider="gemini",
                api_key=getattr(settings, "gemini_api_key", "") if settings else "",
                model=getattr(settings, "gemini_model", "gemini-1.5-flash") if settings else "gemini-1.5-flash",
                base_url=getattr(settings, "gemini_base_url", "") if settings else "",
                glossary=glossary,
            )
        elif tid == "deepseek":
            return LLMTranslator(
                provider="deepseek",
                api_key=getattr(settings, "deepseek_api_key", "") if settings else "",
                model=getattr(settings, "deepseek_model", "deepseek-chat") if settings else "deepseek-chat",
                base_url=getattr(settings, "deepseek_base_url", "") if settings else "",
                glossary=glossary,
            )
        elif tid == "openai":
            return LLMTranslator(
                provider="openai",
                api_key=getattr(settings, "openai_api_key", "") if settings else "",
                model=getattr(settings, "openai_model", "gpt-4o-mini") if settings else "gpt-4o-mini",
                base_url=getattr(settings, "openai_base_url", "") if settings else "",
                glossary=glossary,
            )
        elif tid == "claude":
            return LLMTranslator(
                provider="claude",
                api_key=getattr(settings, "claude_api_key", "") if settings else "",
                model=getattr(settings, "claude_model", "claude-3-5-haiku-20241022") if settings else "claude-3-5-haiku-20241022",
                base_url=getattr(settings, "claude_base_url", "") if settings else "",
                glossary=glossary,
            )
        elif tid == "kimi":
            return LLMTranslator(
                provider="kimi",
                api_key=getattr(settings, "kimi_api_key", "") if settings else "",
                model=getattr(settings, "kimi_model", "moonshot-v1-8k") if settings else "moonshot-v1-8k",
                base_url=getattr(settings, "kimi_base_url", "") if settings else "",
                glossary=glossary,
            )
        elif tid == "custom_llm":
            return LLMTranslator(
                provider="custom_llm",
                api_key=getattr(settings, "custom_llm_api_key", "") if settings else "",
                base_url=getattr(settings, "custom_llm_base_url", "http://localhost:11434/v1") if settings else "http://localhost:11434/v1",
                model=getattr(settings, "custom_llm_model", "qwen2.5:7b") if settings else "qwen2.5:7b",
                glossary=glossary,
            )

    return GoogleTranslator()

