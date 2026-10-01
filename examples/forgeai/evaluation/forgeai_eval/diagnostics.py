"""LQ1.2 failure diagnostics: per-run records and their aggregate fold.

Per run, observed reply diagnoses are reconciled with ForgeAI's own typed
evidence, which stays authoritative:

- a call ForgeAI recorded as a model failure is MODEL_FAILURE, whatever the
  transport saw;
- an observed classification that disagrees with ForgeAI's verdict (or, for a
  valid reply, with the parsed proposal or review itself, by in-memory
  fingerprint) is CLASSIFIER_DISAGREEMENT and counted, never hidden;
- calls that cannot be matched to evidence are OBSERVATION_UNAVAILABLE.

Check diagnostics come from the bounded check output in `CheckRecord`.
`fold` computes every aggregate from the per-run records alone, so the report
aggregate is always re-derivable from its own run rows.
"""

from collections import Counter
from dataclasses import asdict

from legoai.execution.agent.values import AgentExecutionStatus
from legoai_engineering.checks.values import CheckKind
from legoai_engineering.coding.values import CodingStatus
from legoai_engineering.reviewer.values import ReviewStatus

from forgeai.domain import AttemptEvidence
from forgeai_eval.checkdiag import (
    PYTEST_DIAGNOSTIC_UNAVAILABLE,
    RUFF_DIAGNOSTIC_UNAVAILABLE,
    check_diagnostic,
)
from forgeai_eval.observer import Observation, Stage
from forgeai_eval.outputs import (
    CodingDiagnostic,
    ReviewDiagnostic,
    proposal_fingerprint,
    review_fingerprint,
)
from forgeai_eval.runner import FixtureRun

DIAGNOSTIC_DEFINITIONS: dict[str, str] = {
    "diagnostics.coding_output": "per Coding invocation, the first stage of "
    "the existing contract that rejected the reply (or valid / model_failure); "
    "content-free; fenced JSON is response_not_json",
    "diagnostics.reviewer_output": "per Reviewer invocation, the first "
    "rejecting stage of the existing review contract",
    "diagnostics.ruff": "rule-code counts of failed ruff_check runs; "
    "RUFF_DIAGNOSTIC_UNAVAILABLE when Ruff's own total cannot be reconciled",
    "diagnostics.pytest": "failure-kind counts of failed pytest runs; "
    "PYTEST_DIAGNOSTIC_UNAVAILABLE when pytest's own totals cannot be "
    "reconciled",
    "diagnostics.observation": "how replies were observed: calls, transports, "
    "classifier disagreements and unavailable observations",
}

_MODEL_FAILURES = {
    AgentExecutionStatus.MODEL_FAILED,
    AgentExecutionStatus.ROUTING_FAILED,
}
_CONTRACT = {
    CodingDiagnostic.OUTPUT_LIMIT.value,
    CodingDiagnostic.OUTPUT_TEXT_INVALID.value,
}


def _entry(
    attempt: int,
    category: str,
    status: str | None,
    observation: Observation | None,
) -> dict[str, object]:
    diagnosis = observation.diagnosis if observation is not None else None
    return {
        "attempt": attempt,
        "category": category,
        "output_status": status,
        "transport": observation.transport.value if observation else None,
        "features": asdict(diagnosis.features) if diagnosis is not None else None,
    }


def _coding(
    attempt: AttemptEvidence, observation: Observation | None
) -> dict[str, object]:
    C = CodingDiagnostic
    status = attempt.coding_status.value if attempt.coding_status else None
    if attempt.agent_status in _MODEL_FAILURES:
        return _entry(attempt.number, C.MODEL_FAILURE, status, observation)
    if observation is None or observation.diagnosis is None:
        return _entry(attempt.number, C.OBSERVATION_UNAVAILABLE, status, observation)
    diagnosis = observation.diagnosis
    valid = diagnosis.category == C.VALID
    agrees = valid == (attempt.coding_status is CodingStatus.SUCCEEDED)
    agrees &= (diagnosis.category in _CONTRACT) == (
        attempt.agent_status is AgentExecutionStatus.OUTPUT_INVALID
    )
    if valid and agrees:
        agrees = (
            attempt.proposal is not None
            and diagnosis.fingerprint == proposal_fingerprint(attempt.proposal)
        )
    category = diagnosis.category if agrees else C.CLASSIFIER_DISAGREEMENT
    return _entry(attempt.number, category, status, observation)


def _review(
    attempt: AttemptEvidence, observation: Observation | None
) -> dict[str, object]:
    R = ReviewDiagnostic
    result = attempt.review
    assert result is not None and result.agent_result is not None
    status = result.status.value
    agent_status = result.agent_result.status
    if agent_status in _MODEL_FAILURES:
        return _entry(attempt.number, R.MODEL_FAILURE, status, observation)
    if observation is None or observation.diagnosis is None:
        return _entry(attempt.number, R.OBSERVATION_UNAVAILABLE, status, observation)
    diagnosis = observation.diagnosis
    valid = diagnosis.category == R.VALID
    agrees = valid == (result.status is ReviewStatus.COMPLETED)
    agrees &= (diagnosis.category in _CONTRACT) == (
        agent_status is AgentExecutionStatus.OUTPUT_INVALID
    )
    if valid and agrees:
        agrees = result.review is not None and diagnosis.fingerprint == (
            review_fingerprint(result.review)
        )
    category = diagnosis.category if agrees else R.CLASSIFIER_DISAGREEMENT
    return _entry(attempt.number, category, status, observation)


def run_diagnostics(run: FixtureRun) -> dict[str, object]:
    """The content-free LQ1.2 record of one run."""
    attempts = run.task_result.evidence.attempts
    observed = run.observation_complete is not None
    stages = {
        stage: [o for o in run.observations if o.stage is stage] for stage in Stage
    }
    coding_calls = [
        a
        for a in attempts
        if a.agent_status is not None
        and a.agent_status is not AgentExecutionStatus.ROUTING_FAILED
    ]
    review_calls = [
        a
        for a in attempts
        if a.review is not None
        and a.review.agent_result is not None
        and a.review.agent_result.status is not AgentExecutionStatus.ROUTING_FAILED
    ]
    anomalies: Counter[str] = Counter()
    if observed and not run.observation_complete:
        anomalies["call_in_flight_at_close"] += 1
    if stages[Stage.UNKNOWN]:
        anomalies["unidentified_call"] += len(stages[Stage.UNKNOWN])

    def matched(stage: Stage, calls: list[AttemptEvidence]) -> list[Observation | None]:
        found = stages[stage]
        if observed and len(found) == len(calls):
            return list(found)
        if observed:
            anomalies[f"{stage.value}_call_count_mismatch"] += 1
        return [None] * len(calls)

    coding = [
        _coding(a, o)
        for a, o in zip(coding_calls, matched(Stage.CODING, coding_calls), strict=True)
    ]
    reviews = [
        _review(a, o)
        for a, o in zip(review_calls, matched(Stage.REVIEW, review_calls), strict=True)
    ]
    checks: list[dict[str, object]] = []
    for attempt in attempts:
        for record in attempt.checks:
            detail = check_diagnostic(record)
            if detail is not None:
                checks.append(
                    {
                        "attempt": attempt.number,
                        "kind": record.request.kind.value,
                        **detail,
                    }
                )
    return {
        "observed": observed,
        "coding": coding,
        "review": reviews,
        "checks": checks,
        "anomalies": dict(sorted(anomalies.items())),
    }


def _counts(items: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(items).items()))


def _sum_counts(entries: list[dict[str, object]], key: str) -> dict[str, int]:
    total: Counter[str] = Counter()
    for entry in entries:
        counts = entry.get(key)
        if isinstance(counts, dict):
            total.update({str(k): int(v) for k, v in counts.items()})
    return dict(sorted(total.items()))


def fold(rows: list[dict[str, object]]) -> dict[str, object]:
    """Aggregate diagnostics from report run rows ({"fixture", "diagnostics"})."""
    per_run = [(str(row["fixture"]), row["diagnostics"]) for row in rows]
    records = [(fixture, d) for fixture, d in per_run if isinstance(d, dict)]

    def entries(
        part: str, fixture: str | None = None, kind: str | None = None
    ) -> list[dict[str, object]]:
        found: list[dict[str, object]] = []
        for name, record in records:
            if fixture is not None and name != fixture:
                continue
            for entry in record[part]:
                if kind is None or entry["kind"] == kind:
                    found.append(entry)
        return found

    fixtures = sorted({name for name, _ in records})
    coding = entries("coding")
    reviews = entries("review")
    calls = coding + reviews
    anomalies: Counter[str] = Counter()
    for _, record in records:
        anomalies.update(record["anomalies"])

    def categories(part: str, fixture: str) -> list[str]:
        return [str(e["category"]) for e in entries(part, fixture)]

    def check_part(kind: CheckKind, key: str) -> dict[str, object]:
        unavailable_status = (
            RUFF_DIAGNOSTIC_UNAVAILABLE
            if kind is CheckKind.RUFF_CHECK
            else PYTEST_DIAGNOSTIC_UNAVAILABLE
        )
        found = entries("checks", kind=kind.value)
        return {
            "failed_checks": len(found),
            "unavailable": sum(1 for e in found if e["status"] == unavailable_status),
            key: _sum_counts(found, key),
            f"per_fixture_{key}": {
                fixture: _sum_counts(entries("checks", fixture, kind.value), key)
                for fixture in fixtures
                if entries("checks", fixture, kind.value)
            },
        }

    return {
        "coding_output": {
            "counts_by_category": _counts([str(e["category"]) for e in coding]),
            "per_fixture_counts": {
                fixture: _counts(categories("coding", fixture))
                for fixture in fixtures
                if categories("coding", fixture)
            },
            "markdown_fence_replies": sum(
                1
                for e in coding
                if isinstance(e["features"], dict) and e["features"]["markdown_fence"]
            ),
        },
        "reviewer_output": {
            "counts_by_category": _counts([str(e["category"]) for e in reviews]),
            "per_fixture_counts": {
                fixture: _counts(categories("review", fixture))
                for fixture in fixtures
                if categories("review", fixture)
            },
        },
        "ruff": check_part(CheckKind.RUFF_CHECK, "rule_counts"),
        CheckKind.PYTEST.value: check_part(CheckKind.PYTEST, "kind_counts"),
        "observation": {
            "runs_observed": sum(1 for _, record in records if record["observed"]),
            "calls": len(calls),
            "transport": _counts(
                [str(e["transport"]) for e in calls if e["transport"] is not None]
            ),
            "classifier_disagreements": sum(
                1 for e in calls if e["category"] == "classifier_disagreement"
            ),
            "observation_unavailable": sum(
                1 for e in calls if e["category"] == "observation_unavailable"
            ),
            "anomalies": dict(sorted(anomalies.items())),
        },
    }
