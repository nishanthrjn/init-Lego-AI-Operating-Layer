"""Offline retained-agent trace review. Outputs must remain outside Git."""
import argparse
import json
from pathlib import Path
import re
from analysis import canonical, sha


def review(trace):
    turns, submissions, edits, statuses = [], [], [], []
    previous_end = None
    for step in trace.get("steps", []):
        if step.get("source") != "agent":
            continue
        start = step.get("extra", {}).get("elapsed_s")
        observation = step.get("observation", {})
        end = observation.get("extra", {}).get("elapsed_s")
        metrics = step.get("metrics", {})
        turn = {"step_id": step.get("step_id"), "elapsed_s": start,
                "model_seconds": None,
                "model_plus_overhead_gap_seconds": max(0, start - previous_end) if start is not None and previous_end is not None else None,
                "tool_observation_interval_seconds": max(0, end - start) if end is not None and start is not None else None,
                "thinking_tokens": metrics.get("thinking_tokens", metrics.get("reasoning_tokens")),
                "llm_call_count": step.get("llm_call_count")}
        turns.append(turn)
        for call in step.get("tool_calls", []):
            name = call.get("function_name")
            response = observation.get("content") if observation.get("extra", {}).get("tool_name") == name else None
            record = {"step_id": step.get("step_id"), "elapsed_s": call.get("extra", {}).get("elapsed_s", start),
                      "tool_call_id": call.get("tool_call_id"), "tool": name, "response": response}
            if name == "submit_patch":
                submissions.append(record)
            args = call.get("arguments", {})
            command = args.get("command", "") if isinstance(args, dict) else ""
            if name in {"edit_file", "write_file", "apply_patch", "str_replace"}:
                edits.append(record)
            elif name == "run_command" and re.search(r"\b(sed\s+-i|apply_patch|tee)\b|(?<![=>])>{1,2}(?![=>])", command):
                edits.append(dict(record, certainty="shell_edit_candidate_only"))
            if name == "run_command" and re.search(r"\bgit\s+status\b", command):
                statuses.append(record)
        previous_end = end if end is not None else start
    return {"turns": turns, "first_observed_edit_attempt": edits[0] if edits else None,
            "submit_patch_calls": submissions,
            "last_recorded_git_status": statuses[-1] if statuses else None,
            "final_git_status": None,
            "limitations": "Step IDs are trace steps, not guaranteed model turns. Timing deltas include overhead. Edit attempts do not prove successful mutation; script edits may be unrecognizable. Last status may precede later edits; final status is UNKNOWN. Missing token fields remain null."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("task_ids", nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    repository = Path(__file__).resolve().parents[3]
    if output.is_relative_to(repository) or any((p / ".git").exists() for p in output.parents):
        raise ValueError("trace reports must remain outside repositories")
    meta = json.loads((args.run / "run.json").read_bytes())
    reports = {}
    for task_id in args.task_ids:
        if task_id not in meta["task_ids"] or not re.fullmatch(r"[A-Za-z0-9_.-]+", task_id):
            raise ValueError("unknown task identity")
        path = args.run / "official/traces" / ("trace_" + task_id + ".json")
        reports[task_id] = {"trace_sha256": sha(path), **review(json.loads(path.read_bytes()))}
    with output.open("xb") as stream:
        stream.write(canonical(reports))


if __name__ == "__main__":
    main()
