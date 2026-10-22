"""Attended CPU-only GOLD/EMPTY verification; no agent, serving or installs."""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from analysis import canonical, load_subset, sha, verification_outcome
from runtime import check_environment, clean_env, signal_tracked, track_descendants, process_snapshot, write_json

HERE = Path(__file__).resolve().parent
AUTHORIZATION = "AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL CONTROLS ON dev-30+confirm-20 CPU"
ERRORS = {"NONE", "HARNESS_ENVIRONMENT_ERROR", "UNRESOLVED_INCOMPLETE_API",
          "VERIFICATION_FAILED", "CONTROL_EXECUTION_ERROR", "CONTROL_TIMEOUT", "MISSING_PUBLIC_SPEC"}
CLASSES = {"VERIFIABLE", "ENV_BROKEN", "UNSOUND"}


def classify(gold: dict, empty: dict) -> str:
    # Empty passing is unsound even if gold encountered an environment failure.
    if empty["passed"]:
        return "UNSOUND"
    if not gold["passed"] and gold["error_category"] == "HARNESS_ENVIRONMENT_ERROR":
        return "ENV_BROKEN"
    # Infrastructure/timeouts in EMPTY cannot establish a meaningful failing test.
    if gold["passed"] and empty["error_category"] in {"VERIFICATION_FAILED", "UNRESOLVED_INCOMPLETE_API"}:
        return "VERIFIABLE"
    return "UNSOUND"


def safe_result(passed: bool, category: str, duration: float) -> dict:
    if (type(passed) is not bool or category not in ERRORS
            or type(duration) not in (int, float) or not 0 <= duration < float("inf")
            or passed != (category == "NONE")):
        raise ValueError("invalid bounded control result")
    return {"passed": passed, "error_category": category, "seconds": duration}


async def verify_one(task, mode, verifier, manager, config, paths):
    begin = time.perf_counter()
    if not task.test_patch.strip() or (mode == "GOLD" and not task.patch.strip()):
        return safe_result(False, "MISSING_PUBLIC_SPEC", time.perf_counter() - begin)
    try:
        result = await verifier(manager, config, task, paths[0], base_snapshot_path=paths[1],
                                patch_path=paths[2], agent_patch=task.patch if mode == "GOLD" else "",
                                trace=None, start_time=begin)
        outcome = verification_outcome(bool(result.resolved), result.test_output or "", task.repo)
        category = "NONE" if result.resolved else outcome["verification_status"]
        if category not in ERRORS:
            category = "VERIFICATION_FAILED" if result.test_exit_code in (0, 1, 2) else "CONTROL_EXECUTION_ERROR"
        return safe_result(bool(result.resolved), category, time.perf_counter() - begin)
    except Exception:
        # Never stringify exceptions: they may contain gold/test fragments.
        return safe_result(False, "CONTROL_EXECUTION_ERROR", time.perf_counter() - begin)


def preflight(config):
    if (config.get("authorization") != AUTHORIZATION or config.get("cpu_only_confirmed") is not True
            or config.get("internet_off_confirmed") is not True):
        raise ValueError("Exact CPU control authorization and Internet Off required")
    if sys.platform != "linux" or sys.version_info[:2] != (3, 12):
        raise ValueError("CPU controls require Python 3.12 Linux")
    if Path("/dev/nvidia0").exists():
        raise ValueError("Accelerator must be None")
    check_environment()  # Metadata/source checks only; missing packages block, never install.
    pins = (HERE / "subsets.sha256").read_text().split()[0]
    doc, dev = load_subset(HERE / "subsets.json", pins, "dev-30")
    _, confirm = load_subset(HERE / "subsets.json", pins, "confirm-20")
    data = Path(config["data"]).resolve()
    if any((p / "secret").exists() for p in (data, *data.parents)):
        raise ValueError("Public controls cannot use a secret bundle")
    if not (data / "tasks.jsonl").is_file() or any(not (data / d).is_dir() for d in ("snapshots", "wheels")):
        raise ValueError("Public tasks, snapshots and wheels required")
    return data, dev + confirm, pins


def worker(config, task_id, mode, destination):
    data, selected, _ = preflight(config)
    if mode not in {"GOLD", "EMPTY"} or task_id not in {r["task_id"] for r in selected}:
        raise ValueError("unapproved control")
    # No Evaluator: avoid agent loop, secret hydration, traces and result artifact writers.
    from swegemma.models import load_tasks
    from swegemma.config import EvalConfig
    from swegemma.deduplication import resolve_task_snapshot_paths
    from swegemma.harness.verification import verify_task
    from swegemma.sandbox import SubprocessManager
    tasks = {t.instance_id: t for t in load_tasks(data / "tasks.jsonl")}
    task = tasks[task_id]
    if task.repo != next(r["repo"] for r in selected if r["task_id"] == task_id):
        raise ValueError("task identity mismatch")
    paths = resolve_task_snapshot_paths(data / "snapshots", task.instance_id, task.repo)
    if not paths[0].is_file():
        raise ValueError("public snapshot missing")
    scratch = Path(os.environ["TMPDIR"])
    manager = SubprocessManager(timeout_seconds=300, base_dir=scratch)
    cfg = EvalConfig(tasks_path=data / "tasks.jsonl", snapshots_dir=data / "snapshots",
                     results_dir=scratch / "unused-results", submission_dir=scratch,
                     models=None, sandbox="subprocess", wheels_dir=data / "wheels",
                     timeout_seconds=300, verification_timeout_seconds=300)
    try:
        result = asyncio.run(verify_one(task, mode, verify_task, manager, cfg, paths))
    finally:
        manager.cleanup_all()
    destination.write_bytes(canonical(result))  # strict metadata only


def run_child(config_file, task_id, mode, remaining):
    begin = time.perf_counter()
    # Gold may exist transiently in official verifier /tmp files, never retained outputs.
    with tempfile.TemporaryDirectory(prefix="gemma-controls-", dir="/tmp") as directory:
        result_file = Path(directory) / "metadata.json"
        env = clean_env()
        env.update(TMPDIR=directory, HOME=directory, CUDA_VISIBLE_DEVICES="")
        process = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), str(config_file),
                                    "--worker", task_id, mode, str(result_file)],
                                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
        tracked = {}
        deadline = begin + min(900, remaining)
        timed_out = False
        try:
            while process.poll() is None:
                track_descendants(process.pid, tracked, process_snapshot())
                if time.perf_counter() >= deadline:
                    timed_out = True
                    break
                time.sleep(0.2)
        finally:
            track_descendants(process.pid, tracked, process_snapshot())
            signal_tracked(tracked, signal.SIGKILL)
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)
        if timed_out:
            return safe_result(False, "CONTROL_TIMEOUT", time.perf_counter() - begin)
        if process.returncode != 0 or not result_file.is_file():
            return safe_result(False, "CONTROL_EXECUTION_ERROR", time.perf_counter() - begin)
        row = json.loads(result_file.read_bytes())
        return safe_result(row["passed"], row["error_category"], time.perf_counter() - begin)


def run(config_file):
    config = json.loads(config_file.read_bytes())
    data, selected, subset_sha = preflight(config)
    output = Path(config["output"]).resolve()
    if output.parent != Path("/kaggle/working") or output.name != "controls.json" or output.exists():
        raise ValueError("Use fresh /kaggle/working/controls.json; preserve previous attempts")
    source_pins = json.loads((HERE / "source-pins.json").read_bytes())
    doc = {"schema": 1, "state": "INCOMPLETE", "subset_sha256": subset_sha,
           "official_tasks_sha256": sha(data / "tasks.jsonl"),
           "source_pins_sha256": sha(HERE / "source-pins.json"), "runtime_pins": source_pins["versions"],
           "backend": "subprocess", "verification_timeout_seconds": 300, "tasks": []}
    deadline = time.perf_counter() + 11 * 3600
    write_json(output, doc)
    for item in selected:
        if time.perf_counter() >= deadline:
            raise ValueError("Controls incomplete: wall guard; preserve metadata")
        gold = run_child(config_file, item["task_id"], "GOLD", deadline - time.perf_counter())
        if time.perf_counter() >= deadline:
            raise ValueError("Controls incomplete: wall guard; preserve metadata")
        empty = run_child(config_file, item["task_id"], "EMPTY", deadline - time.perf_counter())
        doc["tasks"].append({"task_id": item["task_id"], "repo": item["repo"],
                             "class": classify(gold, empty), "gold": gold, "empty": empty})
        write_json(output, doc)
        print(json.dumps({"task_id": item["task_id"], "class": doc["tasks"][-1]["class"]}), flush=True)
    doc["state"] = "COMPLETE"
    write_json(output, doc)
    print("CONTROLS_SHA256=" + sha(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--worker", nargs=3)
    args = parser.parse_args()
    try:
        if args.worker:
            logging.disable(logging.CRITICAL)
            worker(json.loads(args.config.read_bytes()), args.worker[0], args.worker[1], Path(args.worker[2]))
        else:
            run(args.config.resolve())
    except BaseException:
        # Bounded failure only; never traceback locals/task payloads in notebook outputs.
        print("CONTROLS_BLOCKED_OR_INCOMPLETE; no raw error retained", file=sys.stderr)
        raise SystemExit(1) from None
