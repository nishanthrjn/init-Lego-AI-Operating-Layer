"""P10 operational eligibility for one public measurement; no accuracy gate."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent / "results/dev-16v-comparison.json"
SUBMISSIONS = HERE.parent / "results/submissions.json"
ZIP_SHA256 = "89a84bf709b52858b3a3ce39f33d713501dec1fe00e0fb04164f271158f333d6"
MANIFEST_SHA256 = "06324d20e0a7510f6fa5a40f83b1a922feace6e64054c11c1e9846261bc5579a"
MODEL = "gemma-4-31b-it-qat-w4a16-ct"


def require_qualification_gate(path=EVIDENCE, submissions=SUBMISSIONS):
    raw, selection_raw = Path(path).read_bytes(), Path(submissions).read_bytes()
    doc, registry = json.loads(raw), json.loads(selection_raw)
    amendment = doc.get("p10_timing_amendment", {})
    if any(amendment.get(k) != v for k, v in {
        "id": "P10-FRIEND-ATTEMPT2-TIMING-1", "status": "AUTHORIZED_RUN_IDENTITY_ONLY",
        "attempt": 2, "effective_method": "REPO_ANALYSIS_116_TASK_BOOTSTRAP_V1",
        "attempt1_recording": "DEFERRED_UNTIL_AFTER_BOTH_SUBMISSIONS",
    }.items()):
        raise ValueError("P10 requires the explicit run-identity-only amendment")
    run = doc.get("p10_attempt2", {})
    expected = {
        "candidate": "p10", "subset": "dev-16v", "attempt": 2, "state": "COMPLETED",
        "complete": True, "tasks": 16, "verifiable": 16,
        "controls_status": "PINNED_CONTROLS_APPLIED", "time_fit_gate": "PASS",
        "bootstrap_method": "REPO_ANALYSIS_116_TASK_BOOTSTRAP_V1",
        "zip_sha256": ZIP_SHA256, "manifest_sha256": MANIFEST_SHA256,
        "zip_size": 6501, "model_variant": MODEL,
        "tool_argument_rejection_definition": "mandatory input parameters are not present",
    }
    if any(type(run.get(k)) is not type(v) or run[k] != v for k, v in expected.items()):
        raise ValueError("P10 requires completed pinned-control repo evidence and exact evaluated identity")
    if type(run.get("harness_errors")) is not int or run["harness_errors"] != 0:
        raise ValueError("P10 requires zero known harness errors")
    calls, rejected = run.get("all_tool_attempted"), run.get("all_tool_rejected")
    if (type(calls) is not int or calls <= 0 or type(rejected) is not int
            or not 0 <= rejected <= calls or rejected / calls > 0.05):
        raise ValueError("P10 requires known exact-phrase rejections/all calls <=5%")
    bound = run.get("bootstrap_upper95_hours")
    if type(bound) not in (int, float) or not math.isfinite(bound) or not 0 <= bound <= 11:
        raise ValueError("P10 repo bootstrap upper95 must be <=11 hours")
    selection = registry.get("p10_local_selection", {})
    if any(selection.get(k) != v for k, v in {
        "candidate": "p10", "purpose": "EXPLORATORY_LB_MEASUREMENT", "status": "NOT_SUBMITTED",
        "gate": "PASSED", "eligibility_attempt": 2, "adopt_public_score_at_least": 0.17,
    }.items()):
        raise ValueError("P10 exploratory authorization missing")
    if (type(selection.get("submissions_used")) is not int or selection["submissions_used"] != 0
            or type(selection.get("maximum_submissions_after_gate")) is not int
            or selection["maximum_submissions_after_gate"] != 1 or selection.get("public_score") is not None):
        raise ValueError("P10 single public measurement already consumed or malformed")
    if any(r.get("candidate") == "p10" and
           (r.get("status") != "NOT_SUBMITTED" or r.get("public_score") is not None)
           for r in registry.get("runs", [])):
        raise ValueError("P10 public submission already recorded")
    return {"development_gate": "PASSED", "local_adoption": "NOT_ADOPTED",
            "qualification_purpose": "EXPLORATORY_LB_MEASUREMENT",
            "model_variant": MODEL, "maximum_submissions": 1,
            "adopt_public_score_at_least": 0.17,
            "development_evidence_sha256": hashlib.sha256(raw).hexdigest(),
            "selection_evidence_sha256": hashlib.sha256(selection_raw).hexdigest()}


def main():
    from qualify_p3 import main as prepare
    prepare("p10", guard=require_qualification_gate, external_only=True)


if __name__ == "__main__":
    main()
