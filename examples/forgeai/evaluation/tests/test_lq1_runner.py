"""Replay self-test scenarios with known outcomes and exact aggregate metrics.

Replay mode exercises the harness only; it is never live-model evidence.
ForgeAI's checks and the oracle use recording fake sandboxes here; the real
Docker path is covered by test_lq1_fixtures_docker.py.
"""

from pathlib import Path

import pytest
from eval_support import (
    REVIEW_ACCEPT,
    fixture,
    metadata,
    reference,
    replay_settings,
)
from forgeai_support import REVIEW_CHANGES, REWORK
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure

from forgeai_eval.fixtures import FixtureSet
from forgeai_eval.hidden import HiddenOutcome
from forgeai_eval.report import build_report
from forgeai_eval.runner import FixtureRun, evaluate_run

STOCK = "stock-validation"


def scenario(tmp_path: Path, number: int) -> FixtureRun:
    item = fixture(STOCK)
    good = reference(item)
    cases: dict[int, dict[str, object]] = {
        1: {"outputs": (good, REVIEW_ACCEPT)},
        2: {"outputs": (good, REVIEW_ACCEPT), "hidden_exits": (1,)},
        3: {"outputs": (good, REVIEW_CHANGES, REWORK, REVIEW_ACCEPT)},
        4: {"outputs": ("not a proposal", REVIEW_ACCEPT)},
        5: {"outputs": (good, "not json")},
        6: {"outputs": (good, REVIEW_ACCEPT), "forge_exits": (0, 1, 0)},
        7: {
            "outputs": (good, REVIEW_ACCEPT),
            "hidden_error": SandboxError(SandboxFailure.RUNTIME_UNAVAILABLE),
        },
    }
    case = cases[number]
    settings, model, _, _ = replay_settings(
        tmp_path / f"s{number}",
        case["outputs"],  # type: ignore[arg-type]
        forge_exits=case.get("forge_exits", (0, 0, 0)),  # type: ignore[arg-type]
        hidden_exits=case.get("hidden_exits", (0,)),  # type: ignore[arg-type]
        hidden_error=case.get("hidden_error"),  # type: ignore[arg-type]
    )
    return evaluate_run(item, number, settings)


EXPECTED = {
    1: ("succeeded", None, HiddenOutcome.PASSED, 1),
    2: ("succeeded", None, HiddenOutcome.FAILED, 1),
    3: ("succeeded", None, HiddenOutcome.PASSED, 2),
    4: ("failed", "PROPOSAL_INVALID", HiddenOutcome.NOT_RUN, 1),
    5: ("failed", "REVIEW_OUTPUT_INVALID", HiddenOutcome.PASSED, 1),
    6: ("failed", "CHECKS_FAILED", HiddenOutcome.PASSED, 1),
    7: ("succeeded", None, HiddenOutcome.ERROR, 1),
}


@pytest.mark.parametrize("number", sorted(EXPECTED))
def test_scenario_outcomes(tmp_path: Path, number: int) -> None:
    run = scenario(tmp_path, number)
    disposition, failure, hidden, attempts = EXPECTED[number]
    result = run.task_result
    assert result.disposition.value == disposition
    assert (result.failure.name if result.failure else None) == failure
    assert run.hidden.outcome is hidden
    assert len(result.evidence.attempts) == attempts
    assert run.run_seconds >= 0 and run.hidden_seconds >= 0
    if number == 4:
        assert run.hidden.error == "no change applied"
    if number == 7:
        assert run.hidden.error == "unavailable"


def test_exact_aggregate_metrics(tmp_path: Path) -> None:
    item = fixture(STOCK)
    single = FixtureSet("forgeai-lq1", "1", "1", (item,))
    runs = tuple(scenario(tmp_path, number) for number in sorted(EXPECTED))
    report = build_report(metadata(single, 7), single, runs, 1.0)
    metrics = report["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["runs"] == 7
    completion = metrics["completion"]
    assert (completion["succeeded"], completion["rejected"], completion["failed"]) == (
        4,
        0,
        3,
    )
    hidden = metrics["hidden"]
    assert hidden["outcomes"] == {"error": 1, "failed": 1, "not_run": 1, "passed": 4}
    assert hidden["hidden_pass_rate"]["numerator"] == 4
    assert hidden["hidden_pass_rate"]["denominator"] == 7
    assert hidden["succeeded_and_hidden_pass_rate"]["numerator"] == 2
    assert hidden["succeeded_but_hidden_fail_rate"] == {
        "numerator": 1,
        "denominator": 4,
        "value": 0.25,
    }
    output = metrics["structured_output"]
    assert output["coding_output_invalid_rate"]["numerator"] == 1
    assert output["coding_output_invalid_rate"]["denominator"] == 8
    assert output["review_output_invalid_rate"]["numerator"] == 1
    assert output["review_output_invalid_rate"]["denominator"] == 6
    assert metrics["checks_attempt_1"]["mypy"] == {
        "failed": 1,
        "not_run": 1,
        "passed": 5,
    }
    assert metrics["checks_attempt_1"]["pytest"] == {"not_run": 1, "passed": 6}
    assert metrics["checks_attempt_2"] == {
        "mypy": {"passed": 1},
        "pytest": {"passed": 1},
        "ruff_check": {"passed": 1},
    }
    assert metrics["review_1"] == {
        "accept": 3,
        "changes_required": 1,
        "not_completed:output_invalid": 1,
        "not_run": 2,
    }
    assert metrics["review_2"] == {"accept": 1}
    rework = metrics["rework"]
    assert rework["rework_invocation_rate"]["numerator"] == 1
    assert rework["rework_recovery_rate"] == {
        "numerator": 1,
        "denominator": 1,
        "value": 1.0,
    }
    execution = metrics["execution"]
    assert execution["model_invocations"]["total"] == 14.0
    assert execution["model_invocations"]["min"] == 1.0
    assert execution["model_invocations"]["max"] == 4.0
    assert execution["task_failures"] == {
        "CHECKS_FAILED": 1,
        "PROPOSAL_INVALID": 1,
        "REVIEW_OUTPUT_INVALID": 1,
    }
    assert execution["per_model_call_latency"]["status"] == "unavailable"
    assert execution["unknown_model_effects"] == 0
    signals = metrics["m8_4_signals"]
    assert signals["testing_findings"] == 1  # review #1 in the rework scenario
    assert signals["hidden_fail_without_testing_blocker"] == 1


def test_reviewer_vs_hidden_matrix(tmp_path: Path) -> None:
    """MODEL-JUDGE MEASUREMENT: final review x hidden outcome."""
    item = fixture(STOCK)
    single = FixtureSet("forgeai-lq1", "1", "1", (item,))
    runs = tuple(scenario(tmp_path, number) for number in sorted(EXPECTED))
    metrics = build_report(metadata(single, 7), single, runs, 1.0)["metrics"]
    assert isinstance(metrics, dict)
    judge = metrics["judge_vs_hidden"]
    assert judge["label"] == "MODEL-JUDGE MEASUREMENT"
    assert judge["matrix"] == {
        "accept": {"error": 1, "failed": 1, "passed": 2},
        "not_completed:output_invalid": {"passed": 1},
    }
    assert judge["accept_but_hidden_fail"] == 1
    assert judge["accept_and_hidden_pass"] == 2
    assert judge["changes_required_and_hidden_pass"] == 0
    assert judge["insufficient_evidence"] == 0
