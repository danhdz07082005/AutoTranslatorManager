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

class QARuleRegistry:
    def __init__(self, system_rules_path: str, user_rules_path: str):
        self.system_rules_path = Path(system_rules_path)
        self.user_rules_path = Path(user_rules_path)
        self.rules: Dict[str, QARule] = {}
        self._load_rules()

    def _load_rules(self):
        """Nạp rules từ system (immutable) và overlay user (mutable)."""
        self.rules.clear()
        
        # Load system rules
        if self.system_rules_path.exists():
            try:
                with self.system_rules_path.open('r', encoding='utf-8') as f:
                    sys_data = json.load(f)
                    for item in sys_data.get('rules', []):
                        rule = QARule(
                            schema_version=item.get('schema_version', 1),
                            rule_id=item['rule_id'],
                            type=item['type'],
                            severity=item['severity'],
                            pattern=item['pattern'],
                            replacement=item.get('replacement'),
                            enabled=item.get('enabled', True),
                            source='system'
                        )
                        if rule.is_safe_regex():
                            self.rules[rule.rule_id] = rule
                        else:
                            logger.error(f"System rule {rule.rule_id} rejected due to unsafe regex.")
            except Exception as e:
                logger.error(f"Failed to load system rules: {e}")

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
