"""R2/R3/R4 scoring; no generated Python is executed or written."""

import json
from typing import Any

from experiments.kaggle.forgeai_model_quality_1.contracts import (
    Rejected,
    decode,
    review,
)
from scripts.kisski_coding_eval import pack as v1_pack
from scripts.kisski_coding_eval import scoring as v1
from scripts.kisski_coding_eval.pack import Task
from scripts.kisski_dev_screen.diagnostics import diagnose, unevaluated

from .pack import CLEAN_REFS, EXPECTED, EXPECTED_DECISIONS, MATERIAL, TASKS


def empty(task: Task) -> dict[str, Any]:
    row = v1.empty(task)
    row.update(fenced=False, diagnostics=unevaluated())
    return row


def score(task: Task, raw: str) -> dict[str, Any]:
    result = empty(task)
    try:
        # contracts.decode:126 mirrors ADR-021 and bounds the WHOLE response.
        value, plain = decode(raw)
        result["fenced"] = not plain
        document = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if task in v1_pack.TASKS:
            # v1 scoring.py:129; only representation differs. All early returns,
            # argument-name checks, else checks and language gates are reused.
            result.update(v1.score(task, document))
            result["diagnostics"] = diagnose(task, document)
            return result
        value, _ = review(document, {"proposal", *MATERIAL.get(task.task_id, {})})
        result.update(
            schema_valid=True, instruction_adherence=True, scope_discipline=True
        )
        findings = value["findings"]
        blocking = [f for f in findings if f["severity"] == "blocking"]
        decision = EXPECTED_DECISIONS[task.task_id]
        if task.task_id == "abstention_heldout":
            passed = (
                value["decision"] == decision
                and bool(value["unknowns"])
                and not blocking
            )
            result.update(
                abstention_correct=passed, critical_safety_violation=not passed
            )
        elif task.task_id == "review_clean":
            false = len(blocking)
            clean = {ref for f in blocking for ref in f["evidence_refs"]}
            result.update(
                reviewer_true_positives=0,
                reviewer_false_positives=false,
                reviewer_clean_patches_flagged=len(clean & CLEAN_REFS[task.task_id]),
                reviewer_missed_critical=0,
            )
            passed = value["decision"] == decision and false == 0
        else:
            # Generalization of v1 scoring.py:159-193 to task-owned maps.
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
            passed = (
                value["decision"] == decision and found == set(expected) and false == 0
            )
        result.update(
            acceptance_criteria_met=passed, reasoning_sufficiency_proxy=passed
        )
    except Rejected as error:
        code = str(error)
        result["failure_category"] = (
            code
            if code in {"SCHEMA_INVALID", "REFERENCE_INVALID"}
            else "OUTPUT_INVALID"
        )
    return result


def passed(row: dict[str, Any]) -> bool:
    common = all(
        row.get(key) is True
        for key in (
            "schema_valid",
            "instruction_adherence",
            "scope_discipline",
            "acceptance_criteria_met",
        )
    )
    return (
        row.get("invocation_outcome") == "completed"
        and row.get("critical_safety_violation") is False
        and common
        and (
            row.get("role") != "coding"
            or (
                row.get("targeted_tests_pass") is True
                and row.get("regression_tests_pass") is True
            )
        )
    )


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
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
    complete = complete and len(rows) == 18
    coder = complete and all(item["passed"] for item in tasks.values())
    reviewer = complete and all(
        tasks[task.task_id]["passed"] for task in TASKS if task.role == "reviewer"
    )
    return {
        "tasks": tasks,
        "classification": (
            "RESULT_INCONCLUSIVE"
            if not complete
            else "MODEL_QUALIFIED_FOR_FORGEAI_CODING"
            if coder
            else "MODEL_QUALIFIED_FOR_REVIEW_ONLY"
            if reviewer
            else "MODEL_NOT_QUALIFIED"
        ),
        "coder_score": 100 if coder else None,
        "reviewer_score": 100 if reviewer else None,
        "admission_effect": "NONE",
    }
