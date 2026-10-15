from llm_utils import call_llm, extract_json

SYSTEM_PROMPT = """You are an Analyst Agent. Read the brief and output ONLY one valid JSON object.
No markdown, no extra text.
The JSON must have exactly these keys:
"goal": string,
"allowed_actions": ["FORWARD", "LEFT", "RIGHT", "STOP"],
"safe_stop": boolean,
"avoid_obstacles": boolean
Rules:
- allowed_actions must be exactly ["FORWARD", "LEFT", "RIGHT", "STOP"].
- safe_stop is true if the robot must stop when no safe direction exists.
- avoid_obstacles is true if the robot must never move into a blocked direction.
- Do not add extra keys."""


def validate_requirements(data):
    if not isinstance(data, dict):
        return False
    if set(data.keys()) != {"goal", "allowed_actions", "safe_stop", "avoid_obstacles"}:
        return False
    if not isinstance(data["goal"], str) or not data["goal"].strip():
        return False
    if data["allowed_actions"] != ["FORWARD", "LEFT", "RIGHT", "STOP"]:
        return False
    if not isinstance(data["safe_stop"], bool):
        return False
    if not isinstance(data["avoid_obstacles"], bool):
        return False
    return True


def run_analyst(brief_text):
    user_prompt = f"Brief:\n{brief_text}\n\nReturn only the required JSON."
    last_error = None
    for _ in range(5):
        try:
            raw = call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.0, json_mode=True)
            data = extract_json(raw)
            if validate_requirements(data):
                return data
            last_error = ValueError(f"Invalid data structure: {data}")
        except Exception as e:
            last_error = e
    raise RuntimeError(f"Analyst failed: {last_error}")


run_analyst_agent = run_analyst