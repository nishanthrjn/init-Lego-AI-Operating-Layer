"""Explicitly authorized Kaggle GPU worker; importing this file has no effects."""
from __future__ import annotations

import argparse
import asyncio
import fnmatch
import importlib.metadata
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

from analysis import canonical, extract_package, load_subset, sha, validate_record, verify_package, verification_outcome

HERE = Path(__file__).resolve().parent


def write_json(path: Path, value) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def append(path: Path, row: dict) -> None:
    with path.open("ab") as stream:
        stream.write(json.dumps(row, sort_keys=True, allow_nan=False).encode() + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def clean_env() -> dict[str, str]:
    patterns = ("KAGGLE_*", "*TOKEN*", "*KEY*", "*SECRET*", "*PASSWORD*", "HF_*", "GOOGLE_*CRED*")
    env = {k: v for k, v in os.environ.items() if not any(fnmatch.fnmatch(k.upper(), p) for p in patterns)}
    env.update(TRANSFORMERS_OFFLINE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_NO_TF="1",
               TRANSFORMERS_NO_FLAX="1", VLLM_NO_USAGE_STATS="1", VLLM_WORKER_MULTIPROC_METHOD="spawn",
               VLLM_ENGINE_READY_TIMEOUT_S="1200", VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS="1",
               LITELLM_LOCAL_MODEL_COST_MAP="True", LITELLM_TELEMETRY="False", LITELLM_LOG="WARNING",
               OTEL_SDK_DISABLED="true", OTEL_PYTHON_DISABLED="true", OPENAI_API_KEY="EMPTY",
               LOCAL_API_KEY="EMPTY", PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True",
               PIP_NO_INDEX="1", PYTHONDONTWRITEBYTECODE="1")
    return env


def check_environment() -> dict:
    if sys.platform != "linux" or sys.version_info[:2] != (3, 12):
        raise ValueError("ENVIRONMENT_BLOCKED: Python 3.12 Linux required")
    pins = json.loads((HERE / "source-pins.json").read_bytes())
    for name, version in pins["versions"].items():
        if importlib.metadata.version(name) != version:
            raise ValueError("ENVIRONMENT_BLOCKED: distribution version: " + name)
    for name, files in pins["installed_sources"].items():
        dist = importlib.metadata.distribution(name)
        for member, digest in files.items():
            if sha(Path(dist.locate_file(member))) != digest:
                raise ValueError("ENVIRONMENT_BLOCKED: pinned source mismatch: " + member)
    return pins


def prepare(config: dict) -> tuple[dict, list[dict], dict]:
    candidate, subset = config["candidate"], config["subset"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", candidate):
        raise ValueError("invalid candidate name")
    expected = f"AUTHORIZE FORGEAI GEMMA4 LOCAL EVAL {candidate} ON {subset}"
    if config["authorization"] != expected or config.get("gpu_authorized") is not True:
        raise ValueError("explicit candidate/subset GPU authorization required")
    if subset == "confirm-20" and (config.get("confirmation_only") is not True
                                   or not re.fullmatch(r"[0-9a-f]{64}", config.get("winner_evidence_sha256", ""))):
        raise ValueError("held-out confirmation requires winner evidence hash and confirmation-only approval")
    if config.get("internet_off_confirmed") is not True or config.get("package_reconciled") is not True:
        raise ValueError("Internet Off and prior local package reconciliation must be confirmed")
    if type(config["wall_seconds"]) is not int or not 60 <= config["wall_seconds"] <= 11 * 3600:
        raise ValueError("total wall guard must be 60..39600 seconds")
    doc, selected = load_subset(Path(config["subset_file"]), config["subset_sha256"], subset)
    data = Path(config["data"])
    if not (data / "tasks.jsonl").is_file():
        raise ValueError("official public task inventory missing")
    # No hidden data lookup is authorized. The official Evaluator searches these ancestors.
    for ancestor in (data, *data.resolve().parents):
        if (ancestor / "secret").exists():
            raise ValueError("hidden secret bundle must not be attached to this public-dev session")
    for child in ("snapshots", "graphs", "embeddings", "wheels"):
        if not (data / child).is_dir():
            raise ValueError("missing public data directory: " + child)
    if not Path(config["wheelhouse"]).is_dir():
        raise ValueError("official wheelhouse input missing; no automatic installation")
    wheel_pins = json.loads((HERE / "source-pins.json").read_bytes())["wheels"]
    for filename, digest in wheel_pins.items():
        if sha(Path(config["wheelhouse"]) / filename) != digest:
            raise ValueError("official wheelhouse byte mismatch: " + filename)
    manifest = verify_package(Path(config["package"]), Path(config["manifest"]),
                              config["manifest_sha256"], config["receipt_sha256"])
    return doc, selected, manifest


def stop_reason(error: str | None, submitted: bool) -> str:
    # Classify only explicit pinned harness messages, never a threshold guess.
    text = error or ""
    for needle, category in (("Agent exceeded tool call budget", "call_budget"),
                             ("Agent exceeded session timeout", "time_budget"),
                             ("Agent exceeded turns budget", "turn_budget"),
                             ("Agent exceeded maximum allowed LLM turns", "turn_budget")):
        if text.startswith(needle):
            return category
    return "submitted" if submitted else ("error" if error else "unknown")


def telemetry(task, result, context, elapsed: float, trace) -> dict:
    from swegemma.models.task import extract_test_files_from_patch
    patch = result.agent_patch or ""
    entries = trace.entries if trace is not None else None
    tools = trace.tool_call_breakdown if trace is not None else None
    last_error = None
    test_touch = None
    pending = {}
    if entries is not None:
        for e in entries:
            if e.event_type == "tool_call" and e.tool_name in ("edit_file", "write_file"):
                pending[e.tool_name] = (e.tool_args or {}).get("filepath")
            if e.event_type == "tool_response":
                try:
                    value = json.loads(e.tool_result)
                except (ValueError, TypeError):
                    continue
                if isinstance(value, dict) and value.get("status") == "error":
                    # Tool error text can contain code/commands; retain presence and tool only.
                    last_error = {"tool": e.tool_name, "category": "TOOL_ERROR", "detail": "RETAINED_IN_EXTERNAL_TRACE"}
                # Legacy trace entries omit call IDs. Multiple same-name calls are ambiguous.
                if (isinstance(value, dict) and value.get("status") == "ok" and e.tool_name in pending
                        and tools.get(e.tool_name) == 1):
                    path = pending.pop(e.tool_name)
                    if isinstance(path, str):
                        parts = Path(path).parts
                        name = Path(path).name
                        if (name in {"conftest.py", "pytest.ini", ".pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg",
                                     "sitecustomize.py", "usercustomize.py", "_swegemma_stubs.py"}
                                or name.endswith(".pth") or (name.endswith(".py") and
                                (name.startswith("test_") or name.endswith("_test.py") or
                                 any(p.lower() in {"tests", "test", "testing"} for p in parts)))):
                            test_touch = True  # Positive evidence only; no claim that shell edits were absent.
    error = result.error
    stop = stop_reason(error, context.patch_submitted)
    verification_ran = (result.test_output or "").startswith("STDOUT:\n")
    harness_errors = ["HARNESS_ERROR_DETAILS_IN_EXTERNAL_LOG"] if error and stop == "error" and not verification_ran else []
    outcome = verification_outcome(bool(result.resolved), result.test_output or "")
    harness_errors.extend(outcome["harness_errors"])
    if not result.resolved and result.test_exit_code not in (0, 1) and stop == "submitted":
        harness_errors.append("VERIFICATION_ERROR_OR_INCOMPLETE")
    agent_seconds = context.agent_elapsed_seconds if context.agent_start_time is not None else None
    turns = context.llm_calls_used
    files = extract_test_files_from_patch(patch)
    # Include deleted paths; quoted/unusual git names require raw-patch human review.
    for line in patch.splitlines():
        if line.startswith("diff --git a/") and " b/" in line:
            files.append(line.split(" b/", 1)[1])
    return {"schema": 1, "task_id": task.instance_id, "repo": task.repo,
            "resolved": outcome["resolved"], "official_resolved": outcome["official_resolved"],
            "verification_status": outcome["verification_status"],
            "wall_seconds": elapsed, "agent_seconds": agent_seconds, "model_turns": turns,
            "tool_calls": tools, "budget_counted_tool_calls": context.tool_calls_used,
            "tokens": trace.summarize()["total_tokens"] if entries is not None and any(e.usage for e in entries) else None,
            "submit_patch_called": (bool(tools.get("submit_patch", 0)) if tools is not None else None),
            "submit_patch_succeeded": context.patch_submitted,
            "patch_bytes": len(patch.encode()), "files_changed": sorted(set(files)),
            "test_files_touched": test_touch, "stray_files": None,
            "official_error_present": bool(error),
            "stop_reason": stop, "last_tool_error": last_error, "harness_errors": harness_errors,
            "seconds_per_model_turn": agent_seconds / turns if agent_seconds is not None and turns else None,
            "telemetry_limits": "Tool counts are trace requests, not guaranteed effects. Test-touch/stray intent UNKNOWN after filtering. Seconds/turn includes tools, not inference latency."}


async def evaluate(config: dict, output: Path, selected: list[dict], models, adapters, agent: Path, meta: dict) -> None:
    import yaml
    from google.adk.agents.context_cache_config import ContextCacheConfig
    from google.adk.apps._configs import EventsCompactionConfig
    from adk_eval_core.tracing import SessionTrace
    from swegemma.config import EvalConfig, build_submission_limits
    from swegemma.context import SwegemmaContext
    from swegemma.evaluate import Evaluator
    from swegemma.models import load_tasks
    from swegemma.results import append_task_result
    data = Path(config["data"])
    task_map = {t.instance_id: t for t in load_tasks(data / "tasks.jsonl")}
    tasks = [task_map[r["task_id"]] for r in selected]
    if any(t.repo != r["repo"] for t, r in zip(tasks, selected)):
        raise ValueError("task repository identity mismatch")
    # Public verification payload is consumed only by the official verifier, never added to prompts.
    if any(not t.test_patch for t in tasks):
        raise ValueError("PUBLIC_VERIFICATION_UNAVAILABLE: no hidden-test hydration permitted")
    eval_paths = [agent / n for n in ("eval_config.yaml", "eval_config.yml") if (agent / n).is_file()]
    if len(eval_paths) > 1:
        raise ValueError("ambiguous eval configuration")
    raw = {}
    if eval_paths:
        raw = yaml.safe_load(eval_paths[0].read_text(encoding="utf-8")) or {}
    section = raw.get("evaluation", raw)
    turns_raw = section.get("max_turns", section.get("max_llm_calls"))
    limits, constraints = build_submission_limits()
    cfg = EvalConfig(tasks_path=data / "tasks.jsonl", snapshots_dir=data / "snapshots",
                     results_dir=output / "official", submission_dir=agent, models=models,
                     sandbox="subprocess", concurrency=1,
                     timeout_seconds=int(section.get("timeout_seconds", 300)),
                     verification_timeout_seconds=int(section.get("verification_timeout_seconds", 300)),
                     max_time_minutes=float(section.get("max_time_minutes", 60)),
                     max_tool_calls=int(section.get("max_tool_calls", 100)),
                     max_turns=int(turns_raw) if turns_raw is not None else None,
                     limits=limits, generation_constraints=constraints, adapter_manifest=adapters,
                     context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
                     events_compaction_config=EventsCompactionConfig(compaction_interval=15, overlap_size=2,
                                                                      token_threshold=14336, event_retention_size=5),
                     graph_dir=str(data / "graphs"), embeddings_dir=str(data / "embeddings"),
                     wheels_dir=data / "wheels", verbose=False)
    meta["evaluation_config"] = section
    write_json(output / "run.json", meta)
    evaluator = Evaluator(cfg)
    try:
        for i, task in enumerate(tasks, 1):
            begin = time.perf_counter()
            append(output / "events.jsonl", {"event": "TASK_STARTED", "task_id": task.instance_id, "utc_epoch": time.time()})
            context = SwegemmaContext(docker_manager=evaluator.docker, container_id="",
                                      problem_statement=task.problem_statement, hints_text=task.hints_text,
                                      task=task, repo=task.repo, graph_dir=cfg.graph_dir,
                                      embeddings_dir=cfg.embeddings_dir, budget=cfg.budget, harness=cfg.harness)
            try:
                result = await evaluator.evaluate_task(task, task_index=i, total_tasks=len(tasks), context=context)
            except Exception as exc:
                elapsed = time.perf_counter() - begin
                row = {"schema": 1, "task_id": task.instance_id, "repo": task.repo, "resolved": None,
                       "wall_seconds": elapsed, "agent_seconds": None, "model_turns": None,
                       "tool_calls": None, "tokens": None, "submit_patch_called": None,
                       "patch_bytes": None, "files_changed": None, "test_files_touched": None,
                       "stray_files": None, "stop_reason": "error", "last_tool_error": None,
                       "harness_errors": [type(exc).__name__], "seconds_per_model_turn": None}
                validate_record(row)
                append(output / "tasks.jsonl", row)
                raise
            elapsed = time.perf_counter() - begin  # includes the verifier's finally/teardown
            trace = result.trace
            if trace is None and result.trace_path:
                trace = SessionTrace.from_json(result.trace_path)
            row = telemetry(task, result, context, elapsed, trace)
            validate_record(row)
            append(output / "tasks.jsonl", row)
            append_task_result(result, cfg.results_dir)
            print(json.dumps({"task_id": task.instance_id, "resolved": row["resolved"], "wall_seconds": elapsed}), flush=True)
    finally:
        evaluator.docker.cleanup_all()


OFFICIAL_CELL_HASHES = {
    "2": "c3032e216b0a393aec76180338e56f3ae5d7d995b5de9913f78b79a1fa1105af",
    "8": "05c129500663d3b377f0ffec84ff7145a942e5414717f1a7733108c619c71b9a",
}


def official_cells() -> dict:
    document = json.loads((HERE / "official-cells.json").read_bytes())
    pins = json.loads((HERE / "source-pins.json").read_bytes())
    if document["starter_sha256"] != pins["documents"]["docs/getting-started-gemma-4-developer-agent.ipynb"]:
        raise ValueError("official starter identity mismatch")
    if set(document["cells"]) != set(OFFICIAL_CELL_HASHES):
        raise ValueError("unexpected official cells")
    for index, digest in OFFICIAL_CELL_HASHES.items():
        cell = document["cells"][index]
        if cell["sha256"] != digest or hashlib.sha256(cell["source"].encode()).hexdigest() != digest:
            raise ValueError("official cell source changed: " + index)
    return document


def installed_versions() -> dict:
    return {d.metadata["Name"]: d.version for d in importlib.metadata.distributions() if d.metadata["Name"]}


def worker(config: dict, output: Path) -> None:
    doc, selected, manifest = prepare(config)
    cells = official_cells()
    if config.get("official_environment_authorized") is not True:
        raise ValueError("official wheelhouse installation requires explicit approval")
    if sys.platform != "linux" or sys.version_info[:2] != (3, 12):
        raise ValueError("Python 3.12 Linux required")
    evidence = {"starter_sha256": cells["starter_sha256"], "cell_sha256": OFFICIAL_CELL_HASHES,
                "pre_install_versions": installed_versions(), "state": "INSTALL_STARTED"}
    write_json(output / "environment.json", evidence)
    namespace = {"__name__": "__main__"}
    installation_start = time.perf_counter()
    exec(compile(cells["cells"]["2"]["source"], "official-starter-cell-2", "exec"), namespace)
    evidence.update(post_install_versions=installed_versions(),
                    installation_seconds=time.perf_counter() - installation_start,
                    state="OFFICIAL_INSTALL_COMPLETED")
    write_json(output / "environment.json", evidence)
    pins = check_environment()
    import litellm
    import torch
    from adk_submission import discover_adapters, validate_directory
    from adk_submission.discovery import discover_declared_models
    from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS, build_submission_limits
    from swegemma.models import load_tasks
    public_tasks = load_tasks(Path(config["data"]) / "tasks.jsonl")
    public_map = {t.instance_id: t for t in public_tasks}
    if len(public_tasks) != 129 or any(r["task_id"] not in public_map or public_map[r["task_id"]].repo != r["repo"] for r in selected):
        raise ValueError("official public task identity does not match frozen metadata selection")
    if any(not public_map[r["task_id"]].test_patch for r in selected):
        raise ValueError("PUBLIC_VERIFICATION_UNAVAILABLE: no hidden test lookup authorized")
    if torch.cuda.device_count() != 4 or any("L4" not in torch.cuda.get_device_name(i) for i in range(4)):
        raise ValueError("ENVIRONMENT_BLOCKED: exactly four L4 GPUs required")
    agent = output / "candidate"
    extract_package(Path(config["package"]), agent)
    limits, _ = build_submission_limits()
    validate_directory(agent, limits=limits)
    declared = set(discover_declared_models(agent))
    allowed = {f"gemma-4-{name}-it-qat-w4a16-ct" for name in ("31b", "12b", "e4b", "e2b")}
    if len(declared) != 1 or not declared <= allowed:
        raise ValueError("one official quantized model required")
    model = next(iter(declared))
    model_path = Path(config["model_path"])
    if not model_path.is_dir() or model_path.parent.name != model:
        raise ValueError("model path must be the attached official model/version directory")
    adapters = discover_adapters(str(agent), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
    amap = getattr(adapters, "adapters", None) or {}
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", key) for key in amap):
        raise ValueError("unsafe adapter identity")
    # Dependencies normally supplied by starter cell 4, without copying/mutating sample agents.
    namespace.update(AGENT_DIR=agent, re=re)
    # The unchanged server cell uses this exact official model path (version 2).
    expected_model_path = Path(f"/kaggle/input/models/google/gemma-4/other/{model}/2")
    if model_path != expected_model_path:
        raise ValueError("model path differs from unchanged official server cell")
    meta = {"schema": 1, "candidate": config["candidate"], "subset": config["subset"],
            "subset_sha256": config["subset_sha256"], "source_sha256": doc["source_sha256"],
            "official_tasks_sha256": sha(Path(config["data"]) / "tasks.jsonl"),
            "manifest_sha256": config["manifest_sha256"], "package_sha256": manifest["zip_sha256"],
            "receipt_sha256": config["receipt_sha256"], "task_ids": [r["task_id"] for r in selected],
            "confirmation_only": config.get("confirmation_only", False),
            "winner_evidence_sha256": config.get("winner_evidence_sha256"),
            "task_repos": {r["task_id"]: r["repo"] for r in selected}, "startup_seconds": None,
            "official_cell_sha256": OFFICIAL_CELL_HASHES,
            "installation_seconds": evidence["installation_seconds"],
            "runtime_pins": pins["versions"], "source_pins_sha256": sha(HERE / "source-pins.json"),
            "python": sys.version, "model": model, "model_input": str(model_path),
            "torch_version": torch.__version__, "cuda_version": torch.version.cuda,
            "gpu_names": [torch.cuda.get_device_name(i) for i in range(4)],
            "concurrency": 1, "hidden_scorer_concurrency": "UNKNOWN",
            "utc_epoch_start": time.time(), "wall_guard_seconds": config["wall_seconds"]}
    write_json(output / "run.json", meta)
    (output / "tasks.jsonl").touch(exist_ok=False)
    begin = time.perf_counter()
    try:
        exec(compile(cells["cells"]["8"]["source"], "official-starter-cell-8", "exec"), namespace)
        meta["startup_seconds"] = time.perf_counter() - begin
        evidence.update(state="OFFICIAL_SERVER_STARTED", server_startup_seconds=meta["startup_seconds"],
                        post_server_versions=installed_versions())
        write_json(output / "environment.json", evidence)
        write_json(output / "run.json", meta)
        asyncio.run(evaluate(config, output, selected, namespace["models"], namespace["adapters"], agent, meta))
    finally:
        server = namespace.get("server_instance")
        if server is not None:
            server.stop()


def process_snapshot() -> dict[int, tuple[int, str]]:
    """Linux parent PID/start-tick identity; never read process arguments or environments."""
    snapshot = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            snapshot[int(entry.name)] = (int(fields[1]), fields[19])
        except (OSError, IndexError, ValueError):
            continue  # Process exited between enumeration and read.
    return snapshot


def track_descendants(root: int, tracked: dict[int, str], snapshot: dict[int, tuple[int, str]]) -> None:
    if not tracked and root in snapshot:
        tracked[root] = snapshot[root][1]
    active = {pid for pid, tick in tracked.items() if pid in snapshot and snapshot[pid][1] == tick}
    while True:
        children = {pid for pid, (parent, _) in snapshot.items() if parent in active} - active
        if not children:
            break
        for pid in children:
            tracked[pid] = snapshot[pid][1]
        active.update(children)


def signal_tracked(tracked: dict[int, str], sig: int) -> None:
    snapshot = process_snapshot()
    for pid, tick in tracked.items():
        if pid in snapshot and snapshot[pid][1] == tick:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass


def launch(config_path: Path) -> None:
    config = json.loads(config_path.read_bytes())
    prepare(config)  # stop before any GPU/import/install on missing authorization or identity
    official_cells()
    if config.get("official_environment_authorized") is not True:
        raise ValueError("official wheelhouse installation requires explicit approval")
    if config["wheelhouse"] != "/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse":
        raise ValueError("unchanged official install cell requires its exact wheelhouse mount")
    output = Path(config["output"]).resolve()
    if not output.is_relative_to(Path("/kaggle/working")) or output == Path("/kaggle/working"):
        raise ValueError("output must be a new directory below /kaggle/working")
    output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    with (output / "worker.log").open("xb") as log:
        process = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()),
                                    "--worker", str(config_path.resolve())],
                                   env=clean_env(), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        tracked = {}
        try:
            deadline = start + config["wall_seconds"]
            while process.poll() is None:
                track_descendants(process.pid, tracked, process_snapshot())
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired("local-eval-worker", config["wall_seconds"])
                try:
                    process.wait(timeout=min(1.0, remaining))
                except subprocess.TimeoutExpired:
                    continue
            code = process.returncode
            state = "COMPLETED" if code == 0 else "HARNESS_ERROR"
        except subprocess.TimeoutExpired:
            state, code = "WALL_GUARD", None
        except KeyboardInterrupt:
            state, code = "INTERRUPTED", None
        finally:
            # Official command sandboxes create new sessions: track descendants as well as group.
            track_descendants(process.pid, tracked, process_snapshot())
            signal_tracked(tracked, signal.SIGTERM)
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            signal_tracked(tracked, signal.SIGKILL)
            process.wait()
    write_json(output / "completion.json", {"state": state, "exit_code": code,
               "wall_seconds": time.perf_counter() - start,
               "interrupted_task": "derive TASK_STARTED without result; never score as completed"})
    print(state, str(output))
    if state != "COMPLETED":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        c = json.loads(args.config.read_bytes())
        worker(c, Path(c["output"]))
    else:
        launch(args.config)
