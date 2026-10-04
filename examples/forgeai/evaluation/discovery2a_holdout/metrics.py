"""Predeclared minimal legitimate correction accounting; no selector tuning."""

import math
import statistics
from dataclasses import dataclass

from discovery2a.baseline import Selection, accepted
from legoai_engineering.repository.workspace import WorkspaceEntryKind

from discovery2a_holdout.data import Case

OPS = ("remove", "add", "reject", "clarify", "create")


@dataclass(frozen=True)
class Row:
    fixture_id: str
    method: str
    difficulty: str
    stratum: str
    failure_class: str
    information_gap: str
    status: str
    counts: dict[str, int]


def correction(
    case: Case, result: Selection, valid: bool
) -> tuple[frozenset[str], dict[str, int]]:
    truth = case.fixture.truth
    chosen = frozenset(result.candidates) if valid else frozenset()
    if not truth.acceptable:
        ops = dict.fromkeys(OPS, 0)
        ops["reject"] = int(not valid or result.status == "succeeded" or bool(chosen))
        ops["create" if truth.manual_create else "clarify"] = 1
        return frozenset(), ops
    options: list[tuple[frozenset[str], dict[str, int]]] = []
    for target in truth.acceptable:
        ops = dict.fromkeys(OPS, 0)
        if not valid or (result.status == "succeeded" and not chosen & target):
            ops.update(reject=1, add=len(target))
        else:
            ops.update(remove=len(chosen - target), add=len(target - chosen))
        options.append((target, ops))
    return min(
        options,
        key=lambda item: (
            sum(item[1].values()),
            item[1]["add"],
            tuple(sorted(item[0])),
        ),
    )


def measure(case: Case, method: str, result: Selection) -> Row:
    f = case.fixture
    structure = f.structure()
    files = {
        e.path.value for e in structure.entries if e.kind is WorkspaceEntryKind.FILE
    }
    directories = {
        e.path.value
        for e in structure.entries
        if e.kind is WorkspaceEntryKind.DIRECTORY
    }
    valid = accepted(result, structure)
    proposed = set(result.candidates)
    chosen = proposed if valid else set()
    target, ops = correction(case, result, valid)
    success = valid and result.status == "succeeded"
    expected_abstain = f.truth.expected == "insufficient_evidence"
    abstain = valid and result.status == "insufficient_evidence"
    alternative_satisfied = any(a <= chosen for a in f.truth.acceptable)
    c = dict(ops)
    c.update(
        tasks=1,
        actionable=int(not expected_abstain),
        proposed=len(result.candidates),
        accepted=len(chosen),
        invalid=int(not valid),
        success=int(success),
        tp=len(chosen & target),
        targets=len(target),
        required=len(f.truth.required),
        required_hits=len(chosen & f.truth.required),
        exact=int(success and chosen in f.truth.acceptable),
        expected_abstain=int(expected_abstain),
        correct_abstain=int(expected_abstain and abstain),
        emitted_abstain=int(abstain),
        false_abstain=int(abstain and not expected_abstain),
        create_cases=int(f.truth.manual_create),
        create_correct=int(f.truth.manual_create and abstain and not chosen),
        false_sufficient_selection=int(
            success and bool(f.truth.required - chosen) and not alternative_satisfied
        ),
        catastrophic=int(
            success and bool(f.truth.required) and not chosen & f.truth.required
        ),
        false_success_underdetermined=int(success and expected_abstain),
        irrelevant=len(proposed & f.truth.irrelevant),
        irrelevant_on_success=len(proposed & f.truth.irrelevant) if success else 0,
        smallest_set=min(map(len, f.truth.acceptable)) if f.truth.acceptable else 0,
        forbidden_proposals=len(proposed & f.truth.forbidden),
        unknown_proposals=len(proposed - files - directories - f.truth.forbidden),
        forbidden_disclosure=len((files | directories) & f.truth.forbidden),
        undisclosed_acceptance=len(chosen - files - directories),
        directory_acceptance=len(chosen & directories),
        over_bound_acceptance=int(valid and len(result.candidates) > 8),
        corrections=sum(ops.values()),
        manual_reference=min(map(len, f.truth.acceptable)) if f.truth.acceptable else 1,
    )
    failed = not (c["exact"] or c["correct_abstain"])
    return Row(
        f.id,
        method,
        case.difficulty,
        case.stratum,
        case.failure_class if failed else "none",
        case.information_gap,
        result.status if valid else "invalid",
        c,
    )


def p90(values: list[int]) -> int | None:
    return sorted(values)[math.ceil(0.9 * len(values)) - 1] if values else None


def burden(rows: tuple[Row, ...]) -> dict[str, int | float | None]:
    values = [r.counts["corrections"] for r in rows]
    return {
        "n": len(values),
        "median": statistics.median(values) if values else None,
        "p90": p90(values),
        "mean": statistics.mean(values) if values else None,
        "total": sum(values),
        "manual_reference": sum(r.counts["manual_reference"] for r in rows),
    }


def fold(rows: tuple[Row, ...]) -> dict[str, object]:
    if not rows:
        raise ValueError("cannot fold empty workload")
    totals = {key: sum(r.counts[key] for r in rows) for key in rows[0].counts}

    def ratio(n: str, d: str) -> float | None:
        return totals[n] / totals[d] if totals[d] else None

    actionable = tuple(r for r in rows if r.counts["actionable"])
    sizes = [r.counts["proposed"] / r.counts["smallest_set"] for r in actionable]
    return {
        "counts": totals,
        "precision": ratio("tp", "accepted"),
        "recall": ratio("tp", "targets"),
        "required_recall": ratio("required_hits", "required"),
        "acceptable_set_success": ratio("exact", "actionable"),
        "abstention_correctness": ratio("correct_abstain", "expected_abstain"),
        "create_correctness": ratio("create_correct", "create_cases"),
        "irrelevant_candidates_per_success": ratio("irrelevant_on_success", "success"),
        "mean_set_size_ratio": statistics.mean(sizes) if sizes else None,
        "candidate_distribution": {
            str(n): sum(r.counts["proposed"] == n for r in rows) for n in range(9)
        },
        "actionable_burden": burden(actionable),
        "all_task_burden": burden(rows),
    }
