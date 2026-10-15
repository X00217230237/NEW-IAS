import json
import os
import subprocess
import sys
import logging
import shutil
import importlib


def load_brief():
    for p in ["brief.txt", "artifacts/brief.txt"]:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
    return "Navigate robot to goal, avoid obstacles, stop safely."


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_agent(module_name, func_names, *args, **kwargs):
    mod = importlib.import_module(module_name)
    for name in func_names:
        if hasattr(mod, name):
            return getattr(mod, name)(*args, **kwargs)
    raise AttributeError(f"{module_name} has none of {func_names}")


def ensure_navigation_logic(dev_result):
    os.makedirs("generated", exist_ok=True)
    os.makedirs("generated", exist_ok=True)
    open("generated/__init__.py", "a").close()
    target = "generated/navigation_logic.py"
    if isinstance(dev_result, str):
        if dev_result.endswith(".py") and os.path.exists(dev_result):
            if os.path.abspath(dev_result) != os.path.abspath(target):
                shutil.copyfile(dev_result, target)
            return target
        if "def decide_next_move" in dev_result:
            with open(target, "w", encoding="utf-8") as f:
                f.write(dev_result)
            return target
    if not os.path.exists(target):
        raise FileNotFoundError(f"missing {target}")
    return target


def run_pipeline_once():
    logging.info("pipeline start")
    brief = load_brief()
    logging.info("brief loaded")

    requirements = run_agent("analyst_agent", ["run_analyst", "run_analyst_agent"], brief)
    save_json("artifacts/requirements.json", requirements)
    logging.info("Analyst Agent created requirements.json")

    plan = run_agent("planner_agent", ["run_planner", "run_planner_agent"], requirements)
    save_json("artifacts/plan.json", plan)
    logging.info("Planner Agent created plan.json")

    dev_result = run_agent("developer_agent", ["run_developer", "run_developer_agent"], plan)
    ensure_navigation_logic(dev_result)
    logging.info("Developer Agent created generated/navigation_logic.py")

    test_code = run_agent("test_agent", ["run_test_agent"], requirements, plan)
    os.makedirs("tests", exist_ok=True)
    with open("tests/test_navigation_logic.py", "w", encoding="utf-8") as f:
        f.write(test_code)
    logging.info("Test Agent created tests/test_navigation_logic.py")

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_navigation_logic.py", "-q"],
        capture_output=True, text=True,
    )
    logging.info(f"pytest rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}")

    sim_report = run_agent("runner", ["run_simulation"])
    save_json("artifacts/simulation_report.json", sim_report)
    logging.info("Simulation Runner created simulation_report.json")

    review = run_agent("reviewer_agent", ["run_reviewer_agent", "run_reviewer"], sim_report)
    save_json("artifacts/reviewer_report.json", review)
    logging.info("Reviewer Agent created reviewer_report.json")

    bench_report = run_agent("benchmark_irsim", ["run_benchmark"])
    save_json("artifacts/irsim_benchmark_report.json", bench_report)
    logging.info("IR-SIM benchmark created irsim_benchmark_report.json")

    bench_review = run_agent(
        "reviewer_benchmark_agent",
        ["run_reviewer_benchmark_agent", "run_reviewer_benchmark"],
        bench_report,
    )
    save_json("artifacts/benchmark_review_report.json", bench_review)
    logging.info("Benchmark Reviewer created benchmark_review_report.json")

    return {
        "requirements": requirements,
        "plan": plan,
        "sim_report": sim_report,
        "review": review,
        "bench_report": bench_report,
        "bench_review": bench_review,
    }


def main():
    os.makedirs("artifacts", exist_ok=True)
    os.makedirs("generated", exist_ok=True)
    os.makedirs("tests", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("trace.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logging.info("========== Pipeline start ==========")
    result = run_pipeline_once()
    review = result["review"]
    bench_review = result["bench_review"]

    if review.get("needs_revision") or bench_review.get("needs_revision"):
        logging.info("revision triggered")
        with open("generated/navigation_logic.py", "r", encoding="utf-8") as f:
            original_code = f.read()
        new_path = run_agent(
            "developer_agent",
            ["run_developer_revision"],
            original_code,
            review,
            result["bench_report"],
            result["requirements"],
            result["plan"],
        )
        logging.info(f"revision saved to {new_path}")
        shutil.copyfile(new_path, "generated/navigation_logic.py")

        test_code = run_agent("test_agent", ["run_test_agent"], result["requirements"], result["plan"])
        with open("tests/test_navigation_logic.py", "w", encoding="utf-8") as f:
            f.write(test_code)

        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_navigation_logic.py", "-q"],
            capture_output=True, text=True,
        )
        logging.info(f"pytest after revision rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}")

        sim_report = run_agent("runner", ["run_simulation"])
        save_json("artifacts/simulation_report.json", sim_report)

        review = run_agent("reviewer_agent", ["run_reviewer_agent", "run_reviewer"], sim_report)
        save_json("artifacts/reviewer_report.json", review)

        bench_report = run_agent("benchmark_irsim", ["run_benchmark"])
        save_json("artifacts/irsim_benchmark_report.json", bench_report)

        bench_review = run_agent(
            "reviewer_benchmark_agent",
            ["run_reviewer_benchmark_agent", "run_reviewer_benchmark"],
            bench_report,
        )
        save_json("artifacts/benchmark_review_report.json", bench_review)
        logging.info("post-revision pipeline finished")
    else:
        logging.info("no revision needed")
    logging.info("========== Pipeline finished ==========")


if __name__ == "__main__":
    main()