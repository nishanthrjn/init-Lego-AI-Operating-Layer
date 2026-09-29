"""Typed-value metrics for LQ1; nothing is parsed from human-readable output.

Each run is first reduced to a content-free `RunSummary` built only from
TaskResult, AttemptEvidence, ReviewResult, CheckResult and harness timings.
Aggregates are computed from summaries, so per-fixture and overall numbers
share one definition. Reviewer-derived figures are MODEL-JUDGE MEASUREMENTS.
"""

from collections import Counter
from dataclasses import dataclass
from statistics import mean

from legoai.kernel.effects import EffectExtent
from legoai_engineering.authorization import EffectAuthorizationFailure
from legoai_engineering.reviewer.values import (
    FindingCategory,
    FindingSeverity,
    ReviewStatus,
)

from forgeai.domain import AttemptEvidence
from forgeai_eval.runner import FixtureRun

MODEL_JUDGE = "MODEL-JUDGE MEASUREMENT"
PER_CALL_LATENCY: dict[str, object] = {
    "status": "unavailable",
    "reason": "per-model-call latency is not observable through the public "
    "ForgeAI/LegoAI APIs; LQ1 adds no tracing",
}

DEFINITIONS: dict[str, str] = {
    "runs": "evaluation runs = fixtures x repetitions; every run is counted",
    "succeeded_rate": "runs with disposition SUCCEEDED / runs",
    "rejected_rate": "runs with disposition REJECTED / runs",
    "failed_rate": "runs with disposition FAILED / runs",
    "hidden_pass_rate": "runs whose hidden acceptance tests PASSED / runs "
    "(NOT_RUN and ERROR count as not passed)",
    "succeeded_and_hidden_pass_rate": "runs SUCCEEDED and hidden PASSED / runs",
    "succeeded_but_hidden_fail_rate": "runs SUCCEEDED and hidden FAILED / "
    "SUCCEEDED runs",
    "coding_output_invalid_rate": "attempts with Coding status output_invalid / "
    "attempts that invoked the Coding Agent (succeeded, model_failure or "
    "output_invalid)",
    "review_output_invalid_rate": "reviews with status output_invalid / reviews "
    "with an Agent result",
    "checks_attempt_N": "per check kind, outcome counts over attempts numbered N: "
    "passed, failed, interrupted, no_tests, error, error:<infrastructure>, "
    "denied, not_run",
    "review_N": "decision distribution of review N: accept, changes_required, "
    "insufficient_evidence, not_completed:<status>, input_failed, not_run",
    "judge_vs_hidden": f"{MODEL_JUDGE}: final review label x hidden outcome over "
    "runs with a final review",
    "accept_but_hidden_fail": f"{MODEL_JUDGE}: final review accept AND hidden "
    "FAILED; a count of observations, not a calibrated false-positive rate",
    "rework_invocation_rate": "runs with a second attempt / runs",
    "rework_recovery_rate": "runs with review 1 changes_required, final review "
    "accept and hidden PASSED / runs with a second attempt",
    "failed_recovery": "for reworked runs not recovered: the TaskFailure name, "
    "or succeeded_hidden_<outcome>",
    "model_invocations": "Agent invocations recorded in evidence per run: coding "
    "attempts with an Agent status plus reviews with an Agent result",
    "unknown_model_effects": "recorded invocations whose model effect is UNKNOWN",
    "testing_findings": f"{MODEL_JUDGE}: review findings in the testing category",
    "hidden_fail_without_testing_blocker": "runs with hidden FAILED whose final "
    "review has no blocking testing finding (an M8.4 signal, not a decision)",
}


@dataclass(frozen=True, slots=True)
class RunSummary:
    """Content-free view of one run: identifiers, enums, counts, timings."""

    fixture: str
    repetition: int
    disposition: str
    failure: str | None
    attempts: int
    coding: tuple[str | None, ...]
    checks: tuple[tuple[tuple[str, str], ...], ...]
    reviews: tuple[str, ...]
    review_invoked: tuple[bool, ...]
    final_review: str
    final_blocking_testing_finding: bool
    testing_findings: int
    hidden: str
    hidden_error: str | None
    model_invocations: int
    unknown_model_effects: int
    run_seconds: float
    hidden_seconds: float


def _review_label(attempt: AttemptEvidence) -> str:
    review = attempt.review
    if review is None:
        return "input_failed" if attempt.review_input_failure else "not_run"
    if review.status is ReviewStatus.COMPLETED and review.review is not None:
        return review.review.decision.value
    return f"not_completed:{review.status.value}"


def _check_labels(
    attempt: AttemptEvidence, kinds: tuple[str, ...]
) -> tuple[tuple[str, str], ...]:
    labels = dict.fromkeys(kinds, "not_run")
    for record in attempt.checks:
        kind = record.request.kind.value
        if record.result is not None:
            labels[kind] = record.result.outcome.value
        elif record.workspace_error:
            labels[kind] = "error:workspace"
        elif isinstance(record.error, EffectAuthorizationFailure):
            labels[kind] = "denied"
        elif record.error is not None:
            labels[kind] = "error:" + record.error.name.lower()
    return tuple(labels.items())


def summarize_run(run: FixtureRun) -> RunSummary:
    result = run.task_result
    evidence = result.evidence
    kinds = tuple(request.kind.value for request in evidence.planned_checks)
    attempts = evidence.attempts
    invocations = unknown = testing = 0
    for attempt in attempts:
        if attempt.agent_status is not None:
            invocations += 1
            unknown += attempt.model_effect is EffectExtent.UNKNOWN
        review = attempt.review
        if review is not None and review.agent_result is not None:
            invocations += 1
            execution = review.agent_result.model_execution
            unknown += (
                execution is not None and execution.effect is EffectExtent.UNKNOWN
            )
        if review is not None and review.review is not None:
            testing += sum(
                finding.category is FindingCategory.TESTING
                for finding in review.review.findings
            )
    final = attempts[-1] if attempts else None
    final_review = final.review if final is not None else None
    blocking = (
        final_review is not None
        and final_review.review is not None
        and any(
            finding.category is FindingCategory.TESTING
            and finding.severity is FindingSeverity.BLOCKING
            for finding in final_review.review.findings
        )
    )
    return RunSummary(
        fixture=run.fixture_id,
        repetition=run.repetition,
        disposition=result.disposition.value,
        failure=result.failure.name if result.failure is not None else None,
        attempts=len(attempts),
        coding=tuple(
            attempt.coding_status.value if attempt.coding_status else None
            for attempt in attempts
        ),
        checks=tuple(_check_labels(attempt, kinds) for attempt in attempts),
        reviews=tuple(_review_label(attempt) for attempt in attempts),
        review_invoked=tuple(
            attempt.review is not None and attempt.review.agent_result is not None
            for attempt in attempts
        ),
        final_review=_review_label(final) if final is not None else "not_run",
        final_blocking_testing_finding=blocking,
        testing_findings=testing,
        hidden=run.hidden.outcome.value,
        hidden_error=run.hidden.error,
        model_invocations=invocations,
        unknown_model_effects=unknown,
        run_seconds=round(run.run_seconds, 3),
        hidden_seconds=round(run.hidden_seconds, 3),
    )


def _rate(numerator: int, denominator: int) -> dict[str, object]:
    rate: dict[str, object] = {
        "numerator": numerator,
        "denominator": denominator,
        "value": round(numerator / denominator, 4) if denominator else None,
    }
    if not denominator:
        rate["note"] = "no eligible runs"
    return rate


def _stats(values: list[float]) -> dict[str, object]:
    if not values:
        return {"status": "unavailable", "reason": "no runs"}
    return {
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "mean": round(mean(values), 3),
        "total": round(sum(values), 3),
    }


def _distribution(labels: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(labels).items()))


def _checks(summaries: list[RunSummary], index: int) -> dict[str, dict[str, int]]:
    table: dict[str, Counter[str]] = {}
    for summary in summaries:
        if len(summary.checks) > index:
            for kind, label in summary.checks[index]:
                table.setdefault(kind, Counter())[label] += 1
    return {kind: dict(sorted(table[kind].items())) for kind in sorted(table)}


def aggregate(summaries: list[RunSummary]) -> dict[str, object]:
    runs = len(summaries)
    succeeded = [s for s in summaries if s.disposition == "succeeded"]
    rejected = [s for s in summaries if s.disposition == "rejected"]
    failed = [s for s in summaries if s.disposition == "failed"]
    invoked_coding = [
        c
        for s in summaries
        for c in s.coding
        if c in {"succeeded", "model_failure", "output_invalid"}
    ]
    invoked_reviews = [
        label
        for s in summaries
        for label, invoked in zip(s.reviews, s.review_invoked, strict=True)
        if invoked
    ]
    judged = [s for s in summaries if s.final_review not in {"not_run", "input_failed"}]
    matrix: dict[str, Counter[str]] = {}
    for summary in judged:
        matrix.setdefault(summary.final_review, Counter())[summary.hidden] += 1
    reworked = [s for s in summaries if s.attempts == 2]
    recovered = [
        s
        for s in reworked
        if s.reviews[0] == "changes_required"
        and s.final_review == "accept"
        and s.hidden == "passed"
    ]

    def judged_count(review: str, hidden: str) -> int:
        return sum(
            1 for s in summaries if s.final_review == review and s.hidden == hidden
        )

    return {
        "runs": runs,
        "completion": {
            "succeeded": len(succeeded),
            "rejected": len(rejected),
            "failed": len(failed),
            "succeeded_rate": _rate(len(succeeded), runs),
            "rejected_rate": _rate(len(rejected), runs),
            "failed_rate": _rate(len(failed), runs),
        },
        "hidden": {
            "outcomes": _distribution([s.hidden for s in summaries]),
            "hidden_pass_rate": _rate(
                sum(s.hidden == "passed" for s in summaries), runs
            ),
            "succeeded_and_hidden_pass_rate": _rate(
                sum(s.hidden == "passed" for s in succeeded), runs
            ),
            "succeeded_but_hidden_fail_rate": _rate(
                sum(s.hidden == "failed" for s in succeeded), len(succeeded)
            ),
        },
        "structured_output": {
            "coding_output_invalid_rate": _rate(
                invoked_coding.count("output_invalid"), len(invoked_coding)
            ),
            "review_output_invalid_rate": _rate(
                invoked_reviews.count("not_completed:output_invalid"),
                len(invoked_reviews),
            ),
        },
        "checks_attempt_1": _checks(summaries, 0),
        "checks_attempt_2": _checks(summaries, 1),
        "review_1": _distribution([s.reviews[0] for s in summaries if s.reviews]),
        "review_2": _distribution(
            [s.reviews[1] for s in summaries if len(s.reviews) > 1]
        ),
        "judge_vs_hidden": {
            "label": MODEL_JUDGE,
            "matrix": {
                key: dict(sorted(matrix[key].items())) for key in sorted(matrix)
            },
            "accept_but_hidden_fail": judged_count("accept", "failed"),
            "accept_and_hidden_pass": judged_count("accept", "passed"),
            "changes_required_and_hidden_pass": judged_count(
                "changes_required", "passed"
            ),
            "changes_required_and_hidden_fail": judged_count(
                "changes_required", "failed"
            ),
            "insufficient_evidence": sum(
                1 for s in summaries if s.final_review == "insufficient_evidence"
            ),
        },
        "rework": {
            "rework_invocation_rate": _rate(len(reworked), runs),
            "rework_recovery_rate": _rate(len(recovered), len(reworked)),
            "failed_recovery": _distribution(
                [
                    s.failure if s.failure else f"succeeded_hidden_{s.hidden}"
                    for s in reworked
                    if s not in recovered
                ]
            ),
        },
        "execution": {
            "model_invocations": _stats(
                [float(s.model_invocations) for s in summaries]
            ),
            "run_seconds": _stats([s.run_seconds for s in summaries]),
            "hidden_seconds": _stats([s.hidden_seconds for s in summaries]),
            "per_model_call_latency": PER_CALL_LATENCY,
            "task_failures": _distribution([s.failure for s in summaries if s.failure]),
            "unknown_model_effects": sum(s.unknown_model_effects for s in summaries),
        },
        "m8_4_signals": {
            "label": MODEL_JUDGE,
            "testing_findings": sum(s.testing_findings for s in summaries),
            "hidden_fail_without_testing_blocker": sum(
                1
                for s in summaries
                if s.hidden == "failed" and not s.final_blocking_testing_finding
            ),
        },
    }
