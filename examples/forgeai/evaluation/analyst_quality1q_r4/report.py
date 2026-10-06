"""CONTENT-DISCOVERY-1Q-R4 report: JSON is the evidence; Markdown renders it.

Quality aggregates, gates and the decision are the frozen 1Q functions; the
structural block is DIAG-1's; the clause and confusion block is
ANALYST-INSUFFICIENT-DIAG-1's; the answerable and over-correction blocks are
R3's; timing is the model comparison's. All fold from the content-free records.
The per-case, c15, comparison and stop-rule blocks are descriptive and never
change the decision. Historical facts are preregistered references only.
"""

import json
from pathlib import Path

from analyst_contract_diag1 import report as diag
from analyst_insufficient_diag1 import report as aid
from analyst_insufficient_diag1.clauses import Refined
from analyst_model_compare1.report import timing
from analyst_quality1q import report as q
from analyst_quality1q.metrics import decide, fold, gates
from analyst_quality1q_r3.report import answerable, watch

SCHEMA = "forgeai-analyst-quality-report/4"
CONDITION_SCHEMA = "forgeai-analyst-quality-condition/4"
OUTCOMES = ("succeeded", "insufficient_evidence", "invalid")
STOP_RULE = {
    "A": "CONTINUE_TO_CONTENT_DISCOVERY_2_DECISION",
    "B": "STOP_PROMPT_MODIFICATION_REASSESS_ANALYST_DESIGN",
    "C": "STOP_PROMPT_MODIFICATION_REASSESS_ANALYST_DESIGN",
    "D": "DIAGNOSE_MEASUREMENT_CONDITION",
}
REASSESS = [
    "task design",
    "Analyst contract",
    "evidence-acquisition UX",
    "a separate operator-visible sufficiency/evidence step",
]
COMPARED = (
    "validity",
    "precision",
    "required_recall",
    "acceptable_set_success",
    "insufficient_correct",
    "false_sufficient",
    "catastrophic",
)
DEFINITIONS = {
    **q.DEFINITIONS,
    "answerable_success_rate": "held-out calls expected succeeded, structurally "
    "valid and answered succeeded / all held-out calls expected succeeded "
    "(descriptive; not a gate)",
    "closed_outcome": "per call: succeeded or insufficient_evidence when "
    "structurally valid, otherwise invalid (descriptive)",
    "known_non_gating_label_conflicts": "probes whose recorded label conflicts "
    "with the approved semantics; outside the gating partition, never gated",
    "stop_rule": "disposition derived from the decision code only; not a gate",
    "quality_is_decision_evidence": "true only for a live run with decision A or C",
}
LIMITATIONS = [
    *q.LIMITATIONS,
    "One condition at N=3: changes against the recorded 14b/1.0.2 condition are "
    "consistent with, not proof of, the 1.0.3 semantics causing them.",
    "Historical facts are recorded references; earlier replies were never retained.",
    "Structural and clause diagnostics record the first failure only.",
]


def outcome(record: dict[str, object]) -> str:
    """The closed per-call outcome."""
    if not record["valid"]:
        return "invalid"
    return str(record["runtime_status"])


def per_case(
    records: list[dict[str, object]], cases: list[str]
) -> dict[str, dict[str, int]]:
    """Closed outcome counts for each listed case (descriptive)."""
    result = {}
    for case in cases:
        rows = [r for r in records if r["case"] == case]
        counts = {o: sum(1 for r in rows if outcome(r) == o) for o in OUTCOMES}
        result[case] = {"calls": len(rows), **counts}
    return result


def conflicts(
    records: list[dict[str, object]], known: list[dict[str, object]]
) -> list[dict[str, object]]:
    """Identity and observed closed outcome of each known label conflict."""
    observed = per_case(records, [str(row["case"]) for row in known])
    return [
        {
            "case": row["case"],
            "partition": row["partition"],
            "recorded_expected": row["recorded_expected"],
            "approved_semantics": row["approved_semantics"],
            "statement": row["statement"],
            "gating": False,
            "observed": observed[str(row["case"])],
        }
        for row in known
    ]


def non_regression(
    aggregate: dict[str, object], ans: dict[str, object]
) -> dict[str, object]:
    partitions = aggregate["partitions"]
    by_class = aggregate["heldout_by_class"]
    assert isinstance(partitions, dict) and isinstance(by_class, dict)
    held = partitions["heldout"]
    assert isinstance(held, dict)
    return {
        "answerable_success": ans["answerable_success_rate"],
        "valid_abstention": ans["valid_abstention"],
        "invalid_abstention": ans["invalid_abstention"],
        "required_recall": held["required_recall"],
        "acceptable_set_success": held["acceptable_set_success"],
        "per_class": {
            name: {
                "required_recall": row["required_recall"],
                "acceptable_set_success": row["acceptable_set_success"],
            }
            for name, row in sorted(by_class.items())
        },
    }


def insufficiency_clauses(clauses: dict[str, object]) -> dict[str, dict[str, int]]:
    """Refined insufficient-inconsistent counts, per partition and overall."""
    partitions = clauses["partitions"]
    assert isinstance(partitions, dict)
    result = {}
    for name, summary in [("all", clauses["all"]), *partitions.items()]:
        assert isinstance(summary, dict)
        refined = summary["refined"]
        assert isinstance(refined, dict)
        result[name] = {r.value: int(refined.get(r.value, 0)) for r in Refined}
    return result


def status_confusion(clauses: dict[str, object]) -> dict[str, object]:
    partitions = clauses["partitions"]
    every = clauses["all"]
    assert isinstance(partitions, dict) and isinstance(every, dict)
    return {
        **{name: summary["confusion"] for name, summary in partitions.items()},
        "aggregate": every["confusion"],
    }


def comparison(
    aggregate: dict[str, object], ans: dict[str, object], historical: dict[str, object]
) -> dict[str, object]:
    partitions = aggregate["partitions"]
    assert isinstance(partitions, dict)
    held = partitions["heldout"]
    assert isinstance(held, dict)
    current = {k: held[k] for k in COMPARED}
    current["answerable_success"] = ans["answerable_success_rate"]
    return {
        "reference": historical["analyst_1_0_2_14b"],
        "analyst_1_0_3_14b": current,
        "causal_claim": False,
    }


def stop_rule(mode: object, code: str) -> dict[str, object]:
    disposition = STOP_RULE[code] if mode == "live" else "NOT_APPLICABLE_REPLAY"
    stop = disposition == STOP_RULE["B"]
    return {
        "disposition": disposition,
        "derived_from_decision": code,
        "is_gate": False,
        "prompt_modification_stops": stop,
        "recommend_analyst_1_0_4": False,
        "reassess": REASSESS if stop else [],
    }


def build(
    condition: dict[str, object],
    records: list[dict[str, object]],
    limits: dict[str, object],
    preregistration: dict[str, object],
) -> dict[str, object]:
    aggregate = fold(records)
    passed = gates(aggregate, limits)
    decision = decide(passed)
    code = str(decision["code"])
    if condition["mode"] != "live":
        decision = {**decision, "label": "REPLAY ONLY - not quality evidence"}
    clauses = aid.fold(records)
    ans = answerable(records)
    historical = preregistration["historical"]
    insufficient = preregistration["expected_insufficient_cases"]
    controls = preregistration["future_behavior_controls"]
    known = preregistration["known_non_gating_label_conflicts"]
    assert isinstance(historical, dict) and isinstance(known, list)
    assert isinstance(insufficient, list) and isinstance(controls, list)
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
        "quality_is_decision_evidence": condition["mode"] == "live"
        and code in {"A", "C"},
        "stop_rule": stop_rule(condition["mode"], code),
        "answerable": ans,
        "answerable_non_regression": non_regression(aggregate, ans),
        "expected_insufficient_cases": per_case(records, insufficient),
        "future_behavior_controls": per_case(records, controls),
        "over_correction": watch(aggregate, clauses),
        "structural": {
            "all": diag.summarize(records),
            "heldout": diag.summarize(
                [r for r in records if r["partition"] == "heldout"]
            ),
            "pattern": diag.pattern(records),
        },
        "clauses": clauses,
        "insufficiency_clauses": insufficiency_clauses(clauses),
        "status_confusion": status_confusion(clauses),
        "known_non_gating_label_conflicts": conflicts(records, known),
        "timing": timing(records),
        "primary_comparison": comparison(aggregate, ans, historical),
        "historical_references": historical,
        "definitions": DEFINITIONS,
        "limitations": LIMITATIONS,
    }


def _value(value: object) -> str:
    if isinstance(value, dict) and "numerator" in value:
        if "value" not in value:  # a recorded reference count, not a folded rate
            return f"{value['numerator']}/{value['denominator']}"
        return q._rate(value)
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def _table(summary: object) -> list[str]:
    assert isinstance(summary, dict)
    return ["| Metric | Value |", "| --- | --- |"] + [
        f"| {k} | {_value(v)} |" for k, v in summary.items()
    ]


def _cases(block: object) -> list[str]:
    assert isinstance(block, dict)
    lines = [
        "| Case | Calls | succeeded | insufficient_evidence | invalid |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case, row in block.items():
        assert isinstance(row, dict)
        lines.append(
            f"| {case} | {row['calls']} | {row['succeeded']} | "
            f"{row['insufficient_evidence']} | {row['invalid']} |"
        )
    return lines


def render(report: dict[str, object]) -> str:
    """Markdown from the JSON report only; no metric is computed here."""
    decision, aggregate = report["decision"], report["aggregate"]
    structural, stop = report["structural"], report["stop_rule"]
    compared = report["primary_comparison"]
    known = report["known_non_gating_label_conflicts"]
    assert isinstance(decision, dict) and isinstance(aggregate, dict)
    assert isinstance(structural, dict) and isinstance(stop, dict)
    assert isinstance(compared, dict) and isinstance(known, list)
    pattern = structural["pattern"]
    assert isinstance(pattern, dict)
    lines = [
        "# CONTENT-DISCOVERY-1Q-R4 RepositoryAnalyst 1.0.3 report",
        "",
        f"**Mode:** {report['mode']}. **Decision:** {decision['code']} - "
        f"{decision['label']}",
        "",
        f"**Stop rule (not a gate):** {stop['disposition']}. Analyst 1.0.4 "
        f"recommended: {stop['recommend_analyst_1_0_4']}.",
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
    reference, current = compared["reference"], compared["analyst_1_0_3_14b"]
    assert isinstance(reference, dict) and isinstance(current, dict)
    lines += [
        "",
        "## Primary comparison (recorded 14b/1.0.2 reference; no causal claim)",
        "",
        "| Metric | 14b / 1.0.2 (recorded) | 14b / 1.0.3 (this condition) |",
        "| --- | --- | --- |",
    ]
    for key, value in current.items():
        lines.append(f"| {key} | {_value(reference.get(key, '-'))} | {_value(value)} |")
    lines += [
        "",
        "## Expected-insufficient held-out cases (descriptive)",
        "",
        *_cases(report["expected_insufficient_cases"]),
        "",
        "## Future-behavior controls (descriptive)",
        "",
        *_cases(report["future_behavior_controls"]),
        "",
        "## Known non-gating label conflicts",
        "",
    ]
    for row in known:
        assert isinstance(row, dict)
        lines += [f"- **{row['case']}** ({row['partition']}): {row['statement']}"]
    lines += [
        "",
        *_cases({row["case"]: row["observed"] for row in known}),
        "",
        "## Answerable non-regression (descriptive)",
        "",
    ]
    regression = report["answerable_non_regression"]
    assert isinstance(regression, dict)
    lines += _table({k: v for k, v in regression.items() if k != "per_class"})
    lines += [
        "",
        "| Class | Required recall | Acceptable set |",
        "| --- | --- | --- |",
    ]
    per_class = regression["per_class"]
    assert isinstance(per_class, dict)
    for klass, row in per_class.items():
        lines.append(
            f"| {klass} | {q._rate(row['required_recall'])} | "
            f"{q._rate(row['acceptable_set_success'])} |"
        )
    lines += [
        "",
        "## Answerable held-out calls",
        "",
        *_table(report["answerable"]),
        "",
        "## Over-correction watch",
        "",
        *_table(report["over_correction"]),
        "",
        "## Insufficiency clauses",
        "",
        *_table(report["insufficiency_clauses"]),
        "",
        "## Status confusion (expected -> actual)",
        "",
        *_table(report["status_confusion"]),
        "",
        "## Timing",
        "",
        *_table(report["timing"]),
        "",
        f"## Structural pattern: {pattern['code']} - {pattern['label']} "
        f"({pattern['invalid_calls']} invalid calls)",
    ]
    for name in ("all", "heldout"):
        lines += [
            "",
            f"## Structural diagnostics: {name}",
            "",
            *_table(structural[name]),
        ]
    partitions = aggregate["partitions"]
    assert isinstance(partitions, dict)
    for name, summary in partitions.items():
        lines += ["", f"## Partition: {name}", "", *_table(summary)]
    lines += [
        "",
        "## Historical references (recorded, never recomputed)",
        "",
        "```json",
        json.dumps(report["historical_references"], indent=2, sort_keys=True),
        "```",
        "",
        "## Calls",
        "",
        "| Case | Partition | Rep | Expected | Actual | Category | Stage "
        "| Abstention | Refined | Predicted | s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    records = report["records"]
    assert isinstance(records, list)
    for r in records:
        predicted = ", ".join(r["predicted"]) if r["predicted"] is not None else "-"
        lines.append(
            f"| {r['case']} | {r['partition']} | {r['repetition']} | {r['expected']} "
            f"| {r['actual_status'] or 'unparsed'} | {r['category']} | {r['stage']} "
            f"| {r['abstention']} | {r['refined'] or '-'} | {predicted} "
            f"| {r['seconds']} |"
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
