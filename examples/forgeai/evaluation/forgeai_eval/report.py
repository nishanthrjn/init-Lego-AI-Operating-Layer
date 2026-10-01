"""LQ1 reports: report.json is the evidence; report.md renders the same values.

`build_report` fails closed when required metadata is missing. The Markdown is
rendered only from the JSON dictionary, so it cannot compute different
numbers. Reports hold identifiers, enums, counts and timings: no source text,
prompts, model output, environment or host paths.

Schema 2 (LQ1.2) added a per-run `diagnostics` record and a top-level
`diagnostics` aggregate folded from those records; every schema-1 field is
unchanged. Schema 3 (ADR-021) changes the meaning of `response_not_json`
(an exact json-labelled or unlabelled fence is now decoded) and adds the
`representation` and `fence_label` features and their counts. Schema-1 and
schema-2 reports stay as recorded; the harness never reads them.
"""

import json
from dataclasses import asdict
from pathlib import Path

from legoai_engineering.checks.values import CheckKind

from forgeai_eval.diagnostics import DIAGNOSTIC_DEFINITIONS, fold, run_diagnostics
from forgeai_eval.fixtures import FixtureSet
from forgeai_eval.metrics import (
    DEFINITIONS,
    MODEL_JUDGE,
    RunSummary,
    aggregate,
    summarize_run,
)
from forgeai_eval.runner import FixtureRun, RunMetadata

SCHEMA = "forgeai-lq1-report/3"
LIMITATIONS = (
    "THIS IS NOT A PRODUCTION BENCHMARK. Results describe the frozen fixture set "
    "only, on the recorded model, hardware and revisions.",
    "Hidden acceptance tests are the independent oracle only for the behaviors "
    "they encode; passing them does not prove a change correct in general.",
    f"Reviewer-derived figures are a {MODEL_JUDGE}: the IndependentReviewer is "
    "itself model-based and its ACCEPT is not ground truth.",
    "Small N: rates are descriptive counts, not statistically calibrated "
    "estimates, and are not comparable across models or revisions.",
    "Per-model-call latency is unavailable in LQ1; timings are harness wall-clock.",
    "Replay-mode reports exercise the harness only and are not live-model evidence.",
    "Failure diagnostics name the first stage of the existing contract that "
    "rejected a reply or check; they are not a judgment of model intent. If "
    "Ollama refuses connections mid-run, the live observer turns a NONE model "
    "effect into UNKNOWN; such calls are counted as upstream_* transports.",
)


class ReportError(ValueError):
    """The report would be incomplete; nothing is written."""


def _row(summary: RunSummary) -> dict[str, object]:
    row = asdict(summary)
    row["coding"] = list(summary.coding)
    row["checks"] = [dict(attempt) for attempt in summary.checks]
    row["reviews"] = list(summary.reviews)
    row["review_invoked"] = list(summary.review_invoked)
    return row


def build_report(
    metadata: RunMetadata,
    fixtures: FixtureSet,
    runs: tuple[FixtureRun, ...],
    total_seconds: float,
) -> dict[str, object]:
    missing = metadata.missing()
    if missing:
        raise ReportError(f"required metadata missing: {', '.join(missing)}")
    if metadata.fixture_revision != fixtures.revision or (
        metadata.hidden_revision != fixtures.hidden_revision
    ):
        raise ReportError("metadata revisions do not match the evaluated fixture set")
    if metadata.fixture_digest != fixtures.fixture_digest or (
        metadata.hidden_digest != fixtures.hidden_digest
    ):
        raise ReportError("metadata digests do not match the evaluated fixture set")
    expected = {
        (fixture.fixture_id, repetition)
        for fixture in fixtures.fixtures
        for repetition in range(1, metadata.repetitions + 1)
    }
    if {(run.fixture_id, run.repetition) for run in runs} != expected or len(
        runs
    ) != len(expected):
        raise ReportError("runs do not cover every fixture x repetition exactly once")
    summaries = [summarize_run(run) for run in runs]
    rows = [
        {**_row(summary), "diagnostics": run_diagnostics(run)}
        for summary, run in zip(summaries, runs, strict=True)
    ]
    return {
        "schema": SCHEMA,
        "labels": {
            "model_judge": MODEL_JUDGE,
            "benchmark": "not a production benchmark",
        },
        "metadata": asdict(metadata),
        "fixture_set": {
            "name": fixtures.name,
            "revision": fixtures.revision,
            "hidden_revision": fixtures.hidden_revision,
            "fixtures": [
                {
                    "id": fixture.fixture_id,
                    "category": fixture.category,
                    "fixture_digest": fixture.fixture_digest,
                    "hidden_digest": fixture.hidden_digest,
                }
                for fixture in fixtures.fixtures
            ],
        },
        "repetitions": metadata.repetitions,
        "total_seconds": round(total_seconds, 3),
        "metrics": aggregate(summaries),
        "per_fixture": {
            fixture.fixture_id: aggregate(
                [s for s in summaries if s.fixture == fixture.fixture_id]
            )
            for fixture in fixtures.fixtures
        },
        "diagnostics": fold(rows),
        "runs": rows,
        "definitions": {**DEFINITIONS, **DIAGNOSTIC_DEFINITIONS},
        "limitations": list(LIMITATIONS),
    }


def _value(rate: object) -> str:
    if isinstance(rate, dict) and "numerator" in rate:
        value = rate["value"]
        shown = "unavailable" if value is None else f"{value:.2%}"
        return f"{shown} ({rate['numerator']}/{rate['denominator']})"
    return json.dumps(rate)


def _table(mapping: dict[str, object]) -> list[str]:
    lines = ["| Key | Value |", "| --- | --- |"]
    lines += [f"| {key} | {_value(value)} |" for key, value in mapping.items()]
    return lines


def render_markdown(report: dict[str, object]) -> str:
    """Render the JSON report dictionary; no metric is computed here."""
    metadata = report["metadata"]
    metrics = report["metrics"]
    fixture_set = report["fixture_set"]
    assert isinstance(metadata, dict) and isinstance(metrics, dict)
    assert isinstance(fixture_set, dict)
    lines = [
        "# ForgeAI-LQ1 evaluation report",
        "",
        "> **THIS IS NOT A PRODUCTION BENCHMARK.** Reviewer-derived figures are "
        f"labelled **{MODEL_JUDGE}**.",
        "",
        "## Evaluation identity",
        "",
        *_table({key: metadata[key] for key in metadata}),
        f"| repetitions (N) | {report['repetitions']} |",
        f"| total_seconds | {report['total_seconds']} |",
        "",
        "## Fixture set",
        "",
        f"`{fixture_set['name']}` revision {fixture_set['revision']}, hidden-test "
        f"revision {fixture_set['hidden_revision']}.",
        "",
        "| Fixture | Category | Fixture digest | Hidden digest |",
        "| --- | --- | --- | --- |",
    ]
    for item in fixture_set["fixtures"]:
        lines.append(
            f"| {item['id']} | {item['category']} | `{item['fixture_digest']}` | "
            f"`{item['hidden_digest']}` |"
        )
    sections = (
        ("Completion", "completion"),
        ("Independent correctness (hidden acceptance tests)", "hidden"),
        ("Structured model output", "structured_output"),
        ("Rework", "rework"),
        ("Execution", "execution"),
        (f"M8.4 signals ({MODEL_JUDGE})", "m8_4_signals"),
    )
    lines += ["", f"## Aggregate metrics (runs: {metrics['runs']})"]
    for title, key in sections:
        section = metrics[key]
        assert isinstance(section, dict)
        lines += ["", f"### {title}", "", *_table(section)]
    for title, key in (
        ("Checks, attempt 1", "checks_attempt_1"),
        ("Checks, attempt 2", "checks_attempt_2"),
        ("Review 1 decisions", "review_1"),
        ("Review 2 decisions", "review_2"),
    ):
        section = metrics[key]
        assert isinstance(section, dict)
        lines += ["", f"### {title}", "", *_table(section)]
    judge = metrics["judge_vs_hidden"]
    assert isinstance(judge, dict)
    lines += [
        "",
        f"## Reviewer vs hidden tests — {MODEL_JUDGE}",
        "",
        *_table({key: value for key, value in judge.items() if key != "label"}),
        "",
        "## Per-fixture results",
    ]
    per_fixture = report["per_fixture"]
    assert isinstance(per_fixture, dict)
    for fixture_id, values in per_fixture.items():
        assert isinstance(values, dict)
        completion = values["completion"]
        hidden = values["hidden"]
        assert isinstance(completion, dict) and isinstance(hidden, dict)
        lines += [
            "",
            f"### {fixture_id}",
            "",
            *_table(
                {
                    "runs": values["runs"],
                    "succeeded_rate": completion["succeeded_rate"],
                    "hidden_pass_rate": hidden["hidden_pass_rate"],
                    "succeeded_and_hidden_pass_rate": hidden[
                        "succeeded_and_hidden_pass_rate"
                    ],
                    "task_failures": values["execution"]["task_failures"],
                }
            ),
        ]
    lines += [
        "",
        "## Runs",
        "",
        "| Fixture | Rep | Disposition | Failure | Attempts | Reviews | Hidden | "
        "Model invocations | Run s | Coding diagnostics |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    runs = report["runs"]
    assert isinstance(runs, list)
    for run in runs:
        lines.append(
            f"| {run['fixture']} | {run['repetition']} | {run['disposition']} | "
            f"{run['failure'] or '—'} | {run['attempts']} | "
            f"{', '.join(run['reviews']) or '—'} | {run['hidden']} | "
            f"{run['model_invocations']} | {run['run_seconds']} | "
            f"{', '.join(e['category'] for e in run['diagnostics']['coding']) or '—'} |"
        )
    diagnostics = report["diagnostics"]
    assert isinstance(diagnostics, dict)
    lines += [
        "",
        "## Failure diagnostics (LQ1.2)",
        "",
        "Content-free categories of the existing contracts. Per ADR-021 one "
        "exact fence (label `json` or none) is decoded; any other fenced or "
        "prose reply is `response_not_json`. Diagnostics observe; they never "
        "change behavior.",
    ]
    for title, key in (
        ("Coding output", "coding_output"),
        ("Reviewer output", "reviewer_output"),
        ("Ruff rules (failed ruff_check runs)", "ruff"),
        ("pytest failure kinds (failed pytest runs)", CheckKind.PYTEST.value),
        ("Observation", "observation"),
    ):
        section = diagnostics[key]
        assert isinstance(section, dict)
        lines += ["", f"### {title}", "", *_table(section)]
    limitations = report["limitations"]
    definitions = report["definitions"]
    assert isinstance(limitations, list) and isinstance(definitions, dict)
    lines += ["", "## Metric definitions", ""]
    lines += [f"- **{key}**: {text}" for key, text in definitions.items()]
    lines += ["", "## Limitations", ""]
    lines += [f"- {text}" for text in limitations]
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, object], directory: Path) -> tuple[Path, Path]:
    """Write report.json, then report.md rendered from the written JSON."""
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "report.json"
    markdown_path = directory / "report.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    written = json.loads(json_path.read_text(encoding="utf-8"))
    markdown_path.write_text(render_markdown(written), encoding="utf-8")
    return json_path, markdown_path
