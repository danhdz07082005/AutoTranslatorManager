from typing import List
from atm.core.engines.base import BaseInjector
from atm.core.engines.ir import LocalizationEntry

class BakinInjector(BaseInjector):
    def inject(self, entries: List[LocalizationEntry]) -> bool:
        # Gi? l?p t?o dic.txt
        return True

