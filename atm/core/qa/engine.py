import re
from typing import Dict, List, Any
from atm.core.qa.registry import QARuleRegistry

class QAEngine:
    def __init__(self, registry: QARuleRegistry):
        self.registry = registry

    def extract_protected_tokens(self, text: str) -> List[str]:
        """Extract tokens that MUST be preserved."""
        tokens = []
        # \n
        tokens.extend(re.findall(r'\\n|\n', text))
        # [Player], [Var1]
        tokens.extend(re.findall(r'\[[^\]]+\]', text))
        # {0}, {1}
        tokens.extend(re.findall(r'\{\d+\}', text))
        # <color=#...>, </color>
        tokens.extend(re.findall(r'<[^>]+>', text))
        # \c[1], \v[1] - RPG Maker style
        tokens.extend(re.findall(r'\\[a-zA-Z]\[\d+\]', text))
        return sorted(tokens)

    def is_token_invariant_preserved(self, source: str, suggestion: str) -> bool:
        """Ensure all protected tokens in source exist exactly in suggestion."""
        src_tokens = self.extract_protected_tokens(source)
        sug_tokens = self.extract_protected_tokens(suggestion)
        return src_tokens == sug_tokens

    def review_entry(self, source_text: str, translated_text: str) -> List[Dict[str, Any]]:
        findings = []
        rules = self.registry.get_active_rules()
        
        for rule in rules:
            try:
                pattern = re.compile(rule.pattern)
            except re.error:
                continue

            if rule.type == 'regex_match':
                if pattern.search(translated_text):
                    findings.append({
                        "rule_id": rule.rule_id,
                        "source": rule.source,
                        "severity": rule.severity,
                        "confidence": "AMBIGUOUS",
                        "message": f"Matches forbidden pattern.",
                        "suggestion": None
                    })
            elif rule.type == 'regex_replace':
                if pattern.search(translated_text):
                    suggestion = pattern.sub(rule.replacement or "", translated_text)
                    if suggestion != translated_text:
                        # Check Token Invariant
                        is_safe = self.is_token_invariant_preserved(source_text, suggestion)
                        confidence = "SAFE" if is_safe else "LIKELY"
                        findings.append({
                            "rule_id": rule.rule_id,
                            "source": rule.source,
                            "severity": rule.severity,
                            "confidence": confidence,
                            "message": "Suggested format fix available.",
                            "suggestion": suggestion
                        })
        return findings

    def review_batch(self, entries: List[Dict[str, str]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        entries = [{"id": "xyz", "source": "...", "translated": "..."}, ...]
        Returns { "xyz": [findings] }
        """
        results = {}
        for entry in entries:
            f = self.review_entry(entry["source"], entry["translated"])
            if f:
                results[entry["id"]] = f
        return results
