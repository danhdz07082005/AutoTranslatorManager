import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from atm.utils.logger import get_logger

logger = get_logger(__name__, "qa_registry.log")

@dataclass
class QARule:
    schema_version: int
    rule_id: str
    type: str # 'regex_match' or 'regex_replace'
    severity: str # 'error' or 'warning'
    pattern: str
    replacement: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    source: str = 'system' # 'system' or 'user'

    def is_safe_regex(self) -> bool:
        """Kiểm tra nguy cơ Catastrophic Backtracking tĩnh."""
        try:
            re.compile(self.pattern)
        except re.error:
            return False
        
        # Simple heuristic to detect nested quantifiers like (a+)+ or (.*)*
        # This is a basic static check for standard ReDoS.
        dangerous_patterns = [
            r'(\(.*[\+\*].*\)[\+\*])', # (A+)+ or (A*)*
            r'([\+\*]{2,})' # ++ or **
        ]
        for dp in dangerous_patterns:
            if re.search(dp, self.pattern):
                return False
        return True

DEFAULT_SYSTEM_RULES = {
    "version": 1,
    "rules": [
        {
            "schema_version": 1,
            "rule_id": "empty_translation",
            "type": "regex_match",
            "severity": "error",
            "pattern": r"^\s*$",
            "description": "Bản dịch bị bỏ trống",
            "enabled": True
        },
        {
            "schema_version": 1,
            "rule_id": "newline_space",
            "type": "regex_replace",
            "severity": "warning",
            "pattern": r"\\n\s+",
            "replacement": r"\\n",
            "description": "Thừa khoảng trắng sau ký tự xuống dòng \\n",
            "enabled": True
        },
        {
            "schema_version": 1,
            "rule_id": "space_before_newline",
            "type": "regex_replace",
            "severity": "warning",
            "pattern": r"\s+\\n",
            "replacement": r"\\n",
            "description": "Thừa khoảng trắng trước ký tự xuống dòng \\n",
            "enabled": True
        },
        {
            "schema_version": 1,
            "rule_id": "broken_rpg_maker_var",
            "type": "regex_match",
            "severity": "error",
            "pattern": r"\\[vVcCgGnN]\[\s*\]",
            "description": "Mã điều khiển RPG Maker bị rỗng ruột (ví dụ \\v[], \\c[])",
            "enabled": True
        },
        {
            "schema_version": 1,
            "rule_id": "unclosed_html_color",
            "type": "regex_match",
            "severity": "error",
            "pattern": r"(?s)<color=[^>]+>(?!.*</color>)",
            "description": "Thẻ <color> chưa được đóng thẻ </color>",
            "enabled": True
        },
        {
            "schema_version": 1,
            "rule_id": "unopened_html_color",
            "type": "regex_match",
            "severity": "error",
            "pattern": r"(?s)^(?!.*<color=[^>]+>).*</color>",
            "description": "Thẻ đóng </color> không có thẻ mở tương ứng",
            "enabled": True
        },
        {
            "schema_version": 1,
            "rule_id": "unclosed_bbcode_b",
            "type": "regex_match",
            "severity": "error",
            "pattern": r"(?s)<b>(?!.*</b>)",
            "description": "Thẻ <b> chưa được đóng thẻ </b>",
            "enabled": True
        },
        {
            "schema_version": 1,
            "rule_id": "unclosed_curly_brace",
            "type": "regex_match",
            "severity": "error",
            "pattern": r"\{[0-9]+(?![0-9]*\})",
            "description": "Biến placeholder {n} bị vỡ ngoặc nhọn",
            "enabled": True
        },
        {
            "schema_version": 1,
            "rule_id": "consecutive_spaces",
            "type": "regex_replace",
            "severity": "warning",
            "pattern": r"[^\S\r\n]{2,}",
            "replacement": " ",
            "description": "Lặp liên tiếp nhiều khoảng trắng",
            "enabled": True
        }
    ]
}

class QARuleRegistry:
    def __init__(self, system_rules_path: str, user_rules_path: str, auto_seed: bool = True):
        self.system_rules_path = Path(system_rules_path)
        self.user_rules_path = Path(user_rules_path)
        self.rules: Dict[str, QARule] = {}
        if auto_seed and not self.system_rules_path.exists():
            self._seed_system_rules()
        self._load_rules()

    def _seed_system_rules(self):
        """Tự động tạo tệp system_rules.json với các quy tắc mặc định nếu chưa tồn tại."""
        try:
            self.system_rules_path.parent.mkdir(parents=True, exist_ok=True)
            with self.system_rules_path.open('w', encoding='utf-8') as f:
                json.dump(DEFAULT_SYSTEM_RULES, f, ensure_ascii=False, indent=2)
            logger.info(f"Auto-seeded default QA system rules at {self.system_rules_path}")
        except Exception as e:
            logger.warning(f"Could not write system_rules.json to disk: {e}. Fallback to memory.")

    def _load_rules(self):
        """Nạp rules từ system (immutable) và overlay user (mutable)."""
        self.rules.clear()
        
        # Load system rules
        sys_data = None
        if self.system_rules_path.exists():
            try:
                with self.system_rules_path.open('r', encoding='utf-8') as f:
                    sys_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load system rules from disk: {e}")
        
        # Fallback to built-in defaults in RAM if file missing or corrupted
        if not sys_data or not sys_data.get('rules'):
            sys_data = DEFAULT_SYSTEM_RULES

        try:
            for item in sys_data.get('rules', []):
                rule = QARule(
                    schema_version=item.get('schema_version', 1),
                    rule_id=item['rule_id'],
                    type=item['type'],
                    severity=item['severity'],
                    pattern=item['pattern'],
                    replacement=item.get('replacement'),
                    description=item.get('description'),
                    enabled=item.get('enabled', True),
                    source='system'
                )
                if rule.is_safe_regex():
                    self.rules[rule.rule_id] = rule
                else:
                    logger.error(f"System rule {rule.rule_id} rejected due to unsafe regex.")
        except Exception as e:
            logger.error(f"Corrupted system rules list on disk, falling back to built-in defaults: {e}")
            for item in DEFAULT_SYSTEM_RULES['rules']:
                rule = QARule(
                    schema_version=item.get('schema_version', 1),
                    rule_id=item['rule_id'],
                    type=item['type'],
                    severity=item['severity'],
                    pattern=item['pattern'],
                    replacement=item.get('replacement'),
                    description=item.get('description'),
                    enabled=item.get('enabled', True),
                    source='system'
                )
                if rule.is_safe_regex():
                    self.rules[rule.rule_id] = rule

        # Load user rules
        if self.user_rules_path.exists():
            try:
                with self.user_rules_path.open('r', encoding='utf-8') as f:
                    usr_data = json.load(f)
                    for item in usr_data.get('rules', []):
                        rule_id = item['rule_id']
                        if rule_id in self.rules:
                            # User only overrides enabled & severity for existing system rules
                            self.rules[rule_id].enabled = item.get('enabled', self.rules[rule_id].enabled)
                            self.rules[rule_id].severity = item.get('severity', self.rules[rule_id].severity)
                            self.rules[rule_id].source = 'user_override' # explicitly mark
                        else:
                            # Or user created a brand new custom rule
                            rule = QARule(
                                schema_version=item.get('schema_version', 1),
                                rule_id=rule_id,
                                type=item['type'],
                                severity=item['severity'],
                                pattern=item['pattern'],
                                replacement=item.get('replacement'),
                                description=item.get('description'),
                                enabled=item.get('enabled', True),
                                source='user'
                            )
                            if rule.is_safe_regex():
                                self.rules[rule_id] = rule
                            else:
                                logger.error(f"User rule {rule_id} rejected due to unsafe regex.")
            except Exception as e:
                logger.error(f"Failed to load user rules: {e}")

    def get_active_rules(self) -> List[QARule]:
        return [r for r in self.rules.values() if r.enabled]
