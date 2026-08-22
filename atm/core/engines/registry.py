from atm.core.engines.base import BaseExtractor, BaseInjector, BaseAuditor

class EngineRegistry:
    _extractors = {}
    _injectors = {}
    _auditors = {}
    
    @classmethod
    def register(cls, engine_name: str, extractor: type, injector: type, auditor: type):
        cls._extractors[engine_name] = extractor
        cls._injectors[engine_name] = injector
        cls._auditors[engine_name] = auditor
        
    @classmethod
    def get_extractor(cls, engine_name: str, game_dir: str) -> BaseExtractor:
        ext = cls._extractors.get(engine_name)
        if ext: return ext(game_dir)
        raise ValueError(f"No extractor registered for {engine_name}")
        
    @classmethod
    def get_injector(cls, engine_name: str, game_dir: str) -> BaseInjector:
        inj = cls._injectors.get(engine_name)
        if inj: return inj(game_dir)
        raise ValueError(f"No injector registered for {engine_name}")
        
    @classmethod
    def get_auditor(cls, engine_name: str) -> BaseAuditor:
        aud = cls._auditors.get(engine_name)
        if aud: return aud()
        raise ValueError(f"No auditor registered for {engine_name}")

