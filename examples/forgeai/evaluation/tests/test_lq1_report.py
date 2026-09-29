"""Report completeness (fail closed), JSON/Markdown consistency, no raw content."""

import json
from pathlib import Path

import pytest
from eval_support import (
    REVIEW_ACCEPT,
    SENTINEL,
    fixture,
    metadata,
    reference,
    replay_settings,
)

from forgeai_eval.fixtures import FixtureSet
from forgeai_eval.report import ReportError, build_report, render_markdown, write_report
from forgeai_eval.runner import FixtureRun, evaluate_run


def one_run(tmp_path: Path) -> tuple[FixtureSet, tuple[FixtureRun, ...]]:
    item = fixture("pager-boundaries")
    settings, _, _, _ = replay_settings(tmp_path, (reference(item), REVIEW_ACCEPT))
    single = FixtureSet("forgeai-lq1", "1", "1", (item,))
    return single, (evaluate_run(item, 1, settings),)


@pytest.mark.parametrize(
    "change",
    [
        {"model_digest": ""},
        {"model_name": "  "},
        {"forgeai_commit": ""},
        {"fixture_revision": ""},
        {"hidden_revision": ""},
        {"ollama_version": ""},
        {"hardware_class": ""},
        {"repetitions": 0},
    ],
    ids=lambda c: next(iter(c)),
)
def test_missing_metadata_fails_closed(
    tmp_path: Path, change: dict[str, object]
) -> None:
    single, runs = one_run(tmp_path)
    with pytest.raises(ReportError):
        repetitions = change.pop("repetitions", 1)
        build_report(metadata(single, repetitions, **change), single, runs, 1.0)  # type: ignore[arg-type]
    assert not (tmp_path / "out").exists()


def test_revision_and_coverage_mismatch_fail_closed(tmp_path: Path) -> None:
    single, runs = one_run(tmp_path)
    with pytest.raises(ReportError):
        build_report(
            metadata(single, 1, hidden_digest="sha256:other"), single, runs, 1.0
        )
    with pytest.raises(ReportError):
        build_report(metadata(single, 2), single, runs, 1.0)  # N=2 but one run


def test_markdown_renders_the_written_json_exactly(tmp_path: Path) -> None:
    single, runs = one_run(tmp_path)
    report = build_report(metadata(single, 1), single, runs, 2.5)
    json_path, markdown_path = write_report(report, tmp_path / "out")
    written = json.loads(json_path.read_text(encoding="utf-8"))
    assert written == json.loads(json.dumps(report))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert markdown == render_markdown(written)
    for required in (
        "THIS IS NOT A PRODUCTION BENCHMARK",
        "MODEL-JUDGE MEASUREMENT",
        "| repetitions (N) | 1 |",
        "## Reviewer vs hidden tests",
        "## Per-fixture results",
        "## Limitations",
        "per_model_call_latency",
        "unavailable",
    ):
        assert required in markdown, required
    # Deterministic field order: rebuilding gives the same serialization.
    again = build_report(metadata(single, 1), single, runs, 2.5)
    assert json.dumps(again) == json.dumps(report)


def test_report_carries_no_source_prompts_or_hidden_tests(tmp_path: Path) -> None:
    single, runs = one_run(tmp_path)
    text = json.dumps(build_report(metadata(single, 1), single, runs, 1.0))
    for forbidden in (
        SENTINEL,
        "def page",
        "return items",
        "test_hidden_",
        str(tmp_path),
        "Page slicing",
    ):
        assert forbidden not in text, forbidden


def test_unavailable_metrics_are_explicit(tmp_path: Path) -> None:
    single, runs = one_run(tmp_path)
    report = build_report(metadata(single, 1), single, runs, 1.0)
    metrics = report["metrics"]
    assert isinstance(metrics, dict)
    recovery = metrics["rework"]["rework_recovery_rate"]
    assert recovery == {
        "numerator": 0,
        "denominator": 0,
        "value": None,
        "note": "no eligible runs",
    }
    assert metrics["checks_attempt_2"] == {}
    assert metrics["execution"]["per_model_call_latency"]["status"] == "unavailable"
