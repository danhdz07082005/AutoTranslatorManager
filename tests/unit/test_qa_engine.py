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


def test_qa_auto_seed_and_defaults(tmp_path: Path):
    seed_file = tmp_path / "seeded_rules.json"
    assert not seed_file.exists()
    
    registry = QARuleRegistry(str(seed_file), str(tmp_path / "user.json"))
    assert seed_file.exists(), "system_rules.json phải được tự động tạo (auto-seeded)"
    
    active_rules = registry.get_active_rules()
    rule_ids = {r.rule_id for r in active_rules}
    assert "empty_translation" in rule_ids
    assert "broken_rpg_maker_var" in rule_ids
    assert "unclosed_html_color" in rule_ids
    assert "consecutive_spaces" in rule_ids


def test_api_review_qa_flow():
    from atm.ui.api import BackendApi
    api = BackendApi()
    
    entries = [
        {"id": "1", "source": "Hello", "translated": ""},
        {"id": "2", "source": "Get item \\v[1]", "translated": "Nhận được \\v[]"},
        {"id": "3", "source": "<color=red>Fire</color>", "translated": "<color=red>Lửa"},
        {"id": "4", "source": "Good  morning", "translated": "Chào  buổi sáng"},
        {"id": "5", "source": "Safe sentence", "translated": "Câu chuẩn không lỗi"},
        {"id": "6", "source": "Untranslated row", "translated": None}, # None handling test
        {"id": "7", "source": "Multiline Tag", "translated": "<color=red>Line 1\nLine 2</color>"} # Multiline DOTALL test
    ]
    
    res = api.review_qa(entries)
    assert res["status"] == "success"
    data = res["data"]
    
    # 1: empty_translation with Vietnamese message from description
    assert "1" in data
    empty_f = [f for f in data["1"] if f["rule_id"] == "empty_translation"]
    assert len(empty_f) > 0
    assert empty_f[0]["message"] == "Bản dịch bị bỏ trống"
    
    # 2: broken_rpg_maker_var
    assert "2" in data
    assert any(f["rule_id"] == "broken_rpg_maker_var" for f in data["2"])
    
    # 3: unclosed_html_color
    assert "3" in data
    assert any(f["rule_id"] == "unclosed_html_color" for f in data["3"])
    
    # 4: consecutive_spaces
    assert "4" in data
    assert any(f["rule_id"] == "consecutive_spaces" for f in data["4"])
    
    # 5: No findings
    assert "5" not in data

    # 6: None translated properly flagged as empty_translation without crashing
    assert "6" in data
    assert any(f["rule_id"] == "empty_translation" for f in data["6"])

    # 7: Multiline tag correctly matched without false positive unclosed error
    assert "7" not in data

    # 8: Invalid payload check
    invalid_res = api.review_qa("not a list")
    assert invalid_res["status"] == "error"


