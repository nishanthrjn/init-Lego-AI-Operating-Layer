"""Count-only evaluation reports; alternatives are scored as coherent sets."""

import json
from dataclasses import dataclass

from legoai_engineering.repository.structure import RepositoryStructure, StructureError
from legoai_engineering.repository.workspace import WorkspaceEntryKind

from discovery2a.baseline import METHODS, Selection, accepted, select
from discovery2a.fixtures import Fixture, load


@dataclass(frozen=True)
class Record:
    fixture_id: str
    method: str
    outcome: str
    failure_category: str
    counts: dict[str, int]


def measure(
    f: Fixture, method: str, result: Selection, structure: RepositoryStructure
) -> Record:
    proposed = set(result.candidates)
    files = {
        e.path.value for e in structure.entries if e.kind is WorkspaceEntryKind.FILE
    }
    known = {e.path.value for e in structure.entries}
    valid = accepted(result, structure)
    chosen = proposed if valid else set()
    # Pick one minimum-edit coherent acceptable set; lexical tuple resolves ties.
    target = (
        min(f.truth.acceptable, key=lambda a: (len(chosen ^ a), tuple(sorted(a))))
        if f.truth.acceptable
        else frozenset()
    )
    tp = len(chosen & target)
    removed, added = len(chosen - target), len(target - chosen)
    expected_insufficient = f.truth.expected == "insufficient_evidence"
    rejected = not valid or (
        expected_insufficient and result.status != "insufficient_evidence"
    )
    exact = valid and result.status == "succeeded" and chosen in f.truth.acceptable
    status_correct = valid and result.status == f.truth.expected
    counts = {
        "runs": 1,
        "eligible": int(bool(f.truth.acceptable)),
        "acquisition_blocked": 0,
        "presented": 1,
        "invalid_proposals": int(not valid),
        "proposed_candidates": len(result.candidates),
        "accepted_candidates": len(chosen),
        "true_positive": tp,
        "target_paths": len(target),
        "exact": int(exact),
        "required_hits": len(chosen & f.truth.required),
        "required_paths": len(f.truth.required),
        "irrelevant_paths": len(proposed & f.truth.irrelevant),
        "forbidden_proposals": len(proposed & f.truth.forbidden),
        "unknown_proposals": len(proposed - known - f.truth.forbidden),
        "non_file_proposals": len(proposed & (known - files)),
        "unauthorized_acceptance": len(chosen - files),
        "forbidden_disclosure": len(known & f.truth.forbidden),
        "removed": removed,
        "added": added,
        "over_selection": int(removed > 0),
        "under_selection": int(added > 0),
        "rejected": int(rejected),
        "correction_runs": int(bool(removed or added or rejected)),
        "correction_operations": removed + added + int(rejected),
        "manual_create": int(f.truth.manual_create),
        "clarification": int(valid and result.status == "insufficient_evidence"),
        "insufficient_expected": int(expected_insufficient),
        "insufficient_correct": int(expected_insufficient and status_correct),
        "status_correct": int(status_correct),
    }
    return Record(
        f.id,
        method,
        result.status if valid else "invalid",
        "none"
        if exact or (expected_insufficient and status_correct)
        else f.failure_category,
        counts,
    )


def evaluate(f: Fixture, method: str) -> Record:
    try:
        structure = f.structure()
    except StructureError:
        if not f.truth.acquisition_blocked:
            raise
        # No selection was presented, not a successful selector abstention.
        counts = {key: 0 for key in COUNT_KEYS}
        counts.update(runs=1, acquisition_blocked=1)
        return Record(f.id, method, "acquisition_blocked", "acquisition_limit", counts)
    return measure(f, method, select(f.objective, structure, method), structure)


COUNT_KEYS = (
    "runs",
    "eligible",
    "acquisition_blocked",
    "presented",
    "invalid_proposals",
    "proposed_candidates",
    "accepted_candidates",
    "true_positive",
    "target_paths",
    "exact",
    "required_hits",
    "required_paths",
    "irrelevant_paths",
    "forbidden_proposals",
    "unknown_proposals",
    "non_file_proposals",
    "unauthorized_acceptance",
    "forbidden_disclosure",
    "removed",
    "added",
    "over_selection",
    "under_selection",
    "rejected",
    "correction_runs",
    "correction_operations",
    "manual_create",
    "clarification",
    "insufficient_expected",
    "insufficient_correct",
    "status_correct",
)


def fold(rows: tuple[Record, ...]) -> dict[str, object]:
    totals = {key: sum(r.counts[key] for r in rows) for key in COUNT_KEYS}
    distribution = {
        str(n): sum(
            r.counts["proposed_candidates"] == n for r in rows if r.counts["presented"]
        )
        for n in range(9)
    }

    def rate(n: str, d: str) -> float | None:
        return totals[n] / totals[d] if totals[d] else None

    return {
        "counts": totals,
        "candidate_count_distribution": distribution,
        "candidate_precision": rate("true_positive", "accepted_candidates"),
        "candidate_recall": rate("true_positive", "target_paths"),
        "required_path_recall": rate("required_hits", "required_paths"),
        "exact_acceptable_set_rate": rate("exact", "eligible"),
        "operator_correction_rate": rate("correction_runs", "presented"),
        "insufficient_evidence_correctness": rate(
            "insufficient_correct", "insufficient_expected"
        ),
    }


def report() -> dict[str, object]:
    fixtures = load()
    rows = tuple(evaluate(f, method) for method in METHODS for f in fixtures)
    # Explicit projection: no maps, objective, candidates, prompts or free text.
    return {
        "namespace": "forgeai-discovery-paths",
        "fixture_revision": 1,
        "report_schema": 1,
        "baseline_revision": 1,
        "model_calls": 0,
        "records": [
            {
                "fixture_id": r.fixture_id,
                "method": r.method,
                "outcome": r.outcome,
                "failure_category": r.failure_category,
                "counts": r.counts,
            }
            for r in rows
        ],
        "aggregates": {
            m: fold(tuple(r for r in rows if r.method == m)) for m in METHODS
        },
    }


if __name__ == "__main__":
    print(json.dumps(report(), sort_keys=True, indent=2))
