"""Observation-bound tool argument rejection metrics; no model or tool execution."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

PHRASE = "mandatory input parameters are not present"
EDIT_TOOLS = {"edit_file", "write_file"}


HEREDOC_METHOD = "QUOTED_EOF_SOURCE_EDIT_HEURISTIC_V1"


def heredoc_counts(call):
    """Count actual calls, not echoed text; syntax heuristic, not successful effects.

    Exact <<'EOF' substring; prefix before first << must not contain /tmp.
    Body is the text after the opener line and before a standalone EOF line.
    Any of the literal tokens read_text, write_text, replace( qualifies the body.
    Each call counts at most once, including commands with multiple heredocs.
    """
    arguments = call.get("arguments")
    command = arguments.get("command") if isinstance(arguments, dict) else None
    if call.get("function_name") != "run_command" or not isinstance(command, str):
        return 0, 0
    opener = "<<'EOF'"
    if opener not in command:
        return 0, 0
    prefix = command.split("<<", 1)[0]
    after = command.split(opener, 1)[1]
    _, newline, body = after.partition("\n")
    body = re.split(r"(?m)^EOF\r?$", body, maxsplit=1)[0] if newline else ""
    source_edit = "/tmp" not in prefix and any(token in body for token in ("read_text", "write_text", "replace("))
    return 1, int(source_edit)

def inspect_trace(trace):
    if not isinstance(trace, dict) or not isinstance(trace.get("steps"), list):
        raise ValueError("trace steps missing")
    attempted, rejected, unknown, resends = Counter(), Counter(), Counter(), Counter()
    source_edits = 0
    heredocs = source_heredocs = 0
    previous = None
    streak = maximum = consecutive_resends = 0
    for step in trace["steps"]:
        if not isinstance(step, dict):
            raise ValueError("invalid trace step")
        calls = step.get("tool_calls") or []
        if step.get("source") != "agent":
            if calls:
                previous, streak = None, 0
            continue
        if not isinstance(calls, list):
            raise ValueError("invalid tool calls")
        observation = step.get("observation") or {}
        extra = observation.get("extra") or {}
        response_id = extra.get("tool_call_id") or observation.get("source_call_id")
        tool_name = extra.get("tool_name")
        candidates = [i for i, call in enumerate(calls)
                      if (call.get("tool_call_id") == response_id if response_id
                          else call.get("function_name") == tool_name)]
        matched = candidates[0] if len(candidates) == 1 else None
        content = observation.get("content")
        for index, call in enumerate(calls):
            name = call.get("function_name")
            if not isinstance(name, str) or not name:
                raise ValueError("missing function name")
            attempted[name] += 1
            total, edits = heredoc_counts(call)
            heredocs += total
            source_heredocs += edits
            known = index == matched and isinstance(content, str)
            is_rejected = known and PHRASE in content.lower()
            if not known:
                unknown[name] += 1
            if is_rejected:
                rejected[name] += 1
            if known and not is_rejected and name == "run_command":
                try:
                    response = json.loads(content)
                except (ValueError, TypeError):
                    response = content
                output = response.get("stdout", "") if isinstance(response, dict) else response
                if isinstance(output, str):
                    source_edits += sum(line.strip() == "FORGEAI_SOURCE_EDIT_COMPLETED" for line in output.splitlines())
            fingerprint = (name, json.dumps(call.get("arguments"), sort_keys=True, ensure_ascii=False))
            repeat = previous is not None and previous == fingerprint
            if repeat:
                resends[name] += 1
                consecutive_resends += 1
            if is_rejected:
                streak = streak + 1 if repeat else 1
                maximum = max(maximum, streak)
                previous = fingerprint
            else:
                previous, streak = None, 0
    count = sum(attempted[t] for t in EDIT_TOOLS)
    rejected_count = sum(rejected[t] for t in EDIT_TOOLS)
    unknown_count = sum(unknown[t] for t in EDIT_TOOLS)
    return {"status": "OBSERVED", "attempted_by_tool": dict(attempted),
            "rejected_by_tool": dict(rejected), "unmatched_observations_by_tool": dict(unknown),
            "identical_resends_by_tool": dict(resends),
            "consecutive_identical_resends": consecutive_resends,
            "max_consecutive_identical_rejections": maximum,
            "edit_write_attempted": count, "edit_write_rejected": rejected_count,
            "edit_write_unknown": unknown_count,
            "rejection_rate": rejected_count / count if count and not unknown_count else None,
            "all_tool_attempted": sum(attempted.values()),
            "all_tool_rejected": sum(rejected.values()),
            "all_tool_rejection_rate": sum(rejected.values()) / sum(attempted.values())
                if attempted and not unknown else None,
            "run_command_source_edits_evidenced": source_edits,
            "run_command_heredoc_calls": heredocs,
            "run_command_heredoc_edits_observed": source_heredocs,
            "heredoc_count_method": HEREDOC_METHOD,
            "source_edit_count_status": "MARKER_EVIDENCED_LOWER_BOUND; UNMARKED_EDITS_REQUIRE_REVIEW",
            "zero_edit_attempts": count == 0,
            "failure_categories": ["TOOL_ARGUMENT_REJECTED"] if rejected else []}


def task_report(root, task_id):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", task_id):
        raise ValueError("unsafe trace task identity")
    directory = Path(root) / "official/traces"
    path = directory / ("trace_" + task_id + ".json")
    if not path.resolve().is_relative_to(directory.resolve()):
        raise ValueError("trace escapes run directory")
    if not path.is_file():
        return {"status": "MISSING", "rejection_rate": None, "all_tool_rejection_rate": None,
                "run_command_source_edits_evidenced": None, "run_command_heredoc_calls": None,
                "run_command_heredoc_edits_observed": None, "failure_categories": []}
    raw = path.read_bytes()
    return {"trace_file": str(path), "trace_sha256": hashlib.sha256(raw).hexdigest(),
            **inspect_trace(json.loads(raw))}


def aggregate(reports):
    reports = list(reports)
    observed = [r for r in reports if r.get("status") == "OBSERVED"]
    attempted, rejected, unknown, resends = Counter(), Counter(), Counter(), Counter()
    for report in observed:
        attempted.update(report["attempted_by_tool"])
        rejected.update(report["rejected_by_tool"])
        unknown.update(report["unmatched_observations_by_tool"])
        resends.update(report["identical_resends_by_tool"])
    trace_complete = bool(reports) and len(observed) == len(reports)
    count = sum(attempted[t] for t in EDIT_TOOLS)
    numerator = sum(rejected[t] for t in EDIT_TOOLS)
    complete = bool(reports) and len(observed) == len(reports) and not sum(unknown[t] for t in EDIT_TOOLS)
    return {"trace_tasks": len(observed), "missing_trace_tasks": len(reports) - len(observed),
            "coverage_complete": complete, "all_tool_coverage_complete": complete and not unknown, "attempted_by_tool": dict(attempted),
            "rejected_by_tool": dict(rejected), "unmatched_observations_by_tool": dict(unknown),
            "identical_resends_by_tool": dict(resends),
            "consecutive_identical_resends": sum(r["consecutive_identical_resends"] for r in observed),
            "max_consecutive_identical_rejections": max((r["max_consecutive_identical_rejections"] for r in observed), default=0),
            "edit_write_attempted": count, "edit_write_rejected": numerator,
            "rejection_rate": numerator / count if complete and count else None,
            "all_tool_attempted": sum(attempted.values()),
            "all_tool_rejected": sum(rejected.values()),
            "all_tool_rejection_rate": sum(rejected.values()) / sum(attempted.values())
                if complete and not unknown and attempted else None,
            "run_command_source_edits_evidenced": sum(r["run_command_source_edits_evidenced"] for r in observed),
            "run_command_heredoc_calls": sum(r["run_command_heredoc_calls"] for r in observed) if trace_complete else None,
            "run_command_heredoc_edits_observed": sum(r["run_command_heredoc_edits_observed"] for r in observed) if trace_complete else None,
            "heredoc_count_method": HEREDOC_METHOD,
            "heredoc_trace_coverage_complete": trace_complete,
            "zero_edit_attempts": complete and count == 0,
            "definition": "Rejected matched edit_file/write_file observations / attempted edit_file/write_file calls; zero denominator or incomplete coverage is null, not zero."}
