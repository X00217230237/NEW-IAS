import json
from llm_utils import call_llm, extract_json

SYSTEM_PROMPT = """You are the Reviewer Agent.
Analyze the simulation report and return a strict JSON object with exactly these keys:
- issue: string
- likely_cause: string
- recommendation: string
- needs_revision: boolean

Return only JSON. Do not use markdown fences."""

REQUIRED_KEYS = ["issue", "likely_cause", "recommendation", "needs_revision"]


def validate_reviewer_output(output):
    if not isinstance(output, dict):
        raise ValueError("Reviewer output is not a JSON object")
    for key in REQUIRED_KEYS:
        if key not in output:
            raise ValueError(f"Missing key: {key}")
    if not isinstance(output["needs_revision"], bool):
        raise ValueError("needs_revision must be boolean")
    for key in ["issue", "likely_cause", "recommendation"]:
        if not isinstance(output[key], str):
            raise ValueError(f"{key} must be string")
    return output


def _deterministic_review(simulation_report):
    failed = int(simulation_report.get("failed", 0))
    success_rate = float(simulation_report.get("success_rate", 0.0))
    if failed > 0 or success_rate < 1.0:
        return {
            "issue": f"Simulation has {failed} failed scenario(s), success_rate={success_rate:.2f}",
            "likely_cause": "decide_next_move has incorrect or missing logic for some state combinations",
            "recommendation": "Inspect failed scenarios in simulation_report.json, revise navigation logic, re-run",
            "needs_revision": True,
        }
    return {
        "issue": "No simulation issue detected",
        "likely_cause": "All scenarios passed",
        "recommendation": "Continue to IR-SIM benchmark",
        "needs_revision": False,
    }


def run_reviewer_agent(simulation_report):
    deterministic = _deterministic_review(simulation_report)
    user_prompt = f"""Simulation report:
{json.dumps(simulation_report, indent=2, ensure_ascii=False)}

Deterministic baseline review:
{json.dumps(deterministic, indent=2, ensure_ascii=False)}
"""
    for _ in range(3):
        try:
            raw = call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.1, json_mode=True)
            output = validate_reviewer_output(extract_json(raw))
            output["needs_revision"] = bool(deterministic["needs_revision"] or output["needs_revision"])
            return output
        except Exception:
            continue
    return deterministic


run_reviewer = run_reviewer_agent