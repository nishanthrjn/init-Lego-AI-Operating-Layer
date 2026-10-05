"""CONTENT-DISCOVERY-1Q-R3 report: JSON is the evidence; Markdown renders it.

Quality aggregates, gates and the decision are the frozen 1Q functions; the
structural block is DIAG-1's; the clause, confusion and abstention block is
ANALYST-INSUFFICIENT-DIAG-1's. All fold from the content-free records. The
answerable-success, abstention and over-correction blocks are descriptive and
never change the decision. Historical facts are preregistered references only.
"""

import json
from pathlib import Path

from analyst_contract_diag1 import report as diag
from analyst_insufficient_diag1 import report as aid
from analyst_quality1q import report as q
from analyst_quality1q.metrics import decide, fold, gates

SCHEMA = "forgeai-analyst-quality-report/3"
CONDITION_SCHEMA = "forgeai-analyst-quality-condition/3"
OUTCOMES = ("valid_success", "valid_abstention", "invalid_abstention", "other_invalid")
DEFINITIONS = {
    **q.DEFINITIONS,
    "answerable_success_rate": "held-out calls expected succeeded, structurally "
    "valid and answered succeeded / all held-out calls expected succeeded "
    "(descriptive; not a gate)",
    "total_abstention": "valid_abstention + invalid_abstention over the same "
    "denominator (descriptive)",
    "quality_is_decision_evidence": "true only for decisions A or C",
}
LIMITATIONS = [
    *q.LIMITATIONS,
    "One condition: changes against 1.0.1 are consistent with, not proof of, the "
    "1.0.2 status policy causing them; at N=3 a few calls are within run-to-run "
    "variation (r2 and DIAG-1 differed by 4 answerable successes).",
    "Historical facts are recorded references; earlier replies were never retained.",
    "Structural and clause diagnostics record the first failure only.",
]


def _rate(numerator: int, denominator: int) -> dict[str, object]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": round(numerator / denominator, 4) if denominator else None,
    }


def answerable(records: list[dict[str, object]]) -> dict[str, object]:
    """Held-out calls whose expected outcome is succeeded (descriptive)."""
    rows = [
        r
        for r in records
        if r["partition"] == "heldout" and r["expected"] == "succeeded"
    ]
    n = len(rows)
    counts = {o: sum(1 for r in rows if r["abstention"] == o) for o in OUTCOMES}
    return {
        "calls": n,
        "answerable_success_rate": _rate(counts["valid_success"], n),
        **{o: _rate(c, n) for o, c in counts.items()},
        "total_abstention": _rate(
            counts["valid_abstention"] + counts["invalid_abstention"], n
        ),
    }


def watch(
    aggregate: dict[str, object], clauses: dict[str, object]
) -> dict[str, object]:
    """Over-correction indicators, read from the folded blocks only."""
    partitions = aggregate["partitions"]
    by_partition = clauses["partitions"]
    assert isinstance(partitions, dict) and isinstance(by_partition, dict)
    held = partitions["heldout"]
    assert isinstance(held, dict)
    to_succeeded = {}
    for name, summary in by_partition.items():
        assert isinstance(summary, dict)
        confusion = summary["confusion"]
        assert isinstance(confusion, dict)
        row = confusion["insufficient_evidence"]
        assert isinstance(row, dict)
        to_succeeded[name] = {
            "expected_insufficient": sum(int(v) for v in row.values()),
            "answered_succeeded": int(row["succeeded"]),
        }
    return {
        "expected_insufficient_to_succeeded": to_succeeded,
        "heldout_insufficient_correct": held["insufficient_correct"],
        "heldout_false_sufficient": held["false_sufficient"],
        "heldout_catastrophic": held["catastrophic"],
    }


def comparison(
    records: list[dict[str, object]], historical: dict[str, object]
) -> dict[str, object]:
    held = [r for r in records if r["partition"] == "heldout"]
    ans = answerable(records)
    current = {
        "heldout_validity": _rate(sum(1 for r in held if r["valid"]), len(held)),
        **{
            k: ans[k]
            for k in (
                "answerable_success_rate",
                "valid_abstention",
                "invalid_abstention",
                "other_invalid",
                "total_abstention",
            )
        },
    }
    return {"historical": historical, "analyst_1_0_2": current, "causal_claim": False}


def build(
    condition: dict[str, object],
    records: list[dict[str, object]],
    limits: dict[str, object],
    historical: dict[str, object],
) -> dict[str, object]:
    aggregate = fold(records)
    passed = gates(aggregate, limits)
    decision = decide(passed)
    if condition["mode"] != "live":
        decision = {**decision, "label": "REPLAY ONLY - not quality evidence"}
    clauses = aid.fold(records)
    return {
        "schema": SCHEMA,
        "mode": condition["mode"],
        "condition": condition,
        "condition_digest": q.condition_digest(condition),
        "records": records,
        "aggregate": aggregate,
        "thresholds": limits,
        "gates": passed,
        "decision": decision,
        "quality_is_decision_evidence": decision["code"] in {"A", "C"},
        "structural": {
            "all": diag.summarize(records),
            "heldout": diag.summarize(
                [r for r in records if r["partition"] == "heldout"]
            ),
            "pattern": diag.pattern(records),
        },
        "clauses": clauses,
        "answerable": answerable(records),
        "over_correction": watch(aggregate, clauses),
        "historical_comparison": comparison(records, historical),
        "definitions": DEFINITIONS,
        "limitations": LIMITATIONS,
    }


def _value(value: object) -> str:
    if isinstance(value, dict) and "numerator" in value:
        return q._rate(value)
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def _table(summary: dict[str, object]) -> list[str]:
    return ["| Metric | Value |", "| --- | --- |"] + [
        f"| {k} | {_value(v)} |" for k, v in summary.items()
    ]


def render(report: dict[str, object]) -> str:
    """Markdown from the JSON report only; no metric is computed here."""
    decision, aggregate = report["decision"], report["aggregate"]
    structural, clauses = report["structural"], report["clauses"]
    compared = report["historical_comparison"]
    assert isinstance(decision, dict) and isinstance(aggregate, dict)
    assert isinstance(structural, dict) and isinstance(clauses, dict)
    assert isinstance(compared, dict)
    pattern = structural["pattern"]
    current = compared["analyst_1_0_2"]
    historical = compared["historical"]
    assert isinstance(pattern, dict) and isinstance(current, dict)
    assert isinstance(historical, dict)
    lines = [
        "# CONTENT-DISCOVERY-1Q-R3 RepositoryAnalyst 1.0.2 report",
        "",
        f"**Mode:** {report['mode']}. **Decision:** {decision['code']} - "
        f"{decision['label']}",
        "",
        "Relevance metrics are decision evidence: "
        f"{report['quality_is_decision_evidence']}.",
        "",
        f"Condition digest `{report['condition_digest']}`.",
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
        "## Answerable held-out calls (descriptive)",
        "",
        *_table(report["answerable"]),  # type: ignore[arg-type]
        "",
        "## Over-correction watch",
        "",
        *_table(report["over_correction"]),  # type: ignore[arg-type]
        "",
        "## Historical comparison (recorded references; no causal claim)",
        "",
        "```json",
        json.dumps(historical, indent=2, sort_keys=True),
        "```",
        "",
        "Analyst 1.0.2 (this condition):",
        "",
        *_table(current),
        "",
        f"## Structural pattern: {pattern['code']} - {pattern['label']} "
        f"({pattern['invalid_calls']} invalid calls)",
    ]
    for name in ("all", "heldout"):
        summary = structural[name]
        assert isinstance(summary, dict)
        lines += ["", f"## Structural diagnostics: {name}", "", *_table(summary)]
    by_partition = clauses["partitions"]
    assert isinstance(by_partition, dict)
    for name, summary in [("all", clauses["all"]), *by_partition.items()]:
        assert isinstance(summary, dict)
        lines += [
            "",
            f"## Status, abstention and clauses: {name}",
            "",
            *_table(summary),
        ]
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
        "| Case | Partition | Rep | Expected | Actual | Category | Stage "
        "| Abstention | Refined | Findings | Unknowns | Predicted | s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    records = report["records"]
    assert isinstance(records, list)
    for r in records:
        predicted = ", ".join(r["predicted"]) if r["predicted"] is not None else "-"
        lines.append(
            f"| {r['case']} | {r['partition']} | {r['repetition']} | {r['expected']} "
            f"| {r['actual_status'] or 'unparsed'} | {r['category']} | {r['stage']} "
            f"| {r['abstention']} | {r['refined'] or '-'} "
            f"| {_value(r['findings_count'])} | {_value(r['unknowns_count'])} "
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
