"""Model-comparison reports: per-model (R3 blocks + timing), smoke, comparison.

Per-model reports reuse the R3 report builder unchanged, so gates, decision and
every descriptive block are the frozen R3/1Q functions. A smoke report is never
quality evidence. The comparison reads only verified reports and applies the
predeclared rule (planning/FORGEAI-ANALYST-MODEL-COMPARISON.md, section 9).
"""

import json
import statistics
from collections.abc import Iterable
from pathlib import Path
from typing import cast

from analyst_quality1q import report as qr
from analyst_quality1q_r3 import report as r3

CONDITION_SCHEMA = "forgeai-analyst-model-compare-condition/1"
REPORT_SCHEMA = "forgeai-analyst-model-compare-report/1"
SMOKE_SCHEMA = "forgeai-analyst-model-compare-smoke/1"
COMPARISON_SCHEMA = "forgeai-analyst-model-compare-comparison/1"
TIMEOUT_SECONDS = 600.0
OUTCOMES = {
    "A": "STRONGER MODEL CONDITION JUSTIFIED",
    "B": "MODEL CHANGE DOES NOT RESOLVE ANALYST QUALITY",
    "C": "CURRENT HARDWARE CANNOT TEST A CREDIBLE STRONGER MODEL",
    "D": "EVIDENCE INSUFFICIENT",
}
SMOKE_LABEL = "SMOKE - compatibility and latency only; not quality evidence"
HEADLINE = (
    "validity",
    "precision",
    "required_recall",
    "acceptable_set_success",
    "insufficient_correct",
)


def timing(records: Iterable[dict[str, object]]) -> dict[str, object]:
    seconds = sorted(float(cast(float, r["seconds"])) for r in records)
    if not seconds:
        return {"calls": 0}
    return {
        "calls": len(seconds),
        "mean": round(statistics.mean(seconds), 3),
        "median": round(statistics.median(seconds), 3),
        "p90": seconds[max(0, int(0.9 * len(seconds)) - 1)],
        "max": seconds[-1],
        "total_hours": round(sum(seconds) / 3600, 3),
    }


def build(
    condition: dict[str, object],
    records: list[dict[str, object]],
    limits: dict[str, object],
    historical: dict[str, object],
) -> dict[str, object]:
    """One model condition: the unchanged R3 report plus timing."""
    base = r3.build(condition, records, limits, historical)
    return {**base, "schema": REPORT_SCHEMA, "timing": timing(records)}


def smoke(
    condition: dict[str, object], records: list[dict[str, object]]
) -> dict[str, object]:
    """Compatibility and latency only: no gates, no decision, no quality claim."""
    stages: dict[str, int] = {}
    for r in records:
        stages[str(r["stage"])] = stages.get(str(r["stage"]), 0) + 1
    clock = timing(records)
    failures = stages.get("model_failure", 0)
    longest = float(cast(float, clock.get("max", 0.0)))
    return {
        "schema": SMOKE_SCHEMA,
        "quality_evidence": False,
        "label": SMOKE_LABEL,
        "condition": condition,
        "condition_digest": qr.condition_digest(condition),
        "calls": len(records),
        "stages": dict(sorted(stages.items())),
        "model_failures": failures,
        "timing": clock,
        "projected_full_hours": round(
            float(cast(float, clock.get("mean", 0.0))) * 91 / 3600, 2
        ),
        "fits_host": bool(records) and failures == 0 and longest < TIMEOUT_SECONDS,
    }


def _value(rate: object) -> float | None:
    if isinstance(rate, dict):
        value = rate.get("value")
        return float(value) if isinstance(value, int | float) else None
    return None


def summary(report: dict[str, object]) -> dict[str, object]:
    """Comparable view of one full model report (R3 or comparison schema)."""
    aggregate = cast(dict[str, object], report["aggregate"])
    held = cast(
        dict[str, object], cast(dict[str, object], aggregate["partitions"])["heldout"]
    )
    by_class = cast(dict[str, dict[str, object]], aggregate["heldout_by_class"])
    condition = cast(dict[str, object], report["condition"])
    model = cast(dict[str, object], condition["model"])
    watch = cast(dict[str, object], report["over_correction"])
    records = cast(list[dict[str, object]], report["records"])
    return {
        "model": model["name"],
        "digest": model.get("digest"),
        "decision": cast(dict[str, object], report["decision"])["code"],
        "gates": report["gates"],
        **{k: held[k] for k in HEADLINE},
        "false_sufficient": held["false_sufficient"],
        "catastrophic": held["catastrophic"],
        "model_failures": held["model_failures"],
        "classifier_disagreements": held["classifier_disagreements"],
        "over_selection": held["over_selection"],
        "under_selection": held["under_selection"],
        "safety": aggregate["safety_all_calls"],
        "answerable": report["answerable"],
        "expected_insufficient_to_succeeded": cast(
            dict[str, object], watch["expected_insufficient_to_succeeded"]
        )["heldout"],
        "structural_stages": cast(
            dict[str, object], cast(dict[str, object], report["structural"])["heldout"]
        )["stages"],
        "per_class": {
            name: {
                "required_recall": row["required_recall"],
                "acceptable_set_success": row["acceptable_set_success"],
            }
            for name, row in sorted(by_class.items())
        },
        "timing": timing(records),
    }


def material(
    candidate: dict[str, object],
    control: dict[str, object],
    margins: dict[str, float],
) -> dict[str, object]:
    """The predeclared material-improvement test of one candidate."""

    def at_least(key: str, margin: float) -> bool:
        ours, theirs = _value(candidate[key]), _value(control[key])
        return (
            ours is not None and theirs is not None and ours >= theirs + margin - 1e-9
        )

    ours = cast(dict[str, dict[str, object]], candidate["per_class"])
    theirs = cast(dict[str, dict[str, object]], control["per_class"])
    shared = [
        name
        for name in ours
        if name in theirs
        and _value(ours[name]["required_recall"]) is not None
        and _value(theirs[name]["required_recall"]) is not None
    ]
    improved = sum(
        1
        for name in shared
        if cast(float, _value(ours[name]["required_recall"]))
        > cast(float, _value(theirs[name]["required_recall"]))
    )
    gates = cast(dict[str, bool], candidate["gates"])
    checks = {
        "frozen_decision_a": candidate["decision"] == "A",
        "safety_zero": all(
            v == 0 for v in cast(dict[str, int], candidate["safety"]).values()
        ),
        "validity_gate": bool(gates["validity"]),
        "required_recall": at_least("required_recall", margins["required_recall"]),
        "acceptable_set_success": at_least(
            "acceptable_set_success", margins["acceptable_set_success"]
        ),
        "insufficient_correct": at_least(
            "insufficient_correct", margins["insufficient_correct"]
        ),
        "false_sufficient": int(cast(int, candidate["false_sufficient"]))
        <= int(
            int(cast(int, control["false_sufficient"]))
            * margins["false_sufficient_ratio"]
        ),
        "class_majority": bool(shared) and improved * 2 > len(shared),
    }
    relative = (
        "validity_gate",
        "required_recall",
        "acceptable_set_success",
        "insufficient_correct",
        "false_sufficient",
        "class_majority",
    )
    return {
        "checks": checks,
        "classes_improved": {"improved": improved, "shared": len(shared)},
        "material": checks["safety_zero"]
        and (checks["frozen_decision_a"] or all(checks[k] for k in relative)),
    }


def compare(
    control: dict[str, object],
    candidates: list[dict[str, object]],
    smokes: list[dict[str, object]],
    identity_failures: list[str],
    margins: dict[str, float],
) -> dict[str, object]:
    """Exactly one predeclared outcome."""
    tests = {str(c["model"]): material(c, control, margins) for c in candidates}
    if identity_failures or any(
        c["decision"] == "D" or c["classifier_disagreements"] for c in candidates
    ):
        code = "D"
    elif any(t["material"] for t in tests.values()):
        code = "A"
    elif candidates:
        code = "B"
    elif smokes and not any(s["fits_host"] for s in smokes):
        code = "C"
    else:
        raise ValueError("a comparison needs a full candidate report or failed smokes")
    return {
        "code": code,
        "label": OUTCOMES[code],
        "material": tests,
        "identity_failures": identity_failures,
    }


def render_model(report: dict[str, object]) -> str:
    text = r3.render(report)
    title, _, rest = text.partition("\n")
    clock = cast(dict[str, object], report["timing"])
    lines = ["## Timing (seconds per call)", "", "| Metric | Value |", "| --- | --- |"]
    lines += [f"| {k} | {v} |" for k, v in clock.items()]
    model = cast(
        dict[str, object], cast(dict[str, object], report["condition"])["model"]
    )
    return (
        f"# ANALYST-MODEL-COMPARE-1 model report: {model['name']}\n"
        + rest
        + "\n"
        + "\n".join(lines)
        + "\n"
    )


def render_smoke(report: dict[str, object]) -> str:
    model = cast(
        dict[str, object], cast(dict[str, object], report["condition"])["model"]
    )
    lines = [
        f"# ANALYST-MODEL-COMPARE-1 smoke: {model['name']}",
        "",
        f"**{report['label']}**",
        "",
        "| Metric | Value |",
        "| --- | --- |",
    ]
    for key in (
        "calls",
        "stages",
        "model_failures",
        "timing",
        "projected_full_hours",
        "fits_host",
    ):
        lines.append(f"| {key} | {json.dumps(report[key], sort_keys=True)} |")
    return "\n".join(lines) + "\n"


def render_comparison(report: dict[str, object]) -> str:
    outcome = cast(dict[str, object], report["outcome"])
    rows = cast(list[dict[str, object]], report["models"])
    lines = [
        "# ANALYST-MODEL-COMPARE-1 comparison",
        "",
        f"**Outcome:** {outcome['code']} - {outcome['label']}",
        "",
        "| Model | Decision | Validity | Precision | Required recall | Acceptable set "
        "| Insufficient correct | False sufficient | Answerable success | Mean s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        answerable = cast(dict[str, object], row["answerable"])
        clock = cast(dict[str, object], row["timing"])
        lines.append(
            f"| {row['model']} | {row['decision']} | "
            + " | ".join(qr._rate(row[k]) for k in HEADLINE)
            + f" | {row['false_sufficient']} | "
            f"{qr._rate(answerable['answerable_success_rate'])} | {clock.get('mean')} |"
        )
    lines += ["", "## Material-improvement tests", "", "```json"]
    lines += [json.dumps(outcome["material"], indent=2, sort_keys=True), "```"]
    lines += ["", "## Inputs (SHA-256)", "", "```json"]
    lines += [json.dumps(report["inputs"], indent=2, sort_keys=True), "```"]
    lines += [
        "",
        "## Limitations",
        "",
        *(f"- {t}" for t in cast(list[str], report["limitations"])),
    ]
    return "\n".join(lines) + "\n"


def write(
    directory: Path,
    name: str,
    report: dict[str, object],
    render: object,
) -> tuple[Path, Path]:
    """Write <name>.json, then <name>.md rendered from the written JSON."""
    json_path, md_path = directory / f"{name}.json", directory / f"{name}.md"
    if json_path.exists() or md_path.exists():
        raise FileExistsError("refusing to overwrite an existing report")
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    written = json.loads(json_path.read_text(encoding="utf-8"))
    assert callable(render)
    md_path.write_text(render(written), encoding="utf-8")
    return json_path, md_path
