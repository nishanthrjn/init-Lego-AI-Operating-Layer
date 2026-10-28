"""Pure closed diagnostics layered on the unchanged frozen scorer."""

import ast
from collections import Counter
from typing import Any

from experiments.kaggle.forgeai_model_quality_1.contracts import (
    Rejected,
    coding,
    decode,
    review,
)
from scripts.kisski_coding_eval.pack import (
    OUTPUT_TOKENS,
    REVIEW_MATERIAL,
    VERSION,
    Task,
    digest,
)
from scripts.kisski_coding_eval.scoring import classify, score

EVALUATION = "FORGEAI-KISSKI-DEV-SCREEN-2"
NOTICE = (
    "Diagnosis, not admission. A fresh unchanged frozen evaluation "
    "(pack digest 2bab09bd...) under its unchanged all-dimensions rule, "
    "followed by a separate admission review, is required."
)


def configuration(output_tokens: int) -> str:
    if output_tokens not in (1024, 2048, 4096):
        raise ValueError("OUTPUT_TOKENS_INVALID")
    return (
        "FROZEN_OUTPUT_TOKENS"
        if output_tokens == OUTPUT_TOKENS
        else "DEV_VARIANT_OUTPUT_TOKENS"
    )


def unevaluated() -> dict[str, Any]:
    return {
        "adherence_evaluated": False,
        "adherence_reasons": [],
        "observations": [],
        "rejected_category": None,
        "reviewer_evaluated": False,
        "reviewer_references": {},
        "false_positive_causes": {},
        "reviewer_rejection_causes": {},
        "abstention_reasons": [],
    }


def finding_cause(finding: dict[str, Any], found: set[str]) -> tuple[set[str], str]:
    """Explain the frozen matching predicate; never award or change score credit.

    Filter by category/severity/action FIRST, then count matched references,
    then check duplicate and clean references, as scoring.score does. Two
    supplied refs with only one matching category can therefore earn credit.
    """
    expected = {"r1": "correctness", "r2": "correctness", "r3": "security"}
    references = finding.get("evidence_refs")
    if (
        not isinstance(references, list)
        or not all(isinstance(ref, str) for ref in references)
        or finding.get("category")
        not in (
            "correctness",
            "architecture",
            "security",
            "maintainability",
            "testing",
            "performance",
            "documentation",
        )
        or finding.get("severity") not in ("info", "warning", "blocking")
        or not isinstance(finding.get("required_action"), (str, type(None)))
    ):
        return set(), "OTHER"
    refs = set(references) & set(expected)
    category_refs = {r for r in refs if finding.get("category") == expected[r]}
    blocking = finding.get("severity") == "blocking"
    action = finding.get("required_action")
    matched = category_refs if blocking and action else set()
    clean = set(references) & {"r4", "r5"}
    if len(matched) == 1 and not matched & found and not clean:
        return matched, ""
    if refs and not category_refs:
        return set(), "WRONG_CATEGORY"
    if category_refs and not blocking:
        return set(), "NOT_BLOCKING"
    if category_refs and not action:
        return set(), "NO_REQUIRED_ACTION"
    if len(matched) > 1:
        return set(), "MULTIPLE_REFS"
    if matched & found:
        return set(), "DUPLICATE_REF"
    if clean:
        return set(), "CLEAN_REF"
    return set(), "UNSUPPLIED_REF"


def reviewer_facts(value: dict[str, Any], *, evaluated: bool) -> dict[str, Any]:
    found: set[str] = set()
    clean: set[str] = set()
    causes: Counter[str] = Counter()
    findings = value.get("findings")
    if not isinstance(findings, list) or len(findings) > 8:
        return {"reviewer_rejection_causes": {"OTHER": 1}}
    for finding in findings:
        if not isinstance(finding, dict):
            causes["OTHER"] += 1
            continue
        matched, cause = finding_cause(finding, found)
        refs = finding.get("evidence_refs")
        if (
            not evaluated
            and isinstance(refs, list)
            and all(isinstance(ref, str) for ref in refs)
            and not set(refs) <= {"proposal", *REVIEW_MATERIAL}
        ):
            # review() rejects unknown supplied IDs before scoring any findings.
            matched, cause = set(), "UNSUPPLIED_REF"
        if cause:
            causes[cause] += 1
        else:
            found.update(matched)
        if isinstance(refs, list):
            clean.update(r for r in ("r4", "r5") if r in refs)
    if not evaluated:
        # Rejected findings never become v1 false positives or missed defects.
        return {
            "reviewer_rejection_causes": dict(sorted(causes.items())) or {"OTHER": 1}
        }
    return {
        "reviewer_evaluated": True,
        "false_positive_causes": dict(sorted(causes.items())),
        "reviewer_references": {
            **{r: "found" if r in found else "missed" for r in ("r1", "r2", "r3")},
            **{
                r: "flagged_clean" if r in clean else "not_flagged"
                for r in ("r4", "r5")
            },
        },
    }


def diagnose(task: Task, raw: str) -> dict[str, Any]:
    frozen = score(task, raw)
    result = unevaluated()
    result["rejected_category"] = frozen["failure_category"]
    try:
        value, plain = decode(raw)
    except Rejected:
        return result
    if frozen["failure_category"] is not None:
        if task.task_id == "review":
            result.update(reviewer_facts(value, evaluated=False))
        return result
    reasons: list[str] = [] if plain else ["FENCED_JSON"]
    observations: list[str] = []
    if task.role == "coding":
        files, _ = coding(raw, {file.path: "update" for file in task.files})
        if frozen["patch_applies"] is False:
            observations.append("TARGET_SET_MISMATCH")
        elif frozen["patch_applies"] is True:
            # The frozen language/check gates have already succeeded. Reuse their
            # exact positional argument-name comparison; do not evaluate code.
            for file in task.files:
                tree = ast.parse(files[file.path])
                actual = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
                reference = ast.parse(file.reference).body[0]
                assert isinstance(reference, ast.FunctionDef)
                if [a.arg for a in actual.args.args] != [
                    a.arg for a in reference.args.args
                ]:
                    reasons.append("SIGNATURE_CHANGED:" + file.path)
                if task.task_id == "refactor" and any(
                    isinstance(n, ast.If) and n.orelse for n in ast.walk(tree)
                ):
                    reasons.append("ELSE_RETAINED")
            if frozen["reasoning_sufficiency_proxy"] is False:
                observations.extend(
                    "REASON_EMPTY:" + file.path
                    for file in task.files
                    for change in value["changes"]
                    if change["path"] == file.path and not change["reason"].strip()
                )
    else:
        supplied = {"proposal"}
        if task.task_id == "review":
            supplied.update(REVIEW_MATERIAL)
        value, _ = review(raw, supplied)
        if task.task_id == "review":
            result.update(reviewer_facts(value, evaluated=True))
        else:
            result["abstention_reasons"] = [
                code
                for condition, code in (
                    (
                        value["decision"] != "insufficient_evidence",
                        "DECISION_NOT_INSUFFICIENT",
                    ),
                    (not value["unknowns"], "UNKNOWNS_EMPTY"),
                    (bool(value["findings"]), "FINDINGS_PRESENT"),
                )
                if condition
            ]
    result.update(
        adherence_evaluated=True,
        adherence_reasons=sorted(reasons),
        observations=sorted(observations),
    )
    return result


def task_row(
    task: Task, raw: str, output_tokens: int = OUTPUT_TOKENS
) -> dict[str, Any]:
    """All v1 fields come only from score(), without diagnostic overrides."""
    row = score(task, raw)
    row.update(
        diagnostics=diagnose(task, raw),
        configuration=configuration(output_tokens),
        comparable_with_frozen=output_tokens == OUTPUT_TOKENS,
    )
    return row


def report(
    phase: str,
    rows: list[dict[str, Any]],
    manifest_digest: str,
    output_tokens: int,
    models: tuple[str, ...],
    *,
    completed: bool,
) -> dict[str, Any]:
    summaries = {}
    for model in models:
        records = [row for row in rows if row["model_id"] == model]
        reasons: Counter[str] = Counter()
        for row in records:
            reasons.update(row["diagnostics"]["adherence_reasons"])
        frozen = classify(records)
        summaries[model] = {
            "task_outcomes": {
                row["task_id"]: {
                    "invocation_outcome": row["invocation_outcome"],
                    "acceptance_criteria_met": row["acceptance_criteria_met"],
                }
                for row in records
            },
            "adherence_reason_counts": dict(sorted(reasons.items())),
            "reviewer_reference_outcomes": {
                row["task_id"]: row["diagnostics"]["reviewer_references"]
                for row in records
                if row["role"] == "reviewer"
            },
            "frozen_rule_would_pass": (
                None
                if frozen["classification"] == "RESULT_INCONCLUSIVE"
                else frozen["classification"] == "MODEL_QUALIFIED_FOR_FORGEAI_CODING"
            ),
            "frozen_rule_information_only": True,
        }
    return {
        "evaluation": EVALUATION,
        "frozen_evaluation": VERSION,
        "frozen_pack_digest": digest(),
        "frozen_manifest_digest": manifest_digest,
        "phase": phase,
        "screening_bypassed": True,
        "configuration": configuration(output_tokens),
        "requested_output_tokens": output_tokens,
        "admission_effect": "NONE",
        "notice": NOTICE,
        "completed": completed,
        "records": rows,
        "summaries": summaries,
    }
