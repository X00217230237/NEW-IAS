import json
from llm_utils import call_llm, strip_markdown_fences

SYSTEM_PROMPT = """You are the Test Agent.
Generate a complete pytest test file for decide_next_move(state).

Import as:
from generated.navigation_logic import decide_next_move

state is a dict with boolean keys:
front_blocked, left_blocked, right_blocked, goal_ahead, goal_on_left, goal_on_right.

decide_next_move returns one of: FORWARD, LEFT, RIGHT, STOP.

Cover:
- clear forward
- front blocked
- left blocked
- right blocked
- all blocked
- goal on left
- goal on right
- goal ahead
Use pytest style, function names starting with test_, use assert.
Return only Python code. Do not use markdown fences."""

REQUIRED_KEYWORDS = ["import", "decide_next_move", "def test_", "assert"]


def _fallback_tests():
    return '''import pytest
from generated.navigation_logic import decide_next_move


def test_forward_when_clear_and_goal_ahead():
    state = {"front_blocked": False, "left_blocked": False, "right_blocked": False,
             "goal_ahead": True, "goal_on_left": False, "goal_on_right": False}
    assert decide_next_move(state) == "FORWARD"


def test_turn_left_when_front_blocked_and_left_clear():
    state = {"front_blocked": True, "left_blocked": False, "right_blocked": False,
             "goal_ahead": True, "goal_on_left": False, "goal_on_right": False}
    assert decide_next_move(state) == "LEFT"


def test_turn_right_when_front_and_left_blocked():
    state = {"front_blocked": True, "left_blocked": True, "right_blocked": False,
             "goal_ahead": True, "goal_on_left": False, "goal_on_right": False}
    assert decide_next_move(state) == "RIGHT"


def test_stop_when_all_blocked():
    state = {"front_blocked": True, "left_blocked": True, "right_blocked": True,
             "goal_ahead": False, "goal_on_left": False, "goal_on_right": False}
    assert decide_next_move(state) == "STOP"


def test_goal_on_left():
    state = {"front_blocked": False, "left_blocked": False, "right_blocked": False,
             "goal_ahead": False, "goal_on_left": True, "goal_on_right": False}
    assert decide_next_move(state) == "LEFT"


def test_goal_on_right():
    state = {"front_blocked": False, "left_blocked": False, "right_blocked": False,
             "goal_ahead": False, "goal_on_left": False, "goal_on_right": True}
    assert decide_next_move(state) == "RIGHT"
'''


def validate_test_code(code):
    if not isinstance(code, str) or not code.strip():
        raise ValueError("empty test code")
    if "```" in code:
        raise ValueError("markdown fence found")
    missing = [k for k in REQUIRED_KEYWORDS if k not in code]
    if missing:
        raise ValueError(f"missing keywords: {missing}")
    compile(code, "<generated_test>", "exec")
    return code


def run_test_agent(requirements, plan):
    user_prompt = f"""Requirements:
{json.dumps(requirements, indent=2, ensure_ascii=False)}

Plan:
{json.dumps(plan, indent=2, ensure_ascii=False)}
"""
    for _ in range(5):
        try:
            raw = call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.1)
            return validate_test_code(strip_markdown_fences(raw))
        except Exception:
            continue
    return validate_test_code(_fallback_tests())