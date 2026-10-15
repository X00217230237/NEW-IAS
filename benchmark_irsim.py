import json
import os
import subprocess
import ast
import sys
import glob


def _extract_report(output):
    marker = "IR-SIM report:"
    if marker not in output:
        return None
    after = output.split(marker, 1)[1].strip()
    for line in after.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return ast.literal_eval(line)
            except Exception:
                pass
    return None


def run_irsim_benchmark(world_file):
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    cmd = [sys.executable, "test_irsim_with_agent.py", world_file]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    report = _extract_report(output)
    if report is None:
        rp = "artifacts/irsim_report.json"
        if os.path.exists(rp):
            with open(rp, "r", encoding="utf-8") as f:
                report = json.load(f)
    if report is None:
        raise RuntimeError(f"Cannot extract IR-SIM report for {world_file}\n{output[-3000:]}")
    report["world_file"] = world_file
    report["returncode"] = proc.returncode
    return report


def _get_world_files():
    candidates = [
        "irsim_worlds/world_easy.yaml",
        "irsim_worlds/world_medium.yaml",
        "irsim_worlds/world_difficult.yaml",
        "irsim_worlds/world_hard.yaml",
        "irsim_worlds/world_custom.yaml",
    ]
    files = [p for p in candidates if os.path.exists(p)]
    if not files:
        files = sorted(glob.glob("irsim_worlds/*.yaml"))
    return files


def run_benchmark():
    os.makedirs("artifacts", exist_ok=True)
    world_files = _get_world_files()
    results = []
    for wf in world_files:
        try:
            rep = run_irsim_benchmark(wf)
        except Exception as e:
            rep = {
                "world_file": wf,
                "reached_goal": False,
                "collision_or_done": True,
                "steps_taken": 0,
                "efficiency_status": "failed",
                "efficiency_passed": False,
                "error": str(e),
            }
        results.append(rep)

    total = len(results)
    reached_goal_count = sum(1 for r in results if r.get("reached_goal"))
    efficient_count = sum(1 for r in results if r.get("efficiency_status") == "efficient")
    inefficient_success_count = sum(
        1 for r in results
        if r.get("reached_goal") and r.get("efficiency_status") != "efficient"
    )
    failed_count = total - reached_goal_count
    total_steps = sum(int(r.get("steps_taken", 0)) for r in results)
    average_steps = total_steps / total if total else 0.0

    benchmark_report = {
        "total_worlds": total,
        "goals_reached": reached_goal_count,
        "success_rate": reached_goal_count / total if total else 0.0,
        "efficient_worlds": efficient_count,
        "inefficient_success_worlds": inefficient_success_count,
        "failed_worlds": failed_count,
        "efficiency_rate": efficient_count / total if total else 0.0,
        "average_steps_taken": average_steps,
        "results": results,
    }
    with open("artifacts/irsim_benchmark_report.json", "w", encoding="utf-8") as f:
        json.dump(benchmark_report, f, indent=2, ensure_ascii=False)
    print(json.dumps(benchmark_report, indent=2, ensure_ascii=False))
    return benchmark_report


if __name__ == "__main__":
    run_benchmark()