"""
Knostik rule engine - pattern matching and enrichment

Reference: US4 (Multi-layer correlation), T056
"""

import logging
import re
from typing import Dict, Any, List, Optional

import yaml

logger = logging.getLogger(__name__)


class Rule:
    """Represents a detection rule"""

    def __init__(self, rule_data: Dict[str, Any]):
        self.id = rule_data.get("id")
        self.name = rule_data.get("name")
        self.description = rule_data.get("description")
        self.severity = rule_data.get("severity", "medium")
        self.tags = rule_data.get("tags", [])
        self.conditions = rule_data.get("conditions", [])
        self.enrichment = rule_data.get("enrichment", {})

    def matches(self, event: Dict[str, Any]) -> bool:
        """Check if event matches this rule's conditions"""
        for condition in self.conditions:
            if not self._evaluate_condition(condition, event):
                return False
        return True

    def _evaluate_condition(self, condition: Dict[str, Any], event: Dict[str, Any]) -> bool:
        """Evaluate a single condition against the event"""
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")

        # Navigate to field in event (supports nested paths like "evidence.port")
        event_value = self._get_nested_value(event, field)

        if event_value is None:
            return False

        # Evaluate based on operator
        if operator == "equals":
            return event_value == value
        elif operator == "not_equals":
            return event_value != value
        elif operator == "contains":
            return value in str(event_value)
        elif operator == "regex":
            return re.search(value, str(event_value)) is not None
        elif operator == "in":
            return event_value in value
        elif operator == "gt":
            return event_value > value
        elif operator == "lt":
            return event_value < value
        elif operator == "gte":
            return event_value >= value
        elif operator == "lte":
            return event_value <= value
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False

    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get value from nested dict using dot notation"""
        keys = path.split(".")
        value = obj
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def enrich(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Apply enrichment to the event"""
        enriched = event.copy()

        # Add rule metadata
        if "matched_rules" not in enriched:
            enriched["matched_rules"] = []

        enriched["matched_rules"].append({
            "rule_id": self.id,
            "rule_name": self.name,
            "severity": self.severity,
            "tags": self.tags,
        })

        # Apply custom enrichment fields
        for key, value in self.enrichment.items():
            enriched[key] = value

        return enriched


class RuleEngine:
    """Rule engine for pattern matching and event enrichment"""

    def __init__(self, rules_file: Optional[str] = None):
        self.rules: List[Rule] = []
        if rules_file:
            self.load_rules(rules_file)

    def load_rules(self, rules_file: str) -> None:
        """Load rules from YAML file"""
        try:
            with open(rules_file, 'r') as f:
                rules_data = yaml.safe_load(f)

            self.rules = []
            for rule_data in rules_data.get("rules", []):
                rule = Rule(rule_data)
                self.rules.append(rule)

            logger.info(f"Loaded {len(self.rules)} rules from {rules_file}")

        except Exception as e:
            logger.error(f"Failed to load rules from {rules_file}: {e}")
            raise

    def apply_rules(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply all matching rules to the event.

        Returns enriched event with matched rule metadata.
        """
        enriched = event.copy()

        # Match against all rules
        matched_rules = []
        for rule in self.rules:
            if rule.matches(event):
                matched_rules.append(rule)
                logger.debug(f"Event matched rule: {rule.id} - {rule.name}")

        # Apply enrichments from all matched rules
        for rule in matched_rules:
            enriched = rule.enrich(enriched)

        # Add summary metadata
        if matched_rules:
            enriched["enrichment_applied"] = True
            enriched["matched_rule_count"] = len(matched_rules)
        else:
            enriched["enrichment_applied"] = False
            enriched["matched_rule_count"] = 0

        return enriched

    def get_rule_by_id(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID"""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    def reload_rules(self, rules_file: str) -> None:
        """Reload rules from file (useful for hot-reloading)"""
        self.load_rules(rules_file)
        logger.info("Rules reloaded successfully")
