import os
import json
import re


def call_llm(system_prompt, user_prompt, temperature=0.2, json_mode=False):
    try:
        return _call_ollama(system_prompt, user_prompt, temperature, json_mode)
    except Exception:
        pass
    try:
        return _call_openai(system_prompt, user_prompt, temperature)
    except Exception:
        pass
    return _mock_llm_response(system_prompt, user_prompt)


def _call_ollama(system_prompt, user_prompt, temperature, json_mode):
    from openai import OpenAI
    client = OpenAI(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key="ollama",
    )
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


def _call_openai(system_prompt, user_prompt, temperature):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("no openai key")
    from openai import OpenAI
    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content


def _mock_llm_response(system_prompt, user_prompt):
    if "Analyst" in system_prompt:
        return json.dumps({
            "goal": "Navigate the robot to the goal, avoiding obstacles and stopping safely.",
            "allowed_actions": ["FORWARD", "LEFT", "RIGHT", "STOP"],
            "safe_stop": True,
            "avoid_obstacles": True,
        })
    if "Planner" in system_prompt:
        return json.dumps({
            "strategy": "Goal-oriented obstacle avoidance",
            "decisions": [
                {"condition": "goal ahead and front clear", "action": "FORWARD"},
                {"condition": "front blocked and left clear", "action": "LEFT"},
                {"condition": "front blocked and left blocked and right clear", "action": "RIGHT"},
                {"condition": "all blocked", "action": "STOP"},
            ],
            "stop_condition": "no safe direction available",
        })
    if "Developer" in system_prompt:
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
    if "Test Agent" in system_prompt:
        return '''import pytest
from generated.navigation_logic import decide_next_move


def test_goal_ahead_clear():
    state = {"goal_ahead": True, "goal_on_left": False, "goal_on_right": False,
             "front_blocked": False, "left_blocked": False, "right_blocked": False}
    assert decide_next_move(state) == "FORWARD"


def test_front_blocked_left_clear():
    state = {"goal_ahead": True, "goal_on_left": False, "goal_on_right": False,
             "front_blocked": True, "left_blocked": False, "right_blocked": False}
    assert decide_next_move(state) == "LEFT"


def test_all_blocked():
    state = {"goal_ahead": False, "goal_on_left": False, "goal_on_right": False,
             "front_blocked": True, "left_blocked": True, "right_blocked": True}
    assert decide_next_move(state) == "STOP"


def test_goal_on_right():
    state = {"goal_ahead": False, "goal_on_left": False, "goal_on_right": True,
             "front_blocked": False, "left_blocked": False, "right_blocked": False}
    assert decide_next_move(state) in {"FORWARD", "RIGHT"}
'''
    if "Benchmark Reviewer" in system_prompt:
        return json.dumps({
            "issue": "No benchmark issue detected",
            "likely_cause": "All worlds passed",
            "recommendation": "No revision needed",
            "safety_passed": True,
            "goal_completion_passed": True,
            "efficiency_passed": True,
            "needs_revision": False,
        })
    if "Reviewer" in system_prompt:
        return json.dumps({
            "issue": "No simulation issue detected",
            "likely_cause": "All scenarios passed",
            "recommendation": "No revision needed",
            "needs_revision": False,
        })
    return "{}"


def strip_markdown_fences(text):
    text = text.strip()
    text = re.sub(r"^```(?:python|json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_json(text):
    text = strip_markdown_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise