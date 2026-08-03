from atm.core.translation.translators import GoogleTranslator, DeepLTranslator, BaseTranslator
from atm.core.translation.rpgmaker_translator import RPGMakerTranslator

def get_translator(translator_id: str, settings) -> BaseTranslator:
    if translator_id == "deepl" and settings and settings.deepl_api_key:
        return DeepLTranslator(settings.deepl_api_key)
    return GoogleTranslator()
