"""ANALYST-CONTRACT-DIAG-1 qualification. No live model is contacted.

Replay replies run through the real host, evidence reader and unchanged
RepositoryAnalyst, so every diagnosed stage is checked against the Analyst's
own verdict and against CONTENT-DISCOVERY-1Q's coarse category.
"""

import json
from pathlib import Path

import pytest
from analyst_contract_diag1 import cli, report
from analyst_contract_diag1.diagnose import (
    COARSE,
    CONTRACT,
    Stage,
    diagnose,
    representation,
)
from analyst_contract_diag1.runner import run_call
from analyst_quality1q import cli as cq
from analyst_quality1q import data
from analyst_quality1q.classify import Category
from forgeai.cli import ReplayModel, replay_binding
from forgeai_eval.preflight import PreflightError, PreflightFailure
from legoai_engineering.analyst.api import repository_analyst_definition

CASE = {c.id: c for c in data.load_heldout()}["q23"]  # fx/convert.py, fx/rates.py
SENTINEL = "diag-sentinel-must-not-leak"
ROOT = Path(__file__).resolve().parents[4]


def body(*, drop: tuple[str, ...] = (), **fields: object) -> dict[str, object]:
    value: dict[str, object] = {
        "status": "succeeded",
        "summary": "Synthetic replay for diagnostic qualification.",
        "relevant_files": ["fx/convert.py"],
        "findings": [],
        "risks": [],
        "unknowns": [],
    }
    value.update(fields)
    for name in drop:
        del value[name]
    return value


def reply(**kwargs: object) -> str:
    return json.dumps(body(**kwargs))  # type: ignore[arg-type]


def live_stage(output: str) -> dict[str, object]:
    return run_call(CASE, 1, replay_binding(ReplayModel(output)))


# Taxonomy and contract ------------------------------------------------------


def test_taxonomy_is_closed_and_refines_the_1q_categories() -> None:
    assert set(COARSE) == set(Stage)
    assert set(COARSE.values()) <= {c.value for c in Category}


def test_contract_matches_the_unchanged_analyst() -> None:
    assert data.definition_fingerprint() == (
        "924bdaac617c51341b56d27bb3aef53a7e37dd358d85e37f43bdf4e5c9a659b7"
    )
    prompt = repository_analyst_definition().system_prompt
    positions = [prompt.index(name) for name in CONTRACT]
    assert positions == sorted(positions)  # canonical order is the prompt order
    record = live_stage(reply())
    assert record["stage"] == "valid" and record["runtime_status"] == "succeeded"


# First-failure ordering, agreeing with the real Analyst ----------------------

FENCE = "```"
CASES = {
    "valid": (reply(), "valid"),
    "prose": ("The convert module is relevant.", "response_not_json"),
    "fence-other-label": (
        FENCE + "python\n" + reply() + "\n" + FENCE,
        "response_not_json",
    ),
    "fenced-json-valid": (FENCE + "json\n" + reply() + "\n" + FENCE, "valid"),
    "fenced-unlabelled-valid": (FENCE + "\n" + reply() + "\n" + FENCE, "valid"),
    "duplicate-key": ('{"status":"succeeded",' + reply()[1:], "duplicate_key"),
    "top-level-array": (json.dumps([body()]), "top_level_not_object"),
    "missing-risks": (reply(drop=("risks",)), "field_set_invalid"),
    "field-set-before-summary": (
        reply(drop=("risks",), summary=5, extra=1),
        "field_set_invalid",
    ),
    "extra-field-only": (reply(evidence=[]), "field_set_invalid"),
    "status-value": (reply(status="done"), "status_invalid"),
    "status-type": (reply(status=1), "status_invalid"),
    "findings-shape": (reply(findings="none"), "findings_shape_invalid"),
    "finding-entry": (reply(findings=[{"text": "t"}]), "finding_entry_invalid"),
    "findings-before-summary": (
        reply(findings=[{"text": "t"}], summary=5),
        "finding_entry_invalid",
    ),
    "summary-type": (reply(summary=5), "summary_type_invalid"),
    "summary-before-risks": (reply(summary=5, risks="x"), "summary_type_invalid"),
    "relevant-files-shape": (
        reply(relevant_files="fx/convert.py"),
        "relevant_files_shape_invalid",
    ),
    "risks-shape": (reply(risks="none"), "risks_shape_invalid"),
    "risks-before-unknowns": (reply(risks="none", unknowns=3), "risks_shape_invalid"),
    "unknowns-shape": (reply(unknowns={}), "unknowns_shape_invalid"),
    "summary-bounds": (reply(summary=" "), "summary_bounds_invalid"),
    "relevant-duplicate": (
        reply(relevant_files=["fx/convert.py", "FX/CONVERT.PY"]),
        "relevant_files_duplicate",
    ),
    "narrative-bounds": (reply(risks=[""]), "narrative_bounds_invalid"),
    "insufficient-inconsistent": (
        reply(status="insufficient_evidence"),
        "insufficient_inconsistent",
    ),
    "membership": (reply(relevant_files=["config/secrets.py"]), "membership_invalid"),
    "blank": ("   ", "output_contract_invalid"),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_first_failure_stage_agrees_with_the_analyst(name: str) -> None:
    output, expected = CASES[name]
    record = live_stage(output)
    assert record["stage"] == expected  # never classifier_disagreement
    assert record["coarse_consistent"] is True


def test_every_parser_stage_is_exercised() -> None:
    exercised = {stage for _, stage in CASES.values()}
    unreachable_here = {"model_failure", "classifier_disagreement"}
    assert exercised == {s.value for s in Stage} - unreachable_here


# Field-set diagnostics ------------------------------------------------------


def test_field_set_diagnostics_and_canonical_missing_order() -> None:
    shuffled = json.dumps({"findings": [], "relevant_files": [], "summary": "s"})
    d = diagnose(shuffled, CASE.supplied)
    assert d.stage is Stage.FIELD_SET_INVALID
    assert d.expected_field_count == 6 and d.actual_field_count == 3
    assert d.missing_required_fields == ("status", "risks", "unknowns")
    assert d.unexpected_field_count == 0


def test_unexpected_field_names_are_never_retained() -> None:
    output = reply(**{SENTINEL: 1, SENTINEL + "-2": [SENTINEL]})
    record = live_stage(output)
    assert record["stage"] == "field_set_invalid"
    assert record["unexpected_field_count"] == 2
    assert record["missing_required_fields"] == []
    assert SENTINEL not in json.dumps(record)


def test_required_field_types_are_closed() -> None:
    d = diagnose(
        reply(drop=("unknowns",), risks={}, summary=None, findings=True, status=7),
        CASE.supplied,
    )
    assert d.field_types == {
        "status": "number",
        "summary": "null",
        "relevant_files": "array",
        "findings": "boolean",
        "risks": "object",
        "unknowns": "missing",
    }
    assert d.status_value == "non_string"
    assert (
        diagnose(reply(status="done", extra=1), CASE.supplied).status_value == "other"
    )


def test_representation_classification() -> None:
    assert representation(reply())[1] == "raw"
    assert representation(FENCE + "json\n{}\n" + FENCE)[1] == "fenced_json"
    assert representation(FENCE + "\n{}\n" + FENCE)[1] == "fenced_unlabelled"
    assert representation(FENCE + "JSON\n{}\n" + FENCE)[1] == "other"
    assert representation("Here:\n" + FENCE + "json\n{}\n" + FENCE)[1] == "raw"


# Report: linkage, privacy, folding, rendering, pattern ----------------------


@pytest.fixture(scope="module")
def replay_report(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    output = tmp_path_factory.mktemp("diag") / "replay"
    leaking = json.dumps(
        {
            "status": "succeeded",
            "summary": SENTINEL,
            "relevant_files": [],
            "findings": [],
            "unknowns": [SENTINEL],
            SENTINEL: SENTINEL,
        }
    )
    assert (
        cli.main(["replay", "--output", str(output), "--replay-output", leaking]) == 0
    )
    loaded: dict[str, object] = json.loads((output / "report.json").read_text("utf-8"))
    loaded["_md"] = (output / "report.md").read_text("utf-8")
    loaded["_condition"] = (output / "condition.json").read_text("utf-8")
    loaded["_dir"] = str(output)
    return loaded


def test_condition_links_the_frozen_1q_identity(
    replay_report: dict[str, object],
) -> None:
    condition = replay_report["condition"]
    assert isinstance(condition, dict)
    assert condition["schema"] == report.CONDITION_SCHEMA
    assert condition["linkage"] == report.LINKAGE
    assert condition["fixtures"] == data.freeze()
    assert condition["plan"]["total_calls"] == 91
    recorded = (
        ROOT / "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY.md"
    ).read_text("utf-8")
    assert report.LINKAGE["cq_report_sha256"] in recorded
    assert report.LINKAGE["cq_commit"] in recorded


def test_report_privacy(replay_report: dict[str, object]) -> None:
    text = json.dumps({k: v for k, v in replay_report.items() if k != "_dir"})
    for leaked in (
        SENTINEL,
        CASE.question,
        "ignore previous instructions",
        "RATES",
        str(Path.home()),
        str(replay_report["_dir"]),
    ):
        assert leaked not in text, leaked
    records = replay_report["records"]
    assert isinstance(records, list) and len(records) == 91
    assert {r["stage"] for r in records} == {"field_set_invalid"}
    assert {r["unexpected_field_count"] for r in records} == {1}
    assert {tuple(r["missing_required_fields"]) for r in records} == {("risks",)}


def test_aggregate_folding_and_rendering(
    replay_report: dict[str, object], tmp_path: Path
) -> None:
    records = replay_report["records"]
    assert isinstance(records, list)
    folded = report.fold(records)
    aggregate = replay_report["aggregate"]
    assert isinstance(aggregate, dict)
    assert {k: v for k, v in aggregate.items() if k != "pattern"} == {
        k: v for k, v in folded.items() if k != "pattern"
    }
    assert folded["pattern"]["code"] == "A"  # type: ignore[index]
    assert aggregate["pattern"]["label"] == "REPLAY ONLY - not live evidence"
    clean = {k: v for k, v in replay_report.items() if not k.startswith("_")}
    assert report.render(clean) == replay_report["_md"]
    with pytest.raises(FileExistsError):
        report.write(clean, Path(str(replay_report["_dir"])))


def record(
    stage: str, missing: tuple[str, ...] = (), extra: int = 0
) -> dict[str, object]:
    return {
        "stage": stage,
        "partition": "heldout",
        "case": "q",
        "missing_required_fields": list(missing),
        "unexpected_field_count": extra,
    }


@pytest.mark.parametrize(
    ("records", "code"),
    [
        (
            [record("field_set_invalid", ("risks",))] * 9
            + [record("summary_type_invalid")],
            "A",
        ),
        (
            [record("field_set_invalid", ("risks",))] * 5
            + [record("field_set_invalid", ("unknowns",))] * 5,
            "B",
        ),
        (
            [record("field_set_invalid", (), 2)] * 6
            + [record("field_set_invalid", ("risks",))] * 4,
            "C",
        ),
        (
            [record("risks_shape_invalid")] * 6
            + [record("field_set_invalid", ("risks",))] * 4,
            "D",
        ),
        (
            [record("response_not_json")] * 6
            + [record("field_set_invalid", ("risks",))] * 4,
            "E",
        ),
        (
            [record("response_not_json")] * 3
            + [record("field_set_invalid", ("risks",))] * 3
            + [record("risks_shape_invalid")] * 3
            + [record("membership_invalid")],
            "F",
        ),
    ],
)
def test_pattern_rule(records: list[dict[str, object]], code: str) -> None:
    assert report.pattern(records)["code"] == code


# Non-interference and preflight --------------------------------------------


def test_historical_1q_inputs_and_classifier_unchanged() -> None:
    data.freeze()  # 1Q frozen inputs, Analyst source and fingerprint
    from analyst_quality1q.classify import classify

    assert classify(reply(drop=("risks",)), CASE.supplied)[0] is Category.SCHEMA_INVALID


def test_live_preflight_refuses_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*args: object) -> object:
        raise PreflightError(PreflightFailure.OLLAMA_UNREACHABLE, "no")

    monkeypatch.setattr(cq, "git_state", lambda *a: {"head": "h"})
    monkeypatch.setattr(cli, "verify_ollama", refuse)
    output = tmp_path / "live"
    argv = ["live", "--output", str(output), "--model", "m", "--hardware", "h"]
    argv += ["--model-digest", "sha256:" + "a" * 64]
    argv += ["--expect-branch", "b", "--expect-commit", "c"]
    assert cli.main(argv) == 3
    assert not output.exists()
    existing = tmp_path / "exists"
    existing.mkdir()
    with pytest.raises(SystemExit):
        cli.main(["replay", "--output", str(existing)])
