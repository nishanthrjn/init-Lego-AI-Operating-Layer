"""LQ1.4 closed required-key omissions, never arbitrary model keys."""

import json
from pathlib import Path

import pytest
from diag_support import observed_settings, part, targets_of
from eval_support import fixture, metadata, reference
from forgeai_support import REVIEW_CHANGES
from test_lq1_observer import Reply, Upstream, ollama, projection, run

from forgeai_eval.diagnostics import fold, run_diagnostics
from forgeai_eval.fixtures import FixtureSet
from forgeai_eval.observer import ChatObserver, ObservationLog
from forgeai_eval.outputs import REQUIRED_CHANGE_FIELDS, classify_coding
from forgeai_eval.report import build_report, render_markdown, write_report
from forgeai_eval.runner import evaluate_run

UNEXPECTED = ("explanation", "filename", "patch", "bogus_secret_field")


def omitted(
    keys: tuple[str, ...],
    index: int = 0,
    extra: bool = False,
    fixture_id: str = "stock-validation",
) -> str:
    value = json.loads(reference(fixture(fixture_id)))
    change = value["changes"][index]
    for key in keys:
        del change[key]
    if extra:
        change.update(dict.fromkeys(UNEXPECTED, "lq14-private-value"))
    # Reverse insertion order to prove diagnostics use the contract order.
    value["changes"][index] = dict(reversed(list(change.items())))
    return json.dumps(value)


def test_closed_vocabulary() -> None:
    assert REQUIRED_CHANGE_FIELDS == ("path", "operation", "content", "reason")
    targets = targets_of("stock-validation")
    for output in (reference(fixture("stock-validation")), "not json", "{}"):
        assert classify_coding(output, targets).features.missing_required_fields is None
    # Exact-key failure with extra fields only is known to omit no required keys.
    assert (
        classify_coding(
            omitted((), extra=True), targets
        ).features.missing_required_fields
        == ()
    )


@pytest.mark.parametrize("key", ["path", "operation", "content", "reason"])
@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("fixture_id", ["stock-validation", "text-slug"])
def test_missing_field(tmp_path: Path, key: str, index: int, fixture_id: str) -> None:
    settings, _ = observed_settings(
        tmp_path, (omitted((key,), index, fixture_id=fixture_id),)
    )
    found = evaluate_run(fixture(fixture_id), 1, settings)
    (entry,) = part(run_diagnostics(found), "coding")
    assert entry["category"] == "change_fields_invalid"
    assert entry["output_status"] == "output_invalid"
    assert entry["features"]["missing_required_fields"] == (key,)
    assert entry["features"]["change_entry_index"] == index
    assert entry["features"]["missing_required_field_count"] == 1


def test_multiple_missing(tmp_path: Path) -> None:
    settings, _ = observed_settings(tmp_path, (omitted(("reason", "path")),))
    (entry,) = part(
        run_diagnostics(evaluate_run(fixture("stock-validation"), 1, settings)),
        "coding",
    )
    assert entry["category"] == "change_fields_invalid"
    assert entry["features"]["missing_required_fields"] == ("path", "reason")
    assert entry["features"]["missing_required_field_count"] == 2


def test_first_failure(tmp_path: Path) -> None:
    value = json.loads(omitted(("reason",)))
    del value["changes"][1]["path"]
    settings, _ = observed_settings(tmp_path / "first", (json.dumps(value),))
    (entry,) = part(
        run_diagnostics(evaluate_run(fixture("stock-validation"), 1, settings)),
        "coding",
    )
    assert entry["features"]["missing_required_fields"] == ("reason",)
    assert entry["features"]["change_entry_index"] == 0
    # Earlier value validation prevents reporting later missing keys.
    value = json.loads(omitted(("reason",), index=1))
    value["changes"][0]["operation"] = 7
    settings, _ = observed_settings(tmp_path / "earlier", (json.dumps(value),))
    (entry,) = part(
        run_diagnostics(evaluate_run(fixture("stock-validation"), 1, settings)),
        "coding",
    )
    assert entry["category"] == "operation_invalid"
    assert entry["features"]["missing_required_fields"] is None


def test_rework_fold_report_privacy(tmp_path: Path) -> None:
    item = fixture("stock-validation")
    bad = omitted(("reason", "path"), extra=True)
    settings, _ = observed_settings(
        tmp_path / "run", (reference(item), REVIEW_CHANGES, bad)
    )
    result = evaluate_run(item, 1, settings)
    fixtures = FixtureSet("forgeai-lq1", "1", "1", (item,))
    report = build_report(metadata(fixtures, 1), fixtures, (result,), 1.0)
    jp, mp = write_report(report, tmp_path / "out")
    document = json.loads(jp.read_text(encoding="utf-8"))
    markdown = mp.read_text(encoding="utf-8")
    assert markdown == render_markdown(document)
    assert document["schema"] == "forgeai-lq1-report/3"
    entries = document["runs"][0]["diagnostics"]["coding"]
    assert entries[0]["features"]["missing_required_fields"] is None
    assert entries[1]["attempt"] == 2
    assert entries[1]["category"] == "change_fields_invalid"
    assert entries[1]["features"]["missing_required_fields"] == ["path", "reason"]
    assert entries[1]["features"]["unexpected_field_count"] == 4
    assert document["diagnostics"] == fold(document["runs"])
    counts = document["diagnostics"]["coding_output"]
    assert counts["missing_required_field_counts"] == {"path": 1, "reason": 1}
    assert counts["per_fixture_missing_required_field_counts"] == {
        "stock-validation": {"path": 1, "reason": 1}
    }
    assert "| path, reason |" in markdown
    text = jp.read_text(encoding="utf-8") + markdown
    for secret in (
        *UNEXPECTED,
        "lq14-private-value",
        bad,
        "def reserve",
        item.task.objective,
        "lq1-hidden-acceptance",
        str(tmp_path),
        tmp_path.as_posix(),
    ):
        assert secret not in text
    # Old records lack names: no backfill from a count of two.
    del entries[1]["features"]["missing_required_fields"]
    legacy = fold(document["runs"])["coding_output"]
    assert isinstance(legacy, dict)
    assert legacy["missing_required_field_counts"] == {}
    assert "| unavailable |" in render_markdown(document)


@pytest.mark.parametrize(
    "keys", [("path",), ("operation",), ("content",), ("reason",), ("reason", "path")]
)
def test_noninterference(tmp_path: Path, keys: tuple[str, ...]) -> None:
    replies = [
        Reply(reference(fixture("stock-validation"))),
        Reply(REVIEW_CHANGES),
        Reply(omitted(keys, extra=True)),
    ]
    direct = Upstream(list(replies))
    with ollama(direct) as url:
        plain = run(tmp_path / "direct", url, 30.0, None)
    observed = Upstream(list(replies))
    log = ObservationLog()
    with ollama(observed) as url, ChatObserver(url, 30.5, log) as observer:
        watched = run(tmp_path / "observed", observer.url, 30.0, log)
    assert projection(plain.task_result) == projection(watched.task_result)
    assert direct.bodies == observed.bodies
    assert plain.hidden == watched.hidden
    assert [a.applied for a in plain.task_result.evidence.attempts] == [
        a.applied for a in watched.task_result.evidence.attempts
    ]
    entry = part(run_diagnostics(watched), "coding")[-1]
    assert entry["attempt"] == 2
    assert entry["category"] == "change_fields_invalid"
    assert entry["features"]["missing_required_fields"] == tuple(
        k for k in REQUIRED_CHANGE_FIELDS if k in keys
    )
