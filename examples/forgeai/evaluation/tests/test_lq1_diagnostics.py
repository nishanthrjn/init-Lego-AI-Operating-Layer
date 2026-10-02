"""LQ1.2 report diagnostics: re-derivable aggregate, privacy, unchanged metrics."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
import run
from diag_support import (
    PYTEST_FAILED,
    RUFF_FAILED,
    SENTINEL,
    coding_samples,
    observed_settings,
    review_samples,
)
from eval_support import REVIEW_ACCEPT, fixture, metadata, reference
from forgeai_support import FakeSandbox, git_executable

from forgeai_eval.diagnostics import fold
from forgeai_eval.fixtures import FixtureSet
from forgeai_eval.report import SCHEMA, build_report, write_report
from forgeai_eval.runner import FixtureRun, RunSettings, evaluate, evaluate_run

STOCK = "stock-validation"
SCHEMA_1_METRICS = {
    "runs",
    "completion",
    "hidden",
    "structured_output",
    "checks_attempt_1",
    "checks_attempt_2",
    "review_1",
    "review_2",
    "judge_vs_hidden",
    "rework",
    "execution",
    "m8_4_signals",
}


def runs(tmp_path: Path) -> tuple[FixtureSet, tuple[FixtureRun, ...]]:
    item = fixture(STOCK)
    good = reference(item)
    coding = coding_samples()
    review = review_samples()
    failing = ((1, RUFF_FAILED), (0, ""), (1, PYTEST_FAILED))
    garbage = ((1, f"garbage {SENTINEL}"), (0, ""), (0, ""))
    cases = [
        ((good, REVIEW_ACCEPT), failing),
        ((coding["fenced-other-label"][0], REVIEW_ACCEPT), None),
        ((coding["prose"][0], REVIEW_ACCEPT), None),
        ((coding["path-outside-targets"][0], REVIEW_ACCEPT), None),
        ((good, review["fenced-other-label"][0]), None),
        ((good, REVIEW_ACCEPT), garbage),
    ]
    found = []
    for number, (outputs, script) in enumerate(cases, 1):
        settings, _ = observed_settings(tmp_path / str(number), outputs, script)
        found.append(evaluate_run(item, number, settings))
    return FixtureSet("forgeai-lq1", "1", "1", (item,)), tuple(found)


def written(tmp_path: Path) -> tuple[dict[str, object], str]:
    single, found = runs(tmp_path)
    report = build_report(metadata(single, len(found)), single, found, 1.0)
    json_path, markdown_path = write_report(report, tmp_path / "out")
    return (
        json.loads(json_path.read_text(encoding="utf-8")),
        markdown_path.read_text(encoding="utf-8"),
    )


def test_aggregate_is_the_fold_of_the_run_rows(tmp_path: Path) -> None:
    report, _ = written(tmp_path)
    rows = report["runs"]
    assert isinstance(rows, list)
    assert report["diagnostics"] == fold(rows)  # re-derived from the JSON alone
    diagnostics = report["diagnostics"]
    assert isinstance(diagnostics, dict)
    assert diagnostics["coding_output"] == {
        "counts_by_category": {
            "path_not_requested_target": 1,
            "response_not_json": 2,
            "valid": 3,
        },
        "per_fixture_counts": {
            STOCK: {"path_not_requested_target": 1, "response_not_json": 2, "valid": 3}
        },
        "markdown_fence_replies": 1,
        "representation_counts": {"none": 1, "raw": 5},
        "fence_label_counts": {"other": 1},
        "change_field_failures": {},
        "per_fixture_change_field_failures": {},
    }
    assert diagnostics["reviewer_output"]["counts_by_category"] == {
        "response_not_json": 1
    }
    assert diagnostics["ruff"] == {
        "failed_checks": 2,
        "unavailable": 1,
        "rule_counts": {"E501": 1, "F401": 1, "I001": 1, "invalid-syntax": 1},
        "per_fixture_rule_counts": {
            STOCK: {"E501": 1, "F401": 1, "I001": 1, "invalid-syntax": 1}
        },
    }
    assert diagnostics["pytest"]["kind_counts"] == {
        "assertion_failure": 1,
        "did_not_raise": 1,
        "exception_failure": 1,
        "setup_error": 1,
    }
    observation = diagnostics["observation"]
    assert observation["runs_observed"] == 6
    assert observation["classifier_disagreements"] == 0
    assert observation["anomalies"] == {}


def test_reports_carry_no_model_prompt_source_or_tool_content(tmp_path: Path) -> None:
    report, markdown = written(tmp_path)
    text = json.dumps(report) + markdown
    item = fixture(STOCK)
    forbidden = [
        SENTINEL,
        str(tmp_path),
        tmp_path.as_posix(),
        item.task.objective,
        "Stock reservation for a small inventory",  # generated code
        "def reserve",
        "```",
        "Line too long",
        "Import block",
        "E       assert",
        "test_raises",
        "Captured stdout",
        "lq1-hidden-acceptance",  # hidden-test sentinel
    ]
    for leaked in forbidden:
        assert leaked not in text, leaked


def test_schema_3_keeps_every_schema_1_metric(tmp_path: Path) -> None:
    report, markdown = written(tmp_path)
    assert SCHEMA == report["schema"] == "forgeai-lq1-report/3"
    metrics = report["metrics"]
    assert isinstance(metrics, dict)
    assert set(metrics) == SCHEMA_1_METRICS
    assert "## Failure diagnostics (LQ1.2)" in markdown


def test_replay_command_reports_valid_observed_replies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def offline(
        fixtures: FixtureSet, repetitions: int, settings: RunSettings
    ) -> tuple[tuple[FixtureRun, ...], float]:
        hidden = FakeSandbox()
        return evaluate(
            fixtures,
            repetitions,
            replace(
                settings, forgeai_sandbox=FakeSandbox(), hidden_sandbox=lambda: hidden
            ),
        )

    monkeypatch.setattr(run, "evaluate", offline)
    argv = ["replay", "--output", str(tmp_path / "out")]
    argv += ["--git", str(git_executable()), "--docker", str(git_executable())]
    assert run.main(argv) == 0
    report = json.loads((tmp_path / "out" / "report.json").read_text("utf-8"))
    diagnostics = report["diagnostics"]
    assert diagnostics["coding_output"]["counts_by_category"] == {"valid": 4}
    assert diagnostics["reviewer_output"]["counts_by_category"] == {"valid": 4}
    assert diagnostics["observation"]["anomalies"] == {}
