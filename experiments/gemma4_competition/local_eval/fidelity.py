"""CPU-only diagnostic/reverification support. No effects on import."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import time

PIN = "05706c6a948a67bfaf991ed0282d11308aac79865a614a68c6c582fe01f67033"
AUTH = "AUTHORIZE FORGEAI GEMMA4 CPU FIDELITY {operation}"


def notebook_mode(config, mode, authorization):
    """Translate visible notebook selection into an explicitly authorized worker."""
    import controls as c
    phrases = {"controls": c.AUTHORIZATION,
               "diagnostics": AUTH.format(operation="DIAGNOSTIC"),
               "reverify": AUTH.format(operation="REVERIFY")}
    if mode not in phrases or authorization != phrases[mode]:
        raise ValueError("mode-specific authorization required")
    config["authorization"] = c.AUTHORIZATION
    if mode == "controls":
        return "controls.py"
    config.update(operation="DIAGNOSTIC" if mode == "diagnostics" else "REVERIFY",
                  fidelity_authorization=authorization)
    return "fidelity.py"


def frozen_controls(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN:
        raise ValueError("historical controls hash mismatch")
    return json.loads(raw)


def safe_tail(output, gold, tests):
    """Retain bounded error types only; never arbitrary source/exception payloads.

    Line positions correspond to the final 60 lines. This intentionally loses
    detail rather than claiming arbitrary pytest output is safe after diff removal.
    """
    forbidden = {line.strip().lstrip("+- ") for text in (gold, tests) for line in text.splitlines()}
    result = []
    for line in output.splitlines()[-60:]:
        if line.strip().lstrip("+- ") in forbidden:
            result.append("[REFERENCE_CONTENT_REDACTED]")
            continue
        match = re.search(r"\b(ModuleNotFoundError|ImportError|AttributeError|AssertionError|TimeoutError|ConnectionError)\b", line)
        result.append(match.group(1) if match else "[OUTPUT_REDACTED]")
    return result


def observe_import(manager, repo):
    """Observe in the same sandbox immediately before official teardown."""
    module = repo.rsplit("/", 1)[-1].lower()
    if module not in {"requests", "httpx", "fastapi", "rich"}:
        raise ValueError("unsupported repository")
    observation = {"module": module, "file": None, "status": "NOT_OBSERVED"}
    original = manager.stop

    def stop(sandbox_id):
        try:
            code = f"import {module}; print('ORIGIN=' + str({module}.__file__))"
            response = manager.exec(sandbox_id, "python -c " + shlex.quote(code))
            lines = [s[7:] for s in response.stdout.splitlines() if s.startswith("ORIGIN=/")]
            if response.exit_code == 0 and len(lines) == 1 and len(lines[0]) < 4096:
                observation.update(file=lines[0], status="OBSERVED")
            else:
                observation["status"] = "IMPORT_FAILED"
        except Exception:
            observation["status"] = "PROBE_FAILED"
        finally:
            original(sandbox_id)
    # Preserve the concrete type name: official provisioning branches on it.
    manager.stop = stop
    return observation


def patch_input(config, task_id):
    entry = config["patches"][task_id]
    root = Path(config["previous_run"]).resolve()
    path = (root / entry["path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("agent patch must be within retained run")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise ValueError("retained agent patch hash mismatch")
    return raw.decode("utf-8")


def main(config_path):
    import controls as c
    from runtime import install_official_environment, check_environment, write_json
    config = json.loads(config_path.read_bytes())
    operation = config.get("operation")
    if operation not in {"DIAGNOSTIC", "REVERIFY"} or config.get("fidelity_authorization") != AUTH.format(operation=operation):
        raise ValueError("exact fidelity authorization required")
    data, selected, _ = c.preflight(config, before_install=True)
    output = Path(config["fidelity_output"]).resolve()
    if output.parent != Path("/kaggle/working"):
        raise ValueError("external Kaggle output directory required")
    history = frozen_controls(config["controls"])
    if history["official_tasks_sha256"] != c.sha(data / "tasks.jsonl"):
        raise ValueError("official inventory changed")
    if operation == "DIAGNOSTIC":
        ids = {r["task_id"] for r in history["tasks"] if r["class"] != "VERIFIABLE"}
    else:
        ids = set(config["patches"])
        for task_id in ids:
            patch_input(config, task_id)
    if not ids or not ids <= {r["task_id"] for r in selected}:
        raise ValueError("unknown/empty task selection")
    output.mkdir(exist_ok=False)
    write_json(output / "provenance.json", {
        "operation": operation, "historical_controls_sha256": PIN,
        "official_tasks_sha256": history["official_tasks_sha256"],
        "source_pins_sha256": c.sha(c.HERE / "source-pins.json"),
        "patch_sha256": {k: v["sha256"] for k, v in config.get("patches", {}).items()},
        "qualification": "DIAGNOSTIC_ONLY; NO_VERIFICATION_PARITY_CLAIM"})
    install_official_environment(config, output)
    check_environment()
    deadline = time.perf_counter() + 11 * 3600
    for row in selected:
        if row["task_id"] not in ids:
            continue
        if time.perf_counter() >= deadline:
            raise ValueError("fidelity wall guard reached")
        result = c.run_child(config_path, row["task_id"], operation, deadline - time.perf_counter())
        write_json(output / (row["task_id"] + ".result.json"), result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    main(args.config.resolve())
