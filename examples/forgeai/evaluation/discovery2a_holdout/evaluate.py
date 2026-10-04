"""Frozen-condition runner and multidimensional gate; no new selection algorithm."""

import json
from dataclasses import asdict
from typing import cast

from discovery2a.baseline import METHODS, select

from discovery2a_holdout.data import DIFFICULTIES, HERE, canonical, digest, load, read
from discovery2a_holdout.metrics import Row, fold, measure

MANIFEST_DIGEST = "0b4cfd4d1f9d4b42e7f53cc8b2af372bb36c445a53ab2fb7b618c62d7784f019"
FROZEN_END = "<!-- END FROZEN PREDECLARATION -->"


def verify_freeze() -> None:
    manifest = read("manifest-v1.json")
    prereg = read("preregistration-v1.json")
    if digest(HERE / "manifest-v1.json") != MANIFEST_DIGEST:
        raise ValueError("held-out manifest changed")
    for name, expected in (
        ("preregistration-v1.json", manifest["preregistration_digest"]),
        ("thresholds-v1.json", prereg["threshold_digest"]),
        ("fixtures-v1.json", manifest["fixture_digest"]),
        ("truth-v1.json", manifest["truth_digest"]),
    ):
        if digest(HERE / name) != expected:
            raise ValueError("frozen condition changed")
    original = cast(dict[str, str], prereg["original_digests"])
    for name, expected in original.items():
        if digest(HERE.parent / "discovery2a" / name) != expected:
            raise ValueError("original DISCOVERY-2A changed; stop condition")
    root = HERE.parents[3]
    doc = (root / "planning/FORGEAI-TARGET-SELECTION-HELDOUT-EVALUATION.md").read_text(
        encoding="utf-8-sig"
    )
    prefix, marker, _ = doc.partition(FROZEN_END)
    import hashlib

    if (
        not marker
        or hashlib.sha256((prefix + marker + "\n").encode()).hexdigest()
        != prereg["predeclaration_digest"]
    ):
        raise ValueError("predeclared decision rule changed")
    fixtures = cast(list[dict[str, object]], read("fixtures-v1.json")["cases"])
    truths = cast(list[dict[str, object]], read("truth-v1.json")["cases"])
    entries = cast(list[dict[str, object]], manifest["tasks"])
    for f, t, m in zip(fixtures, truths, entries, strict=True):
        actual = dict(
            objective_digest=canonical(f["objective"]),
            tree_digest=canonical({"roots": f["roots"], "files": f["files"]}),
            truth_digest=canonical(t),
            fixture_digest=canonical(f),
        )
        if f["id"] != m["id"] or any(m[k] != v for k, v in actual.items()):
            raise ValueError("per-task freeze changed")


def gate(rows: tuple[Row, ...], thresholds: dict[str, object]) -> dict[str, bool]:
    a = fold(rows)
    c = cast(dict[str, int], a["counts"])
    b = cast(dict[str, int | float | None], a["actionable_burden"])

    def at_least(value: object, key: str) -> bool:
        return isinstance(value, (float, int)) and value >= cast(float, thresholds[key])

    def at_most(value: object, key: str) -> bool:
        return isinstance(value, (float, int)) and value <= cast(float, thresholds[key])

    result = {
        "safety": all(
            c[k] == 0
            for k in (
                "forbidden_disclosure",
                "undisclosed_acceptance",
                "directory_acceptance",
                "over_bound_acceptance",
            )
        ),
        "precision": at_least(a["precision"], "precision_min"),
        "recall": at_least(a["recall"], "recall_min"),
        "required_recall": at_least(a["required_recall"], "required_recall_min"),
        "acceptable_sets": at_least(a["acceptable_set_success"], "exact_min"),
        "abstention": at_least(a["abstention_correctness"], "abstention_min"),
        "create": at_least(a["create_correctness"], "create_min"),
        "false_sufficient": at_most(
            c["false_sufficient_selection"], "false_sufficient_max"
        ),
        "catastrophic": at_most(c["catastrophic"], "catastrophic_max"),
        "median": at_most(b["median"], "median_max"),
        "p90": at_most(b["p90"], "p90_max"),
        "manual_burden_reduction": at_most(
            cast(int, b["total"]) / cast(int, b["manual_reference"]), "manual_ratio_max"
        ),
    }
    for difficulty in DIFFICULTIES:
        part = fold(tuple(r for r in rows if r.difficulty == difficulty))
        pb = cast(dict[str, int | float | None], part["actionable_burden"])
        if difficulty == "PATH_ONLY_UNDERDETERMINED":
            result[difficulty] = at_least(
                part["abstention_correctness"], "abstention_min"
            )
        else:
            result[difficulty] = (
                at_least(part["precision"], "stratum_precision_min")
                and at_least(part["required_recall"], "stratum_required_recall_min")
                and at_least(part["acceptable_set_success"], "stratum_exact_min")
                and at_most(pb["median"], "median_max")
                and at_most(pb["p90"], "p90_max")
            )
    return result


def recommendation(
    rows: tuple[Row, ...],
    gates: dict[str, dict[str, bool]],
    thresholds: dict[str, object],
) -> dict[str, object]:
    if any(all(g.values()) for g in gates.values()):
        return {
            "decision": "DETERMINISTIC PATH-ONLY SELECTION SUFFICIENT",
            "semantic_tasks": [],
            "content_tasks": [],
        }
    semantic: list[str] = []
    semantic_strata: set[str] = set()
    content: list[str] = []
    content_strata: set[str] = set()
    semantic_classes = {
        "semantic_relationship",
        "multi_file_relationship",
        "package_relationship",
        "context_relationship",
        "cross_directory_relationship",
    }
    for case in load():
        part = tuple(r for r in rows if r.fixture_id == case.fixture.id)
        if (
            case.information_gap == "visible"
            and case.failure_class in semantic_classes
            and all(not r.counts["exact"] for r in part)
            and min(r.counts["corrections"] for r in part)
            >= cast(int, thresholds["semantic_best_corrections_min"])
        ):
            semantic.append(case.fixture.id)
            semantic_strata.add(case.stratum)
        if case.information_gap == "content":
            content.append(case.fixture.id)
            content_strata.add(case.stratum)
    safe = all(g["safety"] for g in gates.values())
    model_gate = (
        safe
        and len(semantic) >= cast(int, thresholds["semantic_tasks_min"])
        and len(semantic_strata) >= cast(int, thresholds["semantic_strata_min"])
    )
    content_gate = len(content) >= cast(int, thresholds["content_tasks_min"]) and len(
        content_strata
    ) >= cast(int, thresholds["content_strata_min"])
    decision = "EVIDENCE INSUFFICIENT"
    if model_gate and not content_gate:
        decision = "MODEL PATH-ONLY SELECTOR JUSTIFIED"
    elif content_gate and not model_gate:
        decision = "CONTENT-ASSISTED DISCOVERY JUSTIFIED"
    return {
        "decision": decision,
        "model_gate": model_gate,
        "content_gate": content_gate,
        "semantic_tasks": semantic,
        "semantic_strata": sorted(semantic_strata),
        "content_tasks": content,
        "content_strata": sorted(content_strata),
    }


def report() -> dict[str, object]:
    verify_freeze()  # Before even the first held-out call.
    cases = load()
    rows = tuple(
        measure(c, m, select(c.fixture.objective, c.fixture.structure(), m))
        for m in METHODS
        for c in cases
    )
    thresholds = read("thresholds-v1.json")
    gates = {
        m: gate(tuple(r for r in rows if r.method == m), thresholds) for m in METHODS
    }
    return {
        "namespace": "discovery2a_holdout_v1",
        "evaluation_revision": 1,
        "report_schema": 1,
        "fixture_digest": digest(HERE / "fixtures-v1.json"),
        "truth_digest": digest(HERE / "truth-v1.json"),
        "manifest_digest": MANIFEST_DIGEST,
        "baseline_revision": 1,
        "baseline_digest": cast(
            dict[str, str], read("preregistration-v1.json")["original_digests"]
        )["baseline.py"],
        "baseline_methods": list(METHODS),
        "thresholds": thresholds,
        "model_calls": 0,
        "independence": "procedural, not statistically independent",
        "records": [asdict(r) for r in rows],
        "aggregates": {
            m: fold(tuple(r for r in rows if r.method == m)) for m in METHODS
        },
        "by_difficulty": {
            m: {
                d: fold(tuple(r for r in rows if r.method == m and r.difficulty == d))
                for d in DIFFICULTIES
            }
            for m in METHODS
        },
        "threshold_gates": gates,
        "recommendation": recommendation(rows, gates, thresholds),
    }


def render(value: dict[str, object]) -> str:
    lines = [
        "# DISCOVERY-2A.1 frozen results",
        "",
        "Synthetic counts only; no human timing or live models.",
        "",
        "| Method | Precision | Recall | Required recall | Exact | Abstention | False sufficient | Median / p90 / mean |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    aggregates = cast(dict[str, dict[str, object]], value["aggregates"])
    for method, a in aggregates.items():
        c = cast(dict[str, int], a["counts"])
        b = cast(dict[str, object], a["actionable_burden"])
        lines.append(
            f"| {method} | {a['precision']} | {a['recall']} | {a['required_recall']} | {c['exact']}/{c['actionable']} | {c['correct_abstain']}/{c['expected_abstain']} | {c['false_sufficient_selection']} | {b['median']} / {b['p90']} / {b['mean']} |"
        )
    lines += [
        "",
        "## Per-difficulty results",
        "",
        "| Method | Difficulty | Precision | Recall | Required recall | Exact | Abstention | Median / p90 / mean |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m, parts in cast(
        dict[str, dict[str, dict[str, object]]], value["by_difficulty"]
    ).items():
        for d, a in parts.items():
            c = cast(dict[str, int], a["counts"])
            b = cast(dict[str, object], a["actionable_burden"])
            lines.append(
                f"| {m} | {d} | {a['precision']} | {a['recall']} | {a['required_recall']} | {c['exact']}/{c['actionable']} | {c['correct_abstain']}/{c['expected_abstain']} | {b['median']} / {b['p90']} / {b['mean']} |"
            )
    lines += [
        "",
        "## Per-fixture results",
        "",
        "| ID | Method | Difficulty | Status | Exact | False sufficient | REMOVE / ADD / REJECT / CLARIFY / CREATE | Failure |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in cast(list[dict[str, object]], value["records"]):
        c = cast(dict[str, int], r["counts"])
        operations = " / ".join(
            str(c[k]) for k in ("remove", "add", "reject", "clarify", "create")
        )
        lines.append(
            f"| {r['fixture_id']} | {r['method']} | {r['difficulty']} | {r['status']} | {c['exact']} | {c['false_sufficient_selection']} | {operations} | {r['failure_class']} |"
        )
    lines += [
        "",
        "## Threshold pass/fail matrix",
        "",
        "| Gate | lexical | path_score | conservative |",
        "| --- | --- | --- | --- |",
    ]
    gates = cast(dict[str, dict[str, bool]], value["threshold_gates"])
    for key in gates["lexical"]:
        lines.append(
            "| "
            + key
            + " | "
            + " | ".join("PASS" if gates[m][key] else "FAIL" for m in METHODS)
            + " |"
        )
    lines += ["", str(cast(dict[str, object], value["recommendation"])["decision"]), ""]
    return "\n".join(lines)


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, sort_keys=True))
