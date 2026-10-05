"""ANALYST-INSUFFICIENT-DIAG-1 report: aggregates folded from records, decision rule.

No composite score and no quality metric. The next-decision rule was declared
before any diagnostic run (planning/FORGEAI-ANALYST-INSUFFICIENT-DIAGNOSTIC.md)
and is a decision only for a live run; recorded and replay modes are previews.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from analyst_contract_diag1.diagnose import Stage

from analyst_insufficient_diag1.clauses import Abstention, Refined, abstention

SCHEMA = "forgeai-analyst-insufficient-diagnostic-report/1"
CONDITION_SCHEMA = "forgeai-analyst-insufficient-diagnostic-condition/1"
# Immutable CONTENT-DISCOVERY-1Q-R2 identity this diagnostic refines.
LINKAGE = {
    "r2_commit": "2e8f1ab8f401c01ec13c75b01041882ff6eea0a2",
    "r2_report_sha256": "e5a0efd31ff391ccafcc70d6f57bdca6ca8f69c994c28f3e99ab2671c199e49c",
    "r2_condition_sha256": "5b716ad7509992e4835932fab225423dfdca7590c2e01da8939f059097856c43",
    "r2_condition_digest": "5cd301942dd91cf6186f768ef6b86ad42a0bc8e131b41c855317a53eba4cfec3",
    "r2_decision": "B",
    "r2_heldout_validity": {"numerator": 59, "denominator": 72},
}
OUTCOMES = ("succeeded", "insufficient_evidence")
STATUSES = (*OUTCOMES, "unparsed")
PARTITIONS = ("heldout", "cd1_quality", "cd1_probe")
DECISIONS = {
    "A": "ANALYST INSUFFICIENT-EVIDENCE PROMPT CLARIFICATION JUSTIFIED",
    "B": "ANALYST ABSTENTION BEHAVIOR REQUIRES QUALITY DECISION",
    "C": "ANALYST CONTRACT SEMANTICS REQUIRE REVIEW",
    "D": "MIXED BLOCKER - FURTHER EVIDENCE REQUIRED",
}
LIMITATIONS = [
    "The refinement covers the first failure only; replies failing earlier stages "
    "are never refined.",
    "Counts are not content: a finding or unknown is counted, never read.",
    "A live diagnostic is a fresh sample of the r2 condition, not the r2 replies, "
    "which were never retained.",
    "Recorded mode folds the r2 records, which hold no findings/unknowns counts; "
    "it cannot split the insufficient_inconsistent clauses.",
    "Decision C is never selected mechanically; it requires a maintainer review.",
]


def _rate(numerator: int, denominator: int) -> dict[str, object]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": round(numerator / denominator, 4) if denominator else None,
    }


def _status(record: dict[str, object]) -> str:
    status = record["actual_status"]
    return str(status) if status in OUTCOMES else "unparsed"


def summarize(records: list[dict[str, object]]) -> dict[str, object]:
    invalid_abstentions = [
        r for r in records if r["stage"] == Stage.INSUFFICIENT_INCONSISTENT
    ]
    insufficient = [r for r in records if r["findings_count"] is not None]
    return {
        "calls": len(records),
        "valid": sum(1 for r in records if r["stage"] == Stage.VALID),
        "stages": dict(sorted(Counter(str(r["stage"]) for r in records).items())),
        "insufficient_inconsistent": len(invalid_abstentions),
        "refined": dict(
            sorted(
                Counter(
                    str(r["refined"]) if r["refined"] is not None else "not_recorded"
                    for r in invalid_abstentions
                ).items()
            )
        ),
        "actual_status": {
            s: sum(1 for r in records if _status(r) == s) for s in STATUSES
        },
        "expected": {
            e: sum(1 for r in records if r["expected"] == e) for e in OUTCOMES
        },
        "confusion": {
            e: {
                s: sum(1 for r in records if r["expected"] == e and _status(r) == s)
                for s in STATUSES
            }
            for e in OUTCOMES
        },
        "abstention": {
            a.value: {
                e: sum(
                    1 for r in records if r["abstention"] == a and r["expected"] == e
                )
                for e in OUTCOMES
            }
            for a in Abstention
        },
        "insufficient_counts": {
            "findings": dict(
                sorted(Counter(str(r["findings_count"]) for r in insufficient).items())
            ),
            "unknowns": dict(
                sorted(Counter(str(r["unknowns_count"]) for r in insufficient).items())
            ),
        },
        "model_failures": sum(1 for r in records if r["stage"] == Stage.MODEL_FAILURE),
        "classifier_disagreements": sum(
            1
            for r in records
            if r["stage"] == Stage.CLASSIFIER_DISAGREEMENT
            or r["category"] == "classifier_disagreement"
        ),
        "coarse_inconsistencies": sum(1 for r in records if not r["coarse_consistent"]),
        "refinement_inconsistencies": sum(
            1 for r in records if not r["refinement_consistent"]
        ),
    }


def fold(records: list[dict[str, object]]) -> dict[str, object]:
    by_case: dict[str, dict[str, int]] = {}
    for r in records:
        row = by_case.setdefault(str(r["case"]), {})
        row[str(r["abstention"])] = row.get(str(r["abstention"]), 0) + 1
    return {
        "all": summarize(records),
        "partitions": {
            p: summarize([r for r in records if r["partition"] == p])
            for p in PARTITIONS
        },
        "by_case": by_case,
    }


def decide(
    records: list[dict[str, object]], clauses_recorded: bool
) -> dict[str, object]:
    """The predeclared next-decision rule over the held-out partition."""
    held = [r for r in records if r["partition"] == "heldout"]
    calls = len(held)
    failures = sum(1 for r in held if r["stage"] == Stage.MODEL_FAILURE)
    integrity = sum(
        1
        for r in held
        if r["stage"] == Stage.CLASSIFIER_DISAGREEMENT
        or r["category"] == "classifier_disagreement"
        or not r["coarse_consistent"]
        or not r["refinement_consistent"]
    )
    answerable = [
        r for r in held if r["expected"] == "succeeded" and _status(r) != "unparsed"
    ]
    va = sum(1 for r in answerable if r["abstention"] == Abstention.VALID_ABSTENTION)
    invalid = [r for r in held if r["stage"] not in {Stage.VALID, Stage.MODEL_FAILURE}]
    ia = [r for r in invalid if r["stage"] == Stage.INSUFFICIENT_INCONSISTENT]
    refined = Counter(str(r["refined"]) for r in ia if r["refined"] is not None)
    top = refined.most_common(1)[0] if refined else ("none", 0)
    inputs = {
        "valid_abstention_share_of_answerable": _rate(va, len(answerable)),
        "invalid_abstention_share_of_invalid": _rate(len(ia), len(invalid)),
        "dominant_refined": top[0],
        "dominant_refined_share": _rate(top[1], len(ia)),
        "model_failure_rate": _rate(failures, calls),
        "integrity_failures": integrity,
    }
    code: str | None
    if integrity or (calls and failures / calls > 0.1):
        code = "D"
    elif answerable and va / len(answerable) >= 0.5:
        code = "B"
    elif invalid and len(ia) / len(invalid) >= 0.5:
        if not clauses_recorded:
            code = None
        elif top[1] / len(ia) >= 0.8:
            code = "A"
        else:
            code = "D"
    else:
        code = "D"
    label = (
        DECISIONS[code] if code else "CLAUSES NOT RECORDED - live diagnostic required"
    )
    return {"code": code, "label": label, "inputs": inputs}


def from_r2(record: dict[str, object]) -> dict[str, object]:
    """A recorded r2 record as a diagnostic record; clause counts were never kept."""
    status = record["status_value"]
    actual = str(status) if status in OUTCOMES else None
    return {
        "case": record["case"],
        "partition": record["partition"],
        "class": record["class"],
        "repetition": record["repetition"],
        "expected": record["expected"],
        "runtime_status": record["runtime_status"],
        "category": record["category"],
        "stage": record["stage"],
        "representation": record["representation"],
        "actual_status": actual,
        "abstention": abstention(str(record["stage"]), actual).value,
        "findings_count": None,
        "unknowns_count": None,
        "findings_present": None,
        "unknowns_empty": None,
        "refined": None,
        "refinement_consistent": True,
        "coarse_consistent": record["coarse_consistent"],
        "seconds": record["seconds"],
    }


def condition_digest(condition: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(condition, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build(
    condition: dict[str, object], records: list[dict[str, object]]
) -> dict[str, object]:
    mode = condition["mode"]
    decision = decide(records, clauses_recorded=mode != "recorded")
    if mode != "live":
        preview = "RECORDED R2 PREVIEW" if mode == "recorded" else "REPLAY ONLY"
        decision = {
            "code": None,
            "label": f"{preview} - not a decision",
            "preview_code": decision["code"],
            "inputs": decision["inputs"],
        }
    return {
        "schema": SCHEMA,
        "mode": mode,
        "condition": condition,
        "condition_digest": condition_digest(condition),
        "linkage": LINKAGE,
        "records": records,
        "aggregate": fold(records),
        "decision": decision,
        "refined_categories": [r.value for r in Refined],
        "limitations": LIMITATIONS,
    }


def _value(value: object) -> str:
    if isinstance(value, dict) and "numerator" in value:
        shown = "n/a" if value["value"] is None else f"{value['value']:.2%}"
        return f"{shown} ({value['numerator']}/{value['denominator']})"
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def render(report: dict[str, object]) -> str:
    """Markdown from the JSON report only."""
    aggregate, decision = report["aggregate"], report["decision"]
    assert isinstance(aggregate, dict) and isinstance(decision, dict)
    inputs = decision["inputs"]
    assert isinstance(inputs, dict)
    lines = [
        "# ANALYST-INSUFFICIENT-DIAG-1 report",
        "",
        f"**Mode:** {report['mode']}. **Decision:** {decision['code']} - "
        f"{decision['label']}",
        "",
        f"Condition digest `{report['condition_digest']}`.",
        "",
        "## Decision-rule inputs (held-out)",
        "",
        "| Input | Value |",
        "| --- | --- |",
        *(f"| {k} | {_value(v)} |" for k, v in inputs.items()),
        "",
        "## Linkage (CONTENT-DISCOVERY-1Q-R2, immutable)",
        "",
        "```json",
        json.dumps(report["linkage"], indent=2, sort_keys=True),
        "```",
        "",
        "## Condition",
        "",
        "```json",
        json.dumps(report["condition"], indent=2, sort_keys=True),
        "```",
    ]
    partitions = aggregate["partitions"]
    assert isinstance(partitions, dict)
    sections = [("All calls", aggregate["all"])]
    sections += [(f"Partition: {k}", v) for k, v in partitions.items()]
    for title, summary in sections:
        assert isinstance(summary, dict)
        lines += ["", f"## {title}", "", "| Metric | Value |", "| --- | --- |"]
        lines += [f"| {k} | {_value(v)} |" for k, v in summary.items()]
    lines += [
        "",
        "## Calls",
        "",
        "| Case | Partition | Rep | Expected | Actual | Stage | Abstention "
        "| Refined | Findings | Unknowns | s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    records = report["records"]
    assert isinstance(records, list)
    for r in records:
        lines.append(
            f"| {r['case']} | {r['partition']} | {r['repetition']} | {r['expected']} "
            f"| {r['actual_status'] or 'unparsed'} | {r['stage']} | {r['abstention']} "
            f"| {r['refined'] or '-'} | {_value(r['findings_count'])} "
            f"| {_value(r['unknowns_count'])} | {r['seconds']} |"
        )
    limitations = report["limitations"]
    assert isinstance(limitations, list)
    lines += ["", "## Limitations", "", *(f"- {text}" for text in limitations)]
    return "\n".join(lines) + "\n"


def write(report: dict[str, object], directory: Path) -> tuple[Path, Path]:
    json_path, md_path = directory / "report.json", directory / "report.md"
    if json_path.exists() or md_path.exists():
        raise FileExistsError("refusing to overwrite an existing report")
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    written = json.loads(json_path.read_text(encoding="utf-8"))
    md_path.write_text(render(written), encoding="utf-8")
    return json_path, md_path
