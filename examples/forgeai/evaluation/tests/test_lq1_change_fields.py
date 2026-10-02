"""LQ1.3 exact-key diagnostics through the real CodingAgent and observer."""

import json
from pathlib import Path

import pytest
from diag_support import observed_settings, part, targets_of
from eval_support import REVIEW_ACCEPT, fixture, metadata, reference
from forgeai_support import REVIEW_CHANGES
from test_lq1_observer import Reply, Upstream, ollama, projection, run

from forgeai_eval.diagnostics import fold, run_diagnostics
from forgeai_eval.fixtures import FixtureSet
from forgeai_eval.observer import ChatObserver, ObservationLog
from forgeai_eval.outputs import ChangeFieldFailure, classify_coding
from forgeai_eval.report import build_report, write_report
from forgeai_eval.runner import evaluate_run

SENTINEL = "lq13-arbitrary-key-private-content"


def reply(kind: str, fixture_id: str = "stock-validation", index: int = 0) -> str:
    value = json.loads(reference(fixture(fixture_id)))
    change = value["changes"][index]
    if kind in {"missing_only", "missing_and_unexpected"}:
        del change["reason"]
    if kind in {"unexpected_only", "missing_and_unexpected"}:
        change[SENTINEL] = SENTINEL
    return json.dumps(value)


def test_taxonomy() -> None:
    assert {x.value for x in ChangeFieldFailure} == {
        "missing_only",
        "unexpected_only",
        "missing_and_unexpected",
    }


@pytest.mark.parametrize("fixture_id", ["stock-validation", "text-slug"])
@pytest.mark.parametrize(
    "kind", ["valid", "missing_only", "unexpected_only", "missing_and_unexpected"]
)
@pytest.mark.parametrize("index", [0, 1])
def test_change_fields(tmp_path: Path, fixture_id: str, kind: str, index: int) -> None:
    output = reply(kind, fixture_id, index)
    settings, _ = observed_settings(tmp_path, (output, REVIEW_ACCEPT))
    found = evaluate_run(fixture(fixture_id), 1, settings)
    (entry,) = part(run_diagnostics(found), "coding")
    assert entry["category"] == (
        "valid" if kind == "valid" else "change_fields_invalid"
    )
    assert entry["output_status"] == (
        "succeeded" if kind == "valid" else "output_invalid"
    )
    features = entry["features"]
    assert features["missing_fields"] == features["unexpected_fields"] == 0
    if kind == "valid":
        assert features["change_field_failure"] is None
        assert features["change_entry_index"] is None
    else:
        missing = int(kind != "unexpected_only")
        unexpected = int(kind != "missing_only")
        assert features["change_field_failure"] == kind
        assert features["change_entry_index"] == index
        assert features["missing_required_field_count"] == missing
        assert features["unexpected_field_count"] == unexpected
        assert features["expected_field_count"] == 4
        assert features["actual_field_count"] == 4 - missing + unexpected
        assert all(
            a.proposal is None and not a.checks and a.review is None
            for a in found.task_result.evidence.attempts
        )


def test_first_failure(tmp_path: Path) -> None:
    # An earlier path/type failure wins over a later key-set mismatch.
    value = json.loads(reply("missing_only", index=1))
    value["changes"][0]["path"] = 7
    settings, _ = observed_settings(tmp_path / "earlier", (json.dumps(value),))
    (entry,) = part(
        run_diagnostics(evaluate_run(fixture("stock-validation"), 1, settings)),
        "coding",
    )
    assert entry["category"] == "path_invalid"
    assert entry["features"]["change_entry_index"] is None
    # Multiple invalid entries: retain only the first key rejection.
    value = json.loads(reply("missing_only"))
    value["changes"][1][SENTINEL] = 1
    settings, _ = observed_settings(tmp_path / "multiple", (json.dumps(value),))
    (entry,) = part(
        run_diagnostics(evaluate_run(fixture("stock-validation"), 1, settings)),
        "coding",
    )
    assert entry["features"]["change_field_failure"] == "missing_only"
    assert entry["features"]["change_entry_index"] == 0
    # Value types and non-objects must not masquerade as field-set failures.
    for field, category in [
        ("path", "path_invalid"),
        ("operation", "operation_invalid"),
        ("content", "content_invalid"),
        ("reason", "reason_invalid"),
    ]:
        value = json.loads(reply("valid"))
        value["changes"][0][field] = 7
        diagnosis = classify_coding(json.dumps(value), targets_of("stock-validation"))
        assert diagnosis.category == category
        assert diagnosis.features.change_field_failure is None


def test_rework_aggregate_privacy(tmp_path: Path) -> None:
    item = fixture("stock-validation")
    outputs = (reference(item), REVIEW_CHANGES, reply("missing_and_unexpected"))
    settings, _ = observed_settings(tmp_path / "run", outputs)
    found = evaluate_run(item, 1, settings)
    single = FixtureSet("forgeai-lq1", "1", "1", (item,))
    report = build_report(metadata(single, 1), single, (found,), 1.0)
    json_path, md_path = write_report(report, tmp_path / "report")
    document = json.loads(json_path.read_text(encoding="utf-8"))
    entries = document["runs"][0]["diagnostics"]["coding"]
    assert [(e["attempt"], e["category"]) for e in entries] == [
        (1, "valid"),
        (2, "change_fields_invalid"),
    ]
    assert entries[1]["features"]["change_field_failure"] == "missing_and_unexpected"
    assert document["diagnostics"] == fold(document["runs"])
    coding = document["diagnostics"]["coding_output"]
    assert coding["change_field_failures"] == {"missing_and_unexpected": 1}
    assert coding["per_fixture_change_field_failures"] == {
        "stock-validation": {"missing_and_unexpected": 1}
    }
    text = json_path.read_text(encoding="utf-8") + md_path.read_text(encoding="utf-8")
    for forbidden in [
        SENTINEL,
        outputs[2],
        "def reserve",
        item.task.objective,
        "lq1-hidden-acceptance",
        str(tmp_path),
        tmp_path.as_posix(),
        "Line too long",
        "E       assert",
    ]:
        assert forbidden not in text
    assert (
        "| stock-validation | 1 | 2 | 0 | missing_and_unexpected | 1 | 1 | 4 | 4 |"
        in text
    )
    # Additive compatibility: an older schema-3 invocation has no details.
    for entry in entries:
        entry["features"].pop("change_field_failure")
    legacy_coding = fold(document["runs"])["coding_output"]
    assert isinstance(legacy_coding, dict)
    assert legacy_coding["change_field_failures"] == {"other": 1}


@pytest.mark.parametrize(
    "kind", ["missing_only", "unexpected_only", "missing_and_unexpected", "rework"]
)
def test_noninterference(tmp_path: Path, kind: str) -> None:
    bad = Reply(reply("missing_and_unexpected" if kind == "rework" else kind))
    replies = (
        [Reply(reference(fixture("stock-validation"))), Reply(REVIEW_CHANGES), bad]
        if kind == "rework"
        else [bad]
    )
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
    entries = part(run_diagnostics(watched), "coding")
    assert entries[-1]["category"] == "change_fields_invalid"
    assert entries[-1]["attempt"] == (2 if kind == "rework" else 1)
