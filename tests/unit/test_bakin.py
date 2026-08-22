import os
from atm.core.engines.ir import LocalizationEntry
from atm.core.engines.bakin.extractor import BakinExtractor
from atm.core.engines.bakin.auditor import BakinAuditor

def test_bakin_auditor():
    auditor = BakinAuditor()
    entries = [
        LocalizationEntry(translation_status="translated", confidence=1.0),
        LocalizationEntry(translation_status="pending", confidence=0.3)
    ]
    report = auditor.audit(entries)
    assert report["coverage_percent"] == 50.0
    assert report["untranslated"] == 1
    assert report["confidence_breakdown"]["high"] == 1
    assert report["confidence_breakdown"]["low"] == 1

def test_bakin_extractor():
    extractor = BakinExtractor("mock_dir")
    entries = extractor.extract()
    assert len(entries) == 3

