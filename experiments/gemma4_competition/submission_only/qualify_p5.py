"""P5 submission preparation: require two-run adoption, then shared reconciliation."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent / "results/dev-16v-comparison.json"


def require_two_run_gate(path=EVIDENCE):
    raw = Path(path).read_bytes()
    doc = json.loads(raw)
    if doc.get("p5_adoption_decision", {}).get("status") != "PASSED":
        raise ValueError("P5 submission blocked: recorded two-run decision must be PASSED")

    def number(value, label, maximum=None, integer=False):
        if (type(value) not in (int, float) or not math.isfinite(value) or value < 0
                or (integer and type(value) is not int) or (maximum is not None and value > maximum)):
            raise ValueError("P5 submission blocked: missing/invalid " + label)
        return value

    baseline = doc.get("tool_argument_rejection_evidence", {}).get("patch_production_baseline", {})
    if baseline.get("tasks_per_run") != 16:
        raise ValueError("P5 submission blocked: two P3 dev-16v patch baselines required")
    patch_mean = sum(number(baseline.get(k), k, 16, True)
                     for k in ("p3_attempt1", "p3_attempt2")) / 2
    solved = []
    retained = set()
    for attempt in (1, 2):
        run = doc.get(f"p5_attempt{attempt}", {})
        if (run.get("candidate") != "p5" or run.get("subset") != "dev-16v"
                or type(run.get("attempt")) is not int or run["attempt"] != attempt
                or run.get("state") != "COMPLETED" or run.get("verifiable") != 16):
            raise ValueError("P5 submission blocked: two complete independent dev-16v runs required")
        location = run.get("retained_path")
        if not isinstance(location, str) or not location.strip() or location.casefold() in retained:
            raise ValueError("P5 submission blocked: distinct retained run paths required")
        retained.add(location.casefold())
        solved.append(number(run.get("resolved"), "resolved", 16, True))
        calls = number(run.get("all_tool_attempted"), "tool calls", integer=True)
        rejected = number(run.get("all_tool_rejected"), "rejections", calls, True)
        if calls == 0 or rejected / calls > 0.05:
            raise ValueError("P5 submission blocked: all-tool rejection gate failed")
        patches = number(run.get("nonempty_patch_tasks"), "patch count", 16, True)
        if patches < patch_mean:
            raise ValueError("P5 submission blocked: patch production below P3 mean")
        if number(run.get("bootstrap_upper95_hours_approx"), "bootstrap upper95 hours") > 11:
            raise ValueError("P5 submission blocked: bootstrap time-fit exceeds 11 h")
        if number(run.get("run_command_heredoc_edits_observed"), "observed source edits", integer=True) == 0:
            raise ValueError("P5 submission blocked: source-edit evidence required")
    if sum(solved) / 2 < 7:
        raise ValueError("P5 submission blocked: two-run mean solved below 7")
    return {"development_gate": "PASSED", "development_evidence_sha256": hashlib.sha256(raw).hexdigest()}


def main():
    from qualify_p3 import main as prepare
    prepare("p5", guard=require_two_run_gate)


if __name__ == "__main__":
    main()
