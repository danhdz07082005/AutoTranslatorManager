from atm.core.engines.registry import EngineRegistry
from .extractor import BakinExtractor
from .injector import BakinInjector
from .auditor import BakinAuditor

EngineRegistry.register("Bakin", BakinExtractor, BakinInjector, BakinAuditor)

