"""V2 rules preserved; new controls and explicit all-task eligibility."""

import json
from typing import Any

from experiments.kaggle.forgeai_model_quality_1.contracts import (
    Rejected,
    decode,
    review,
)
from scripts.kisski_coding_eval.pack import Task
from scripts.kisski_coding_eval_v2 import pack as v2_pack
from scripts.kisski_coding_eval_v2 import scoring as v2
from scripts.kisski_coding_eval_v2.scoring import empty as empty
from scripts.kisski_coding_eval_v2.scoring import passed as passed

from .pack import CLEAN_REFS, EXPECTED, EXPECTED_DECISIONS, MATERIAL, TASKS


def score(task: Task, raw: str) -> dict[str, Any]:
    if task in v2_pack.TASKS:
        return v2.score(task, raw)
    result = empty(task)
    try:
        value, plain = decode(raw)
        result["fenced"] = not plain
        document = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        value, _ = review(document, {"proposal", *MATERIAL[task.task_id]})
        result.update(
            schema_valid=True,
            instruction_adherence=True,
            scope_discipline=True,
        )
        findings = value["findings"]
        decision = EXPECTED_DECISIONS[task.task_id]
        if task.task_id == "review_clean2":
            # V2 scoring.score clean-control branch: only blocking false positives.
            blocking = [f for f in findings if f["severity"] == "blocking"]
            clean = {ref for f in blocking for ref in f["evidence_refs"]}
            result.update(
                reviewer_true_positives=0,
                reviewer_false_positives=len(blocking),
                reviewer_clean_patches_flagged=len(clean & CLEAN_REFS[task.task_id]),
                reviewer_missed_critical=0,
            )
            accepted = value["decision"] == decision and not blocking
        else:
            # V2 scoring.score:72-110 matching order, applied to new expected maps.
            expected = EXPECTED[task.task_id]
            found: set[str] = set()
            clean = set()
            false = 0
            for finding in findings:
                refs = set(finding["evidence_refs"]) & set(expected)
                matched = {
                    ref
                    for ref in refs
                    if finding["category"] == expected[ref]
                    and finding["severity"] == "blocking"
                    and finding["required_action"]
                }
                clean_refs = set(finding["evidence_refs"]) & CLEAN_REFS[task.task_id]
                clean.update(clean_refs)
                if len(matched) == 1 and not matched & found and not clean_refs:
                    found.update(matched)
                else:
                    false += 1
            result.update(
                reviewer_true_positives=len(found),
                reviewer_false_positives=false,
                reviewer_clean_patches_flagged=len(clean),
                reviewer_missed_critical=sum(
                    category == "security" and ref not in found
                    for ref, category in expected.items()
                ),
            )
            accepted = (
                value["decision"] == decision and found == set(expected) and false == 0
            )
        result.update(
            acceptance_criteria_met=accepted, reasoning_sufficiency_proxy=accepted
        )
    except Rejected as error:
        code = str(error)
        result["failure_category"] = (
            code
            if code in {"SCHEMA_INVALID", "REFERENCE_INVALID"}
            else "OUTPUT_INVALID"
        )
    return result


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    # V2 summarize:134 onward, with 22 records and no review-only admission bypass.
    tasks: dict[str, Any] = {}
    complete = True
    for task in TASKS:
        group = [row for row in rows if row.get("task_id") == task.task_id]
        count = 1 if task.phase == "A" else 2
        intact = (
            len(group) == count
            and {row.get("repeat") for row in group} == set(range(1, count + 1))
            and all(row.get("invocation_outcome") == "completed" for row in group)
        )
        successes = sum(passed(row) for row in group)
        tasks[task.task_id] = {
            "passed": intact and successes == count,
            "complete": intact,
            "attempted": len(group),
            "repeatability": (
                f"{min(successes, 2)}_OF_2" if count == 2 else "NOT_MEASURED"
            ),
        }
        complete = complete and intact
    complete = complete and len(rows) == 22
    qualified = complete and all(item["passed"] for item in tasks.values())
    heldout = {name: tasks[name] for name in MATERIAL}
    return {
        "tasks": tasks,
        "qualified_all_tasks": qualified,
        "heldout_only": {
            "informational_only": True,
            "passed": all(item["passed"] for item in heldout.values()),
            "tasks": heldout,
        },
        "classification": (
            "RESULT_INCONCLUSIVE"
            if not complete
            else "MODEL_QUALIFIED_FOR_FORGEAI_CODING"
            if qualified
            else "MODEL_NOT_QUALIFIED"
        ),
        "coder_score": 100 if qualified else None,
        "reviewer_score": (
            100
            if complete
            and all(tasks[t.task_id]["passed"] for t in TASKS if t.role == "reviewer")
            else None
        ),
        "admission_effect": "NONE",
    }
