import json
import os
from llm_utils import call_llm, strip_markdown_fences

SYSTEM_PROMPT = """You are the Developer Agent for a robot navigation system.
Return only Python code. Do not include markdown fences.
The code must define a function named decide_next_move(state).
The function must return exactly one of: FORWARD, LEFT, RIGHT, STOP.
The state is a dict with boolean keys:
front_blocked, left_blocked, right_blocked, goal_ahead, goal_on_left, goal_on_right.
Do not use external libraries. Do not access files or network."""

REVISION_SYSTEM_PROMPT = """You are the Developer Agent performing a revision.
You receive the original navigation code, review notes, benchmark report, requirements, and plan.
Return only Python code. Do not include markdown fences.
The code must define decide_next_move(state) returning one of: FORWARD, LEFT, RIGHT, STOP.
state is a dict with boolean keys:
front_blocked, left_blocked, right_blocked, goal_ahead, goal_on_left, goal_on_right."""


def _fallback_code():
    return '''def decide_next_move(state):
    if state.get("goal_ahead") and not state.get("front_blocked"):
        return "FORWARD"
    if state.get("goal_on_left") and not state.get("left_blocked"):
        return "LEFT"
    if state.get("goal_on_right") and not state.get("right_blocked"):
        return "RIGHT"
    if not state.get("front_blocked"):
        return "FORWARD"
    if not state.get("left_blocked"):
        return "LEFT"
    if not state.get("right_blocked"):
        return "RIGHT"
    return "STOP"
'''


def validate_code(code):
    if not isinstance(code, str):
        raise TypeError("code must be a string")
    code = strip_markdown_fences(code)
    if not code:
        raise ValueError("code must not be empty")
    if "def decide_next_move" not in code:
        raise ValueError("code must define decide_next_move(state)")
    compile(code, "navigation_logic.py", "exec")
    return code


def run_developer(plan):
    user_prompt = json.dumps(plan, ensure_ascii=False)
    for _ in range(5):
        try:
            raw = call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.2)
            return validate_code(raw)
        except Exception:
            continue
    return _fallback_code()


def run_developer_revision(
    original_navigation_code,
    review_notes,
    benchmark_report,
    requirements,
    plan,
    output_path="generated/navigation_logic_revised.py",
):
    user_prompt = f"""Original navigation code:
{original_navigation_code}

Review notes:
{json.dumps(review_notes, indent=2, ensure_ascii=False)}

Benchmark report:
{json.dumps(benchmark_report, indent=2, ensure_ascii=False)}

Requirements:
{json.dumps(requirements, indent=2, ensure_ascii=False)}

Plan:
{json.dumps(plan, indent=2, ensure_ascii=False)}
"""
    code = None
    for _ in range(5):
        try:
            raw = call_llm(REVISION_SYSTEM_PROMPT, user_prompt, temperature=0.2)
            code = validate_code(raw)
            break
        except Exception:
            continue
    if code is None:
        code = original_navigation_code
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)
    return output_path


run_developer_agent = run_developer