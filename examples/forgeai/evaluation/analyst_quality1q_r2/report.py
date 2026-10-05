"""CONTENT-DISCOVERY-1Q-R2 report: JSON is the evidence; Markdown renders it.

Quality aggregates, gates and the decision are the frozen 1Q functions; the
structural aggregates and pattern are the DIAG-1 functions. All of them fold
from the content-free per-call records. Historical 1Q/DIAG-1 facts are carried
as preregistered references only and are never recomputed.
"""

import json
from pathlib import Path

from analyst_contract_diag1 import report as diag
from analyst_quality1q import report as q
from analyst_quality1q.metrics import decide, fold, gates

SCHEMA = "forgeai-analyst-quality-report/2"
CONDITION_SCHEMA = "forgeai-analyst-quality-condition/2"
OBSERVATIONS = {
    "addressed": "CONSISTENT WITH THE PRIOR BLOCKER BEING ADDRESSED",
    "persists": "PRIOR BLOCKER PERSISTS",
    "reduced": "PRIOR BLOCKER REDUCED, NOT ELIMINATED",
}
DEFINITIONS = {
    **q.DEFINITIONS,
    "prior_blocker": "first failure field_set_invalid with both risks and unknowns "
    "missing (the ANALYST-CONTRACT-DIAG-1 finding for Analyst 1.0.0)",
    "quality_is_decision_evidence": "true only for decisions A or C; below the "
    "validity gate, relevance metrics are descriptive only",
}
LIMITATIONS = [
    *q.LIMITATIONS,
    "One condition: a structural change is consistent with, not proof of, the "
    "1.0.1 prompt clarification causing it.",
    "Historical 1.0.0 facts are recorded references; their rejected replies were "
    "never retained and are not compared.",
    "Structural diagnosis records the first failure only.",
]


def prior_blocker(record: dict[str, object]) -> bool:
    missing = record["missing_required_fields"]
    return (
        record["stage"] == "field_set_invalid"
        and isinstance(missing, list)
        and {"risks", "unknowns"} <= set(missing)
    )


def comparison(
    records: list[dict[str, object]], historical: dict[str, object]
) -> dict[str, object]:
    calls = len(records)
    valid = sum(1 for r in records if r["valid"])
    blocked = sum(1 for r in records if prior_blocker(r))
    if blocked == 0 and valid > 0:
        key = "addressed"
    elif calls and blocked / calls >= 0.5:
        key = "persists"
    else:
        key = "reduced"
    return {
        "historical": historical,
        "structural_validity": {
            "analyst_1_0_0": historical["1q_validity"],
            "analyst_1_0_1": {"numerator": valid, "denominator": calls},
        },
        "prior_blocker_calls": blocked,
        "observation": OBSERVATIONS[key],
        "causal_claim": False,
    }


def build(
    condition: dict[str, object],
    records: list[dict[str, object]],
    limits: dict[str, object],
    historical: dict[str, object],
) -> dict[str, object]:
    aggregate = fold(records)
    passed = gates(aggregate, limits)
    decision = decide(passed)
    compared = comparison(records, historical)
    if condition["mode"] != "live":
        decision = {**decision, "label": "REPLAY ONLY - not quality evidence"}
        compared = {**compared, "observation": "REPLAY ONLY - not live evidence"}
    held = [r for r in records if r["partition"] == "heldout"]
    return {
        "schema": SCHEMA,
        "mode": condition["mode"],
        "condition": condition,
        "condition_digest": q.condition_digest(condition),
        "records": records,
        "aggregate": aggregate,
        "structural": {
            "all": diag.summarize(records),
            "heldout": diag.summarize(held),
            "pattern": diag.pattern(records),
            "prior_blocker_calls": compared["prior_blocker_calls"],
        },
        "thresholds": limits,
        "gates": passed,
        "decision": decision,
        "quality_is_decision_evidence": decision["code"] in {"A", "C"},
        "historical_comparison": compared,
        "definitions": DEFINITIONS,
        "limitations": LIMITATIONS,
    }


def _table(summary: dict[str, object]) -> list[str]:
    lines = ["| Metric | Value |", "| --- | --- |"]
    return lines + [f"| {k} | {q._rate(v)} |" for k, v in summary.items()]


def render(report: dict[str, object]) -> str:
    """Markdown from the JSON report only; no metric is computed here."""
    condition, aggregate = report["condition"], report["aggregate"]
    decision, structural = report["decision"], report["structural"]
    compared = report["historical_comparison"]
    assert isinstance(condition, dict) and isinstance(aggregate, dict)
    assert isinstance(decision, dict) and isinstance(structural, dict)
    assert isinstance(compared, dict)
    validity = compared["structural_validity"]
    pattern = structural["pattern"]
    assert isinstance(validity, dict) and isinstance(pattern, dict)
    old, new = validity["analyst_1_0_0"], validity["analyst_1_0_1"]
    assert isinstance(old, dict) and isinstance(new, dict)
    lines = [
        "# CONTENT-DISCOVERY-1Q-R2 RepositoryAnalyst 1.0.1 report",
        "",
        f"**Mode:** {report['mode']}. **Decision:** {decision['code']} - "
        f"{decision['label']}",
        "",
        f"Relevance metrics are decision evidence: "
        f"{report['quality_is_decision_evidence']}.",
        "",
        f"Condition digest `{report['condition_digest']}`.",
        "",
        "## Historical comparison (reference only; no causal claim)",
        "",
        "| Analyst | Structurally valid |",
        "| --- | --- |",
        f"| 1.0.0 (1Q, recorded) | {old['numerator']}/{old['denominator']} |",
        f"| 1.0.1 (r2) | {new['numerator']}/{new['denominator']} |",
        "",
        f"Prior-blocker calls: {compared['prior_blocker_calls']}. "
        f"Observation: {compared['observation']}.",
        "",
        "## Condition",
        "",
        "```json",
        json.dumps(condition, indent=2, sort_keys=True),
        "```",
        "",
        "## Gates (held-out partition; safety over all calls)",
        "",
        "| Gate | Passed |",
        "| --- | --- |",
    ]
    gates_ = report["gates"]
    assert isinstance(gates_, dict)
    lines += [f"| {name} | {passed} |" for name, passed in gates_.items()]
    lines += [
        "",
        f"## Structural pattern: {pattern['code']} - {pattern['label']} "
        f"({pattern['invalid_calls']} invalid calls)",
    ]
    for name in ("all", "heldout"):
        summary = structural[name]
        assert isinstance(summary, dict)
        lines += ["", f"## Structural diagnostics: {name}", "", *_table(summary)]
    partitions = aggregate["partitions"]
    assert isinstance(partitions, dict)
    for name, summary in partitions.items():
        assert isinstance(summary, dict)
        lines += ["", f"## Partition: {name}", "", *_table(summary)]
    by_class = aggregate["heldout_by_class"]
    assert isinstance(by_class, dict)
    lines += [
        "",
        "## Held-out quality by class",
        "",
        "| Class | Calls | Valid | Required recall | Acceptable set | False sufficient |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for klass, s in by_class.items():
        assert isinstance(s, dict)
        lines.append(
            f"| {klass} | {s['calls']} | {q._rate(s['validity'])} | "
            f"{q._rate(s['required_recall'])} | "
            f"{q._rate(s['acceptable_set_success'])} | {s['false_sufficient']} |"
        )
    lines += [
        "",
        "## Calls",
        "",
        "| Case | Partition | Rep | Expected | Status | Category | Stage "
        "| Representation | Missing | Unexpected | Predicted | s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    records = report["records"]
    assert isinstance(records, list)
    for r in records:
        predicted = ", ".join(r["predicted"]) if r["predicted"] is not None else "-"
        missing = ", ".join(r["missing_required_fields"] or []) or "-"
        lines.append(
            f"| {r['case']} | {r['partition']} | {r['repetition']} | {r['expected']} "
            f"| {r['runtime_status']} | {r['category']} | {r['stage']} "
            f"| {r['representation']} | {missing} | {r['unexpected_field_count']} "
            f"| {predicted} | {r['seconds']} |"
        )
    definitions, limitations = report["definitions"], report["limitations"]
    assert isinstance(definitions, dict) and isinstance(limitations, list)
    lines += ["", "## Definitions", ""]
    lines += [f"- **{k}**: {v}" for k, v in definitions.items()]
    lines += ["", "## Limitations", "", *(f"- {text}" for text in limitations)]
    return "\n".join(lines) + "\n"


def write(report: dict[str, object], directory: Path) -> tuple[Path, Path]:
    """Write report.json, then report.md rendered from the written JSON."""
    json_path, md_path = directory / "report.json", directory / "report.md"
    if json_path.exists() or md_path.exists():
        raise FileExistsError("refusing to overwrite an existing report")
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    written = json.loads(json_path.read_text(encoding="utf-8"))
    md_path.write_text(render(written), encoding="utf-8")
    return json_path, md_path
