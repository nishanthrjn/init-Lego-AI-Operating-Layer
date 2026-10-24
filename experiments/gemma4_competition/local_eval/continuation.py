"""Offline outcome projection and hash-bound resume; no effects on import."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def fatal_error(error):
    text = (error or "").lower()
    return any(token in text for token in (
        "failed to load agent", "agent load failed", "failed to compile", "compilation failed",
        "compile_submission", "vllm", "server disconnected", "connection refused",
        "connection error", "apiconnectionerror", "server unavailable"))


def project(row, error="", log=""):
    result = dict(row)
    categories = set(row.get("failure_categories", []))
    text = (error + "\n" + log).lower()
    # Structured per-task evaluator error only: model prose may quote error names.
    context_failure = "contextwindowexceedederror" in error.lower()
    format_failure = any(s in text for s in (
        "reached maximum continuation nudges", "malformed tool", "unparsed tool",
        "<|tool_call>call:", "<|tool_call|> was cut off"))
    agent_outcome = (error.startswith("Agent exceeded ") or
                     "without calling submit_patch" in error or format_failure or context_failure)
    if context_failure:
        categories.add("CONTEXT_WINDOW_EXCEEDED")
    if format_failure:
        categories.add("TOOL_CALL_FORMAT_FAILURE")
    if row.get("patch_bytes") == 0:
        categories.add("NO_PATCH")
    if agent_outcome and not fatal_error(error):
        result["harness_errors"] = [v for v in row.get("harness_errors", [])
                                    if v != "HARNESS_ERROR_DETAILS_IN_EXTERNAL_LOG"]
        if not row.get("official_resolved", row.get("resolved")):
            result.update(resolved=False, verification_status="UNRESOLVED")
        result["classification_source"] = "OFFICIAL_AGENT_OUTCOME"
    result["failure_categories"] = sorted(categories)
    return result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


IDENTITY = ("candidate", "subset", "subset_sha256", "manifest_sha256", "package_sha256",
            "runtime_pins", "source_pins_sha256", "official_tasks_sha256", "task_ids", "task_repos",
            "model", "official_cell_sha256", "package_mode")


def load_resume(config, current=None):
    """Verify immutable source evidence before trusting completed task rows."""
    if not config.get("resume_manifest"):
        return [], None
    from analysis import read_run
    path = Path(config["resume_manifest"])
    if digest(path) != config["resume_manifest_sha256"]:
        raise ValueError("resume manifest hash mismatch")
    manifest = json.loads(path.read_bytes())
    root = Path(config["resume_previous"]).resolve()
    previous_config = Path(config["resume_previous_config"])
    if digest(previous_config) != manifest["config_sha256"]:
        raise ValueError("resume config hash mismatch")
    for name, pin in manifest["files"].items():
        file = (root / name).resolve()
        if not file.is_relative_to(root) or digest(file) != pin:
            raise ValueError("resume source hash mismatch: " + name)
    # Require every classification-bearing log to be pinned, including absence.
    actual_logs = {p.relative_to(root).as_posix() for p in (root / "official/logs").glob("*.log")}
    actual_tests = {p.relative_to(root).as_posix() for p in (root / "official/test_outputs").glob("*.log")}
    official_results = {"official/task_results.jsonl"} if (root / "official/task_results.jsonl").is_file() else set()
    if set(manifest["files"]) != {"run.json", "tasks.jsonl", "completion.json"} | actual_logs | actual_tests | official_results:
        raise ValueError("resume evidence inventory mismatch")
    old, rows = read_run(root)
    old_config = json.loads(previous_config.read_bytes())
    for key in ("candidate", "subset", "subset_sha256", "manifest_sha256", "package_mode"):
        if old.get(key) != config.get(key, "RECONCILED" if key == "package_mode" else None) or old_config.get(key, "RECONCILED" if key == "package_mode" else None) != old.get(key):
            raise ValueError("resume configuration mismatch: " + key)
    if current is not None:
        for key in IDENTITY:
            if current.get(key) != old.get(key):
                raise ValueError("resume run identity mismatch: " + key)
    kept = []
    for row in rows:
        completed = row.get("completed_result", "official_resolved" in row)
        if completed:
            kept.append(dict(row, completed_result=True,
                             attempt_id=row.get("attempt_id", manifest["files"]["run.json"]),
                             inherited_from_run_sha256=manifest["files"]["run.json"]))
    return kept, old


def merge(prior, new):
    rows = prior + new
    if len({r["task_id"] for r in rows}) != len(rows):
        raise ValueError("completed task cannot be overwritten on resume")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("previous", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.previous.resolve()
    output = args.output.resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[3]) or output.is_relative_to(root):
        raise ValueError("resume preparation output must be external and separate")
    files = [root / n for n in ("run.json", "tasks.jsonl", "completion.json")]
    files += list((root / "official/logs").glob("*.log"))
    files += list((root / "official/test_outputs").glob("*.log"))
    if (root / "official/task_results.jsonl").is_file():
        files.append(root / "official/task_results.jsonl")
    doc = {"schema": 1, "config_sha256": digest(args.config),
           "files": {p.relative_to(root).as_posix(): digest(p) for p in files}}
    from analysis import canonical, read_run
    meta, rows = read_run(root)
    output.mkdir(parents=True, exist_ok=False)
    (output / "resume-manifest.json").write_bytes(canonical(doc))
    (output / "reclassified-tasks.json").write_bytes(canonical(rows))
    print("RESUME_MANIFEST_SHA256=" + digest(output / "resume-manifest.json"))
    print("DERIVED_EVIDENCE_ONLY; HISTORICAL_ATTEMPT_UNCHANGED")


if __name__ == "__main__":
    main()
