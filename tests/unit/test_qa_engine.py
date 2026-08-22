import json
import pytest
from pathlib import Path
from atm.core.qa.registry import QARule, QARuleRegistry
from atm.core.qa.engine import QAEngine

def test_safe_regex_detection():
    # Valid regex
    rule1 = QARule(1, "r1", "regex_match", "error", r"\[Player\]")
    assert rule1.is_safe_regex() == True
    
    # Invalid regex syntax
    rule2 = QARule(1, "r2", "regex_match", "error", r"[Player")
    assert rule2.is_safe_regex() == False
    
    # Catastrophic backtracking detection: (a+)+
    rule3 = QARule(1, "r3", "regex_match", "error", r"([a-z]+)+")
    assert rule3.is_safe_regex() == False
    
    # Nested quantifier: (.*)*
    rule4 = QARule(1, "r4", "regex_match", "error", r"(.*)*")
    assert rule4.is_safe_regex() == False

def test_qa_registry_overlay(tmp_path: Path):
    sys_path = tmp_path / "system.json"
    sys_path.write_text(json.dumps({
        "rules": [
            {"rule_id": "r1", "type": "regex_match", "severity": "error", "pattern": "abc"},
            {"rule_id": "r2", "type": "regex_replace", "severity": "warning", "pattern": "def", "replacement": "xyz"}
        ]
    }))
    
    usr_path = tmp_path / "user.json"
    usr_path.write_text(json.dumps({
        "rules": [
            {"rule_id": "r1", "enabled": False}, # override system rule
            {"rule_id": "r3", "type": "regex_match", "severity": "error", "pattern": "custom"} # new custom rule
        ]
    }))
    
    registry = QARuleRegistry(str(sys_path), str(usr_path))
    
    assert "r1" in registry.rules
    assert registry.rules["r1"].enabled == False
    assert registry.rules["r1"].source == "user_override"
    
    assert "r2" in registry.rules
    assert registry.rules["r2"].enabled == True
    assert registry.rules["r2"].source == "system"
    
    assert "r3" in registry.rules
    assert registry.rules["r3"].source == "user"
    
    active = registry.get_active_rules()
    assert len(active) == 2
    assert active[0].rule_id == "r2"
    assert active[1].rule_id == "r3"

def test_qa_engine_token_invariant(tmp_path: Path):
    sys_path = tmp_path / "sys.json"
    sys_path.write_text(json.dumps({
        "rules": [
            {
                "rule_id": "newline_space",
                "type": "regex_replace",
                "severity": "error",
                "pattern": r"\\n\s+",
                "replacement": r"\\n"
            }
        ]
    }))
    registry = QARuleRegistry(str(sys_path), "non_existent.json")
    engine = QAEngine(registry)
    
    # 1. Safe Suggestion: Protected tokens perfectly match
    source = "Hello\\nWorld [Player] <color=red>"
    translated_bad = "Xin chào\\n Thế giới [Player] <color=red>"
    
    findings = engine.review_entry(source, translated_bad)
    assert len(findings) == 1
    assert findings[0]["confidence"] == "SAFE"
    assert findings[0]["suggestion"] == "Xin chào\\nThế giới [Player] <color=red>"
    
    # 2. Likely Suggestion: Missing protected token in bad translation
    # If the translator completely missed [Player], fixing \n still happens, but it's not SAFE
    translated_worse = "Xin chào\\n Thế giới <color=red>"
    findings2 = engine.review_entry(source, translated_worse)
    assert len(findings2) == 1
    assert findings2[0]["confidence"] == "LIKELY"
