import json
from llm_utils import call_llm, extract_json

SYSTEM_PROMPT = """You are the Benchmark Reviewer Agent.
Analyze the IR-SIM benchmark report and return a strict JSON object with exactly these keys:
- issue: string
- likely_cause: string
- recommendation: string
- safety_passed: boolean
- goal_completion_passed: boolean
- efficiency_passed: boolean
- needs_revision: boolean

Return only JSON. Do not use markdown fences."""

REQUIRED_KEYS = [
    "issue", "likely_cause", "recommendation",
    "safety_passed", "goal_completion_passed",
    "efficiency_passed", "needs_revision",
]


def validate_benchmark_reviewer_output(output):
    if not isinstance(output, dict):
        raise ValueError("Output is not a JSON object")
    for key in REQUIRED_KEYS:
        if key not in output:
            raise ValueError(f"Missing key: {key}")
    for key in ["safety_passed", "goal_completion_passed", "efficiency_passed", "needs_revision"]:
        if not isinstance(output[key], bool):
            raise ValueError(f"{key} must be boolean")
    for key in ["issue", "likely_cause", "recommendation"]:
        if not isinstance(output[key], str):
            raise ValueError(f"{key} must be string")
    return output


def build_deterministic_review(benchmark_report):
    success_rate = float(benchmark_report.get("success_rate", 0.0))
    efficiency_rate = float(benchmark_report.get("efficiency_rate", 0.0))
    inefficient_success = int(benchmark_report.get("inefficient_success_worlds", 0))
    results = benchmark_report.get("results", [])

    unsafe = False
    for r in results:
        if r.get("collision_or_done") and not r.get("reached_goal"):
            unsafe = True
            break

    safety_passed = not unsafe
    goal_completion_passed = success_rate >= 1.0
    efficiency_passed = (inefficient_success == 0 and efficiency_rate >= 1.0)
    needs_revision = not (safety_passed and goal_completion_passed and efficiency_passed)

    issues = []
    if not safety_passed:
        issues.append("Unsafe benchmark behavior detected")
    if not goal_completion_passed:
        issues.append("Goal completion failure")
    if not efficiency_passed:
        issues.append("Successful but inefficient navigation")
    issue = "; ".join(issues) if issues else "No benchmark issue detected"

    if unsafe:
        likely_cause = "Collision or terminal condition before goal; obstacle avoidance insufficient"
        recommendation = "Strengthen obstacle detection and add STOP before collision"
    elif not goal_completion_passed:
        likely_cause = "Some worlds did not reach goal; possibly local deadlock or wrong turn priority"
        recommendation = "Review failed worlds, adjust turn and goal direction priority"
    elif not efficiency_passed:
        likely_cause = "Goal reached but too many steps, inefficient detours"
        recommendation = "Reduce unnecessary turns, prefer shortest safe direction"
    else:
        likely_cause = "All benchmark worlds passed"
        recommendation = "No revision needed"

    return {
        "issue": issue,
        "likely_cause": likely_cause,
        "recommendation": recommendation,
        "safety_passed": safety_passed,
        "goal_completion_passed": goal_completion_passed,
        "efficiency_passed": efficiency_passed,
        "needs_revision": needs_revision,
    }


def run_reviewer_benchmark_agent(benchmark_report):
    deterministic = build_deterministic_review(benchmark_report)
    user_prompt = f"""IR-SIM benchmark report:
{json.dumps(benchmark_report, indent=2, ensure_ascii=False)}

Deterministic baseline review:
{json.dumps(deterministic, indent=2, ensure_ascii=False)}
"""
    for _ in range(3):
        try:
            raw = call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.1, json_mode=True)
            output = validate_benchmark_reviewer_output(extract_json(raw))
            for key in ["safety_passed", "goal_completion_passed", "efficiency_passed", "needs_revision"]:
                output[key] = bool(deterministic[key])
            return output
        except Exception:
            continue
    return deterministic


run_reviewer_benchmark = run_reviewer_benchmark_agent