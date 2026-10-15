import json
from llm_utils import call_llm, extract_json

ALLOWED_ACTIONS = {"FORWARD", "LEFT", "RIGHT", "STOP"}

SYSTEM_PROMPT = """You are the Planner Agent for a robot navigation system.
Return only a JSON object. Do not include markdown.
The JSON must have:
- strategy: a non-empty string
- decisions: a non-empty list of objects, each with condition and action
- stop_condition: a non-empty string
Allowed actions are only: FORWARD, LEFT, RIGHT, STOP.
Keep the plan deterministic and safe."""


def validate_plan(data):
    if not isinstance(data, dict):
        raise TypeError("plan must be a dict")
    strategy = data.get("strategy")
    if not isinstance(strategy, str) or not strategy.strip():
        raise ValueError("strategy must be a non-empty string")
    decisions = data.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise ValueError("decisions must be a non-empty list")
    for i, item in enumerate(decisions):
        if not isinstance(item, dict):
            raise TypeError(f"decisions[{i}] must be a dict")
        if not isinstance(item.get("condition"), str) or not item["condition"].strip():
            raise ValueError(f"decisions[{i}].condition must be a non-empty string")
        if item.get("action") not in ALLOWED_ACTIONS:
            raise ValueError(f"decisions[{i}].action must be one of {sorted(ALLOWED_ACTIONS)}")
    stop_condition = data.get("stop_condition")
    if not isinstance(stop_condition, str) or not stop_condition.strip():
        raise ValueError("stop_condition must be a non-empty string")
    return data


def run_planner(requirements):
    user_prompt = json.dumps(requirements, ensure_ascii=False)
    last_error = None
    for _ in range(5):
        try:
            raw = call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.0, json_mode=True)
            plan = extract_json(raw)
            return validate_plan(plan)
        except Exception as e:
            last_error = e
    raise RuntimeError(f"Planner failed: {last_error}")


run_planner_agent = run_planner