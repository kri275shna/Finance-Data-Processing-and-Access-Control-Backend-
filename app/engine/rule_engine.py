from typing import Dict, Any, List

def _evaluate_condition(condition: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    """
    Evaluates a single condition like:
    {"field": "income", "operator": "<", "value": 20000}
    """
    field = condition.get("field")
    operator = condition.get("operator")
    target_value = condition.get("value")

    if not field or not operator:
        return False

    # Get nested value from payload if field is like "user.income"
    actual_value = payload
    for key in field.split("."):
        if isinstance(actual_value, dict) and key in actual_value:
            actual_value = actual_value[key]
        else:
            actual_value = None
            break

    if actual_value is None:
        return False # or maybe handle depending on operator, e.g. "is_null"

    if operator == "==":
        return actual_value == target_value
    elif operator == "!=":
        return actual_value != target_value
    elif operator == ">":
        return actual_value > target_value
    elif operator == ">=":
        return actual_value >= target_value
    elif operator == "<":
        return actual_value < target_value
    elif operator == "<=":
        return actual_value <= target_value
    elif operator == "IN":
        return actual_value in target_value
    elif operator == "NOT_IN":
        return actual_value not in target_value
    elif operator == "CONTAINS":
        # Check if target_value is inside actual_value (e.g. array or string)
        try:
            return target_value in actual_value
        except TypeError:
            return False

    return False

def evaluate_rules(conditions: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    """
    Evaluates a ruleset which might be nested:
    {"AND": [{"field":...}, {"OR": [...]}]}
    Or a simple single rule:
    {"field": "income", "operator": "<", "value": 20000}
    """
    if "AND" in conditions:
        return all(evaluate_rules(cond, payload) for cond in conditions["AND"])
    if "OR" in conditions:
        return any(evaluate_rules(cond, payload) for cond in conditions["OR"])
    
    # It must be a single condition
    return _evaluate_condition(conditions, payload)
