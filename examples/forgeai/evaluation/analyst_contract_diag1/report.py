"""ANALYST-CONTRACT-DIAG-1 report: aggregates folded from records, pattern rule.

No composite score and no reasoning-quality metric: rejected replies carry no
admissible relevance claims. The pattern rule below was declared before any
diagnostic live run (see planning/FORGEAI-ANALYST-CONTRACT-DIAGNOSTIC.md).
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from analyst_contract_diag1.diagnose import CONTRACT, Stage

SCHEMA = "forgeai-analyst-contract-diagnostic-report/1"
CONDITION_SCHEMA = "forgeai-analyst-contract-diagnostic-condition/1"
# Frozen CONTENT-DISCOVERY-1Q identity this diagnostic re-measures.
LINKAGE = {
    "cq_commit": "2edc3f7e5911b60cd6a40108446eae5aeb01ecaf",
    "cq_condition_digest": "2cdb97109fee018ff9a1f36e47a7663202a36ec2e8de80f68ec940f8b5f5afbf",
    "cq_report_sha256": "f03d213f367e4fcbfbb445a3f67e12db7b5ea7d0ce15933d1fafa6725bbcb93d",
    "cq_decision": "B",
}
PARSE_STAGES = {
    Stage.RESPONSE_NOT_JSON,
    Stage.TOP_LEVEL_NOT_OBJECT,
    Stage.OUTPUT_CONTRACT_INVALID,
}
SHAPE_STAGES = {
    Stage.STATUS_INVALID,
    Stage.FINDINGS_SHAPE_INVALID,
    Stage.FINDING_ENTRY_INVALID,
    Stage.SUMMARY_TYPE_INVALID,
    Stage.RELEVANT_FILES_SHAPE_INVALID,
    Stage.RISKS_SHAPE_INVALID,
    Stage.UNKNOWNS_SHAPE_INVALID,
    Stage.SUMMARY_BOUNDS_INVALID,
    Stage.RELEVANT_FILES_DUPLICATE,
    Stage.NARRATIVE_BOUNDS_INVALID,
}
PATTERNS = {
    "A": "SINGLE-FIELD OMISSION PATTERN",
    "B": "MIXED REQUIRED-FIELD OMISSION PATTERN",
    "C": "UNEXPECTED-FIELD PATTERN",
    "D": "TYPE/SHAPE PATTERN",
    "E": "NON-JSON / REPRESENTATION PATTERN",
    "F": "MIXED STRUCTURAL PATTERN",
}
LIMITATIONS = [
    "Diagnoses the first structural failure only; later fields are not validated.",
    "A fresh live run of the frozen 1Q condition: the replies are new samples, "
    "not the 1Q replies, which were never retained.",
    "No reasoning quality is computed from rejected replies.",
    "Unexpected field names are never recorded, only their count.",
]


def _missing(record: dict[str, object]) -> list[str]:
    names = record["missing_required_fields"]
    return [str(n) for n in names] if isinstance(names, list) else []


def _type(record: dict[str, object], name: str) -> str:
    types = record["field_types"]
    return str(types[name]) if isinstance(types, dict) else "missing"


def _counts(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def summarize(records: list[dict[str, object]]) -> dict[str, object]:
    objects = [r for r in records if r["field_types"] is not None]
    field_set = [r for r in records if r["stage"] == Stage.FIELD_SET_INVALID]
    missing: list[str] = []
    for r in field_set:
        missing.extend(_missing(r))
    return {
        "calls": len(records),
        "valid": sum(1 for r in records if r["stage"] == Stage.VALID),
        "stages": _counts([str(r["stage"]) for r in records]),
        "representations": _counts([str(r["representation"]) for r in records]),
        "field_set_invalid": len(field_set),
        "missing_required_fields": {
            name: missing.count(name) for name in CONTRACT if name in missing
        },
        "missing_field_combinations": _counts(
            ["+".join(_missing(r)) or "none" for r in field_set]
        ),
        "unexpected_field_count": _counts(
            [str(r["unexpected_field_count"]) for r in field_set]
        ),
        "field_types": {
            name: _counts([_type(r, name) for r in objects]) for name in CONTRACT
        },
        "status_values": _counts(
            [str(r["status_value"]) for r in objects if r["status_value"] is not None]
        ),
        "model_failures": sum(1 for r in records if r["stage"] == Stage.MODEL_FAILURE),
        "classifier_disagreements": sum(
            1 for r in records if r["stage"] == Stage.CLASSIFIER_DISAGREEMENT
        ),
        "coarse_inconsistencies": sum(1 for r in records if not r["coarse_consistent"]),
    }


def pattern(records: list[dict[str, object]]) -> dict[str, object]:
    """The predeclared structural-pattern rule over all invalid calls."""
    invalid = [
        r for r in records if r["stage"] not in {Stage.VALID, Stage.MODEL_FAILURE}
    ]
    if not invalid:
        return {"code": None, "label": "NO STRUCTURAL FAILURE", "invalid_calls": 0}
    n = len(invalid)
    stages = Counter(Stage(str(r["stage"])) for r in invalid)
    field_set = [r for r in invalid if r["stage"] == Stage.FIELD_SET_INVALID]
    if sum(stages[s] for s in PARSE_STAGES) / n >= 0.5:
        code = "E"
    elif len(field_set) / n >= 0.5:
        extra_only = [
            r
            for r in field_set
            if not r["missing_required_fields"] and r["unexpected_field_count"]
        ]
        names: Counter[str] = Counter()
        for r in field_set:
            names.update(_missing(r))
        if len(extra_only) / len(field_set) >= 0.5:
            code = "C"
        elif names and (
            names.most_common(1)[0][1] / len(field_set) >= 0.8
            and names.most_common(1)[0][1] / sum(names.values()) >= 0.8
        ):
            code = "A"
        else:
            code = "B"
    elif sum(stages[s] for s in SHAPE_STAGES) / n >= 0.5:
        code = "D"
    else:
        code = "F"
    return {"code": code, "label": PATTERNS[code], "invalid_calls": n}


def fold(records: list[dict[str, object]]) -> dict[str, object]:
    partitions = sorted({str(r["partition"]) for r in records})
    by_case: dict[str, dict[str, int]] = {}
    for r in records:
        by_case.setdefault(str(r["case"]), {})
        stage = str(r["stage"])
        by_case[str(r["case"])][stage] = by_case[str(r["case"])].get(stage, 0) + 1
    return {
        "all": summarize(records),
        "partitions": {
            p: summarize([r for r in records if r["partition"] == p])
            for p in partitions
        },
        "by_case": by_case,
        "pattern": pattern(records),
    }


def condition_digest(condition: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(condition, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build(
    condition: dict[str, object], records: list[dict[str, object]]
) -> dict[str, object]:
    aggregate = fold(records)
    label = aggregate["pattern"]
    if condition["mode"] != "live":
        assert isinstance(label, dict)
        aggregate["pattern"] = {**label, "label": "REPLAY ONLY - not live evidence"}
    return {
        "schema": SCHEMA,
        "mode": condition["mode"],
        "condition": condition,
        "condition_digest": condition_digest(condition),
        "records": records,
        "aggregate": aggregate,
        "limitations": LIMITATIONS,
    }


def _value(value: object) -> str:
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def render(report: dict[str, object]) -> str:
    """Markdown from the JSON report only."""
    aggregate = report["aggregate"]
    assert isinstance(aggregate, dict)
    pat = aggregate["pattern"]
    assert isinstance(pat, dict)
    lines = [
        "# ANALYST-CONTRACT-DIAG-1 report",
        "",
        f"**Mode:** {report['mode']}. **Pattern:** {pat['code']} - {pat['label']} "
        f"({pat['invalid_calls']} invalid calls)",
        "",
        f"Condition digest `{report['condition_digest']}`.",
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
    sections += [(f"Partition: {name}", value) for name, value in partitions.items()]
    for title, summary in sections:
        assert isinstance(summary, dict)
        lines += ["", f"## {title}", "", "| Metric | Value |", "| --- | --- |"]
        lines += [f"| {k} | {_value(v)} |" for k, v in summary.items()]
    lines += [
        "",
        "## Calls",
        "",
        "| Case | Partition | Rep | Stage | Representation | Fields (actual/expected) "
        "| Missing | Unexpected | s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    records = report["records"]
    assert isinstance(records, list)
    for r in records:
        missing = ", ".join(r["missing_required_fields"] or []) or "-"
        lines.append(
            f"| {r['case']} | {r['partition']} | {r['repetition']} | {r['stage']} | "
            f"{r['representation']} | {r['actual_field_count']}/"
            f"{r['expected_field_count']} | {missing} | "
            f"{r['unexpected_field_count']} | {r['seconds']} |"
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
