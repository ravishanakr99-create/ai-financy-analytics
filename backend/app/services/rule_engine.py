"""Config-driven eligibility rule engine."""

import json
from pathlib import Path

from app.models.schemas import RuleDecision

RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "eligibility_rules.json"


def _load_rules() -> list[dict]:
    with RULES_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("rules", [])


def evaluate_eligibility(extracted_data: dict) -> tuple[bool, list[RuleDecision]]:
    """
    Evaluate eligibility using externally editable JSON rules.
    Supported operators: >=, <=, >, <, ==.
    """
    decisions: list[RuleDecision] = []
    rules = _load_rules()
    all_passed = True

    for rule in rules:
        metric = rule["metric"]
        operator = rule["operator"]
        threshold = rule["value"]
        value = extracted_data.get(metric)
        passed = False

        if value is None:
            passed = False
            message = f"Metric {metric} missing in extracted data"
        elif operator == ">=":
            passed = value >= threshold
            message = f"{metric}={value} {'>=' if passed else '<'} {threshold}"
        elif operator == "<=":
            passed = value <= threshold
            message = f"{metric}={value} {'<=' if passed else '>'} {threshold}"
        elif operator == ">":
            passed = value > threshold
            message = f"{metric}={value} {'>' if passed else '<='} {threshold}"
        elif operator == "<":
            passed = value < threshold
            message = f"{metric}={value} {'<' if passed else '>='} {threshold}"
        elif operator == "==":
            passed = value == threshold
            message = f"{metric}={value} {'==' if passed else '!='} {threshold}"
        else:
            passed = False
            message = f"Unsupported operator: {operator}"

        decisions.append(
            RuleDecision(
                rule_id=rule["id"],
                rule_name=rule["name"],
                passed=passed,
                message=message,
                details={
                    "metric": metric,
                    "operator": operator,
                    "threshold": threshold,
                    "value": value,
                },
            )
        )
        all_passed = all_passed and passed

    return all_passed, decisions
