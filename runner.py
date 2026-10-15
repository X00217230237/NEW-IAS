import json
import os
import itertools
import importlib

from generated.navigation_logic import decide_next_move


def _expected_move(state):
    if state["goal_ahead"] and not state["front_blocked"]:
        return "FORWARD"
    if state["goal_on_left"] and not state["left_blocked"]:
        return "LEFT"
    if state["goal_on_right"] and not state["right_blocked"]:
        return "RIGHT"
    if not state["front_blocked"]:
        return "FORWARD"
    if not state["left_blocked"]:
        return "LEFT"
    if not state["right_blocked"]:
        return "RIGHT"
    return "STOP"


def _build_scenarios():
    scenarios = []
    keys = ("goal_ahead", "goal_on_left", "goal_on_right",
            "front_blocked", "left_blocked", "right_blocked")
    for values in itertools.product([False, True], repeat=6):
        state = dict(zip(keys, values))
        scenarios.append({"state": state, "expected": _expected_move(state)})
    return scenarios


def run_simulation():
    scenarios = _build_scenarios()
    results = []
    passed = 0
    failed = 0
    for i, sc in enumerate(scenarios, 1):
        state = sc["state"]
        expected = sc["expected"]
        try:
            actual = decide_next_move(state)
            ok = actual == expected
        except Exception as e:
            actual = f"ERROR: {e}"
            ok = False
        if ok:
            passed += 1
        else:
            failed += 1
        results.append({
            "scenario_id": i,
            "state": state,
            "expected": expected,
            "actual": actual,
            "passed": ok,
        })
    total = len(scenarios)
    return {
        "total_scenarios": total,
        "passed": passed,
        "failed": failed,
        "success_rate": passed / total if total else 0.0,
        "results": results,
    }


def save_simulation_report(report=None, path="artifacts/simulation_report.json"):
    if report is None:
        report = run_simulation()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return path


if __name__ == "__main__":
    report = run_simulation()
    save_simulation_report(report)
    print(json.dumps(report, indent=2, ensure_ascii=False))