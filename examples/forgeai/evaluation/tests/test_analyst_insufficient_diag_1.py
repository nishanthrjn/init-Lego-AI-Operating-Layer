"""ANALYST-INSUFFICIENT-DIAG-1 qualification. No live model is contacted.

Replay replies run through the real host, evidence reader and RepositoryAnalyst
1.0.1, so every refined clause is checked against the Analyst's own verdict.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest
from analyst_contract_diag1.diagnose import Diagnosis, Stage
from analyst_insufficient_diag1 import cli, report
from analyst_insufficient_diag1.clauses import (
    Abstention,
    Refined,
    abstention,
    observe,
    refine,
)
from analyst_insufficient_diag1.runner import run_call
from analyst_quality1q import cli as cq
from analyst_quality1q import data as q
from analyst_quality1q_r2 import data as r2
from analyst_quality1q_r2.runner import run_call as r2_call
from forgeai.cli import ReplayModel, replay_binding
from forgeai_eval.preflight import PreflightError, PreflightFailure

HELDOUT = {c.id: c for c in q.load_heldout()}
CASE = HELDOUT["q23"]  # expected succeeded; fx/convert.py, fx/rates.py
INSUFFICIENT_CASE = HELDOUT["q19"]  # expected insufficient_evidence
PATH = sorted(CASE.supplied)[0]
SENTINEL = "insufficient-diag-sentinel-must-not-leak"
MODEL = "qwen2.5-coder:7b"
DIGEST = "sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364"
FINDING = {"text": "Supplied evidence.", "paths": [PATH]}


def reply(*, drop: tuple[str, ...] = (), **fields: object) -> str:
    value: dict[str, object] = {
        "status": "insufficient_evidence",
        "summary": "Synthetic replay for diagnostic qualification.",
        "relevant_files": [PATH],
        "findings": [],
        "risks": [],
        "unknowns": ["Unresolved."],
    }
    value.update(fields)
    for name in drop:
        del value[name]
    return json.dumps(value)


def call(output: str, case: object = CASE) -> dict[str, object]:
    return run_call(case, 1, replay_binding(ReplayModel(output)))  # type: ignore[arg-type]


# Analyst, parser and r2 immutability -----------------------------------------


def test_analyst_and_r2_condition_are_unchanged() -> None:
    r2.freeze()
    analyst = r2.read()["analyst"]
    assert isinstance(analyst, dict)
    # The diagnostic sampled the preregistered 1.0.1; a later Analyst is refused.
    assert analyst["version"] == "1.0.1"
    assert q.analyst_version() != analyst["version"]
    with pytest.raises(r2.AnalystIdentityError):
        r2.require_live_identity()
    current = r2.parser_identity((q.ROOT / r2.API).read_text(encoding="utf-8"))
    assert current == analyst["parser_identity"]


def test_linkage_is_the_recorded_r2_identity() -> None:
    doc = (
        q.ROOT / "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R2.md"
    ).read_text(encoding="utf-8")
    for key in (
        "r2_commit",
        "r2_report_sha256",
        "r2_condition_sha256",
        "r2_condition_digest",
    ):
        assert str(report.LINKAGE[key]) in doc
    assert report.LINKAGE["r2_decision"] == "B"
    assert report.LINKAGE["r2_heldout_validity"] == {"numerator": 59, "denominator": 72}
    assert cli.freeze()["diagnostic_predeclaration"] == cli.predeclaration_digest()


# Refined taxonomy and clause classification -----------------------------------


@pytest.mark.parametrize(
    ("findings", "unknowns", "expected"),
    [
        (1, 1, Refined.FINDINGS_PRESENT),
        (0, 0, Refined.UNKNOWNS_EMPTY),
        (2, 0, Refined.BOTH),
        (0, 1, None),
        (0, 8, None),
    ],
)
def test_refinement_mirrors_the_unchanged_rule(
    findings: int, unknowns: int, expected: Refined | None
) -> None:
    assert refine(findings, unknowns) is expected


@pytest.mark.parametrize(
    ("fields", "refined", "counts"),
    [
        ({"findings": [FINDING]}, Refined.FINDINGS_PRESENT, (1, 1)),
        ({"unknowns": []}, Refined.UNKNOWNS_EMPTY, (0, 0)),
        ({"findings": [FINDING], "unknowns": []}, Refined.BOTH, (1, 0)),
    ],
    ids=["findings", "unknowns", "both"],
)
def test_insufficient_clauses_agree_with_the_analyst(
    fields: dict[str, Any], refined: Refined, counts: tuple[int, int]
) -> None:
    for output in (reply(**fields), "```json\n" + reply(**fields) + "\n```"):
        record = call(output)
        assert record["runtime_status"] == "output_invalid"
        assert record["stage"] == Stage.INSUFFICIENT_INCONSISTENT
        assert record["category"] == "insufficient_inconsistent"
        assert record["refined"] == refined
        assert (record["findings_count"], record["unknowns_count"]) == counts
        assert record["findings_present"] is (counts[0] > 0)
        assert record["unknowns_empty"] is (counts[1] == 0)
        assert record["abstention"] == Abstention.INVALID_ABSTENTION
        assert record["refinement_consistent"] is True
        assert record["coarse_consistent"] is True


def test_valid_abstention_and_valid_success_are_separate() -> None:
    abstained = call(reply())
    assert abstained["stage"] == Stage.VALID
    assert abstained["runtime_status"] == "insufficient_evidence"
    assert abstained["abstention"] == Abstention.VALID_ABSTENTION
    assert abstained["refined"] is None
    assert (abstained["findings_count"], abstained["unknowns_count"]) == (0, 1)
    success = call(reply(status="succeeded", findings=[FINDING]))
    assert success["abstention"] == Abstention.VALID_SUCCESS
    assert success["actual_status"] == "succeeded"
    assert success["findings_count"] is None and success["refined"] is None


@pytest.mark.parametrize(
    ("output", "stage"),
    [
        ("The convert module is relevant.", Stage.RESPONSE_NOT_JSON),
        (reply(drop=("risks",), findings=[FINDING]), Stage.FIELD_SET_INVALID),
        (reply(findings={"text": "x"}), Stage.FINDINGS_SHAPE_INVALID),
        (reply(unknowns="x", findings=[FINDING]), Stage.UNKNOWNS_SHAPE_INVALID),
        (reply(summary="x" * 2049, findings=[FINDING]), Stage.SUMMARY_BOUNDS_INVALID),
        (
            reply(status="succeeded", relevant_files=["not/supplied.py"]),
            Stage.MEMBERSHIP_INVALID,
        ),
    ],
    ids=[
        "not_json",
        "field_set",
        "findings_shape",
        "unknowns_shape",
        "bounds",
        "membership",
    ],
)
def test_first_failure_ordering_is_preserved(output: str, stage: Stage) -> None:
    record = call(output)
    assert record["stage"] == stage
    assert record["refined"] is None and record["findings_count"] is None
    assert record["abstention"] == Abstention.OTHER_INVALID
    assert record["coarse_consistent"] is True


def test_insufficient_rule_precedes_membership() -> None:
    finding = {"text": "x", "paths": ["not/supplied.py"]}
    record = call(reply(findings=[finding]))
    assert record["stage"] == Stage.INSUFFICIENT_INCONSISTENT
    assert record["refined"] == Refined.FINDINGS_PRESENT


def test_records_extend_the_r2_record_for_the_same_reply() -> None:
    output = reply(findings=[FINDING])
    ours = call(output)
    theirs = r2_call(CASE, 1, replay_binding(ReplayModel(output)))
    for key in ("case", "partition", "class", "repetition", "expected", "runtime_status",
                "category", "stage", "representation", "coarse_consistent"):  # fmt: skip
        assert ours[key] == theirs[key], key
    assert ours["actual_status"] == theirs["status_value"]


def test_expected_outcome_and_actual_status_linkage() -> None:
    record = call(reply(), INSUFFICIENT_CASE)
    assert (
        record["expected"]
        == INSUFFICIENT_CASE.oracle.expected
        == "insufficient_evidence"
    )
    assert record["actual_status"] == "insufficient_evidence"
    assert call(reply())["expected"] == "succeeded"
    assert call("not json")["actual_status"] is None


def test_observe_takes_counts_only_after_the_rule_is_reached() -> None:
    assert observe(Diagnosis(Stage.FIELD_SET_INVALID, "raw", status_value="insufficient_evidence"), reply())["findings_count"] is None  # fmt: skip
    assert observe(Diagnosis(Stage.MODEL_FAILURE, "none"), None)["abstention"] == "other_invalid"  # fmt: skip


# Folding, confusion, abstention, decision --------------------------------------


def row(
    expected: str,
    stage: str,
    status: str | None,
    refined: str | None = None,
    partition: str = "heldout",
    case: str = "q01",
) -> dict[str, object]:
    return {
        "case": case,
        "partition": partition,
        "class": "c",
        "repetition": 1,
        "expected": expected,
        "runtime_status": "x",
        "category": "valid" if stage == "valid" else stage,
        "stage": stage,
        "representation": "raw",
        "actual_status": status,
        "abstention": abstention(stage, status).value,
        "findings_count": None if refined is None else 1,
        "unknowns_count": None if refined is None else 1,
        "findings_present": None,
        "unknowns_empty": None,
        "refined": refined,
        "refinement_consistent": True,
        "coarse_consistent": True,
        "seconds": 1.0,
    }


SUC, INS = "succeeded", "insufficient_evidence"
FP = Refined.FINDINGS_PRESENT.value


def test_confusion_and_abstention_fold_exactly() -> None:
    records = [
        row(SUC, "valid", SUC),
        row(SUC, "valid", INS),
        row(SUC, "insufficient_inconsistent", INS, FP),
        row(SUC, "response_not_json", None),
        row(INS, "valid", SUC),
        row(INS, "valid", INS, partition="cd1_probe", case="c15"),
    ]
    aggregate = report.fold(records)
    held = aggregate["partitions"]["heldout"]  # type: ignore[index]
    assert held["confusion"] == {
        SUC: {SUC: 1, INS: 2, "unparsed": 1},
        INS: {SUC: 1, INS: 0, "unparsed": 0},
    }
    assert held["abstention"] == {
        "valid_abstention": {SUC: 1, INS: 0},
        "invalid_abstention": {SUC: 1, INS: 0},
        "valid_success": {SUC: 1, INS: 1},
        "other_invalid": {SUC: 1, INS: 0},
    }
    assert held["refined"] == {FP: 1}
    everything = cast(dict[str, Any], aggregate["all"])
    assert sum(sum(v.values()) for v in everything["confusion"].values()) == 6
    assert everything["actual_status"] == {SUC: 2, INS: 3, "unparsed": 1}
    assert aggregate["by_case"]["c15"] == {"valid_abstention": 1}  # type: ignore[index]
    assert report.fold(list(reversed(records)))["all"] == everything


@pytest.mark.parametrize(
    ("records", "code"),
    [
        ([row(SUC, "valid", INS)] * 6 + [row(SUC, "valid", SUC)] * 4, "B"),
        (
            [row(SUC, "valid", SUC)] * 6
            + [row(SUC, "insufficient_inconsistent", INS, FP)] * 4,
            "A",
        ),
        (
            [row(SUC, "valid", SUC)] * 6
            + [row(SUC, "insufficient_inconsistent", INS, FP)] * 2
            + [row(SUC, "insufficient_inconsistent", INS, Refined.UNKNOWNS_EMPTY.value)]
            * 2,
            "D",
        ),
        ([row(SUC, "valid", SUC)] * 6 + [row(SUC, "response_not_json", None)] * 4, "D"),
        (
            [row(SUC, "valid", SUC)] * 6 + [row(SUC, "classifier_disagreement", SUC)],
            "D",
        ),
    ],
    ids=["abstention", "clarification", "split_clauses", "other_stage", "integrity"],
)
def test_next_decision_rule(records: list[dict[str, object]], code: str) -> None:
    decision = report.decide(records, clauses_recorded=True)
    assert decision["code"] == code
    assert decision["label"] == report.DECISIONS[code]


def test_recorded_mode_cannot_select_a_without_clauses() -> None:
    records = [row(SUC, "valid", SUC)] * 6 + [
        {**row(SUC, "insufficient_inconsistent", INS), "refined": None}
    ] * 4
    assert report.decide(records, clauses_recorded=False)["code"] is None
    assert (
        report.decide([row(SUC, "valid", INS)] * 3, clauses_recorded=False)["code"]
        == "B"
    )


def test_from_r2_maps_recorded_records() -> None:
    base = {
        "case": "q01", "partition": "heldout", "class": "c", "repetition": 1,
        "expected": SUC, "runtime_status": "output_invalid",
        "category": "insufficient_inconsistent", "stage": "insufficient_inconsistent",
        "representation": "raw", "status_value": INS, "coarse_consistent": True,
        "seconds": 1.0, "predicted": None, "field_types": {}, "summary": SENTINEL,
    }  # fmt: skip
    mapped = report.from_r2(base)
    assert mapped["abstention"] == Abstention.INVALID_ABSTENTION
    assert mapped["refined"] is None and mapped["findings_count"] is None
    assert SENTINEL not in json.dumps(mapped) and "predicted" not in mapped
    unparsed = report.from_r2(
        {**base, "stage": "response_not_json", "status_value": None}
    )
    assert unparsed["actual_status"] is None
    assert unparsed["abstention"] == Abstention.OTHER_INVALID


def test_recorded_mode_requires_the_exact_r2_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = tmp_path / "report.json"
    body = {
        "schema": "forgeai-analyst-quality-report/2",
        "mode": "live",
        "condition_digest": report.LINKAGE["r2_condition_digest"],
        "records": [],
    }
    fake.write_bytes(json.dumps(body).encode())
    with pytest.raises(cli.RecordedReportError):
        cli.recorded_records(fake)
    with pytest.raises(SystemExit):
        cli.main(
            ["recorded", "--r2-report", str(fake), "--output", str(tmp_path / "o")]
        )
    assert not (tmp_path / "o").exists()
    pinned = hashlib.sha256(fake.read_bytes()).hexdigest()
    monkeypatch.setitem(report.LINKAGE, "r2_report_sha256", pinned)
    assert cli.recorded_records(fake) == []
    fake.write_bytes(json.dumps({**body, "mode": "replay"}).encode())
    monkeypatch.setitem(
        report.LINKAGE,
        "r2_report_sha256",
        hashlib.sha256(fake.read_bytes()).hexdigest(),
    )
    with pytest.raises(cli.RecordedReportError):
        cli.recorded_records(fake)


# Report, privacy ---------------------------------------------------------------


def test_replay_report_schema_and_deterministic_folding(tmp_path: Path) -> None:
    output = tmp_path / "replay"
    fixed = reply(findings=[FINDING])
    assert cli.main(["replay", "--output", str(output), "--replay-output", fixed]) == 0
    condition = json.loads((output / "condition.json").read_text("utf-8"))
    written = json.loads((output / "report.json").read_text("utf-8"))
    assert condition["schema"] == report.CONDITION_SCHEMA
    assert condition["analyst"]["version"] == q.analyst_version()
    assert condition["linkage"] == report.LINKAGE
    assert set(written) == {
        "schema", "mode", "condition", "condition_digest", "linkage", "records",
        "aggregate", "decision", "refined_categories", "limitations",
    }  # fmt: skip
    assert written["schema"] == report.SCHEMA
    assert written["decision"]["code"] is None
    assert written["decision"]["label"] == "REPLAY ONLY - not a decision"
    records = written["records"]
    assert len(records) == 91
    rebuilt = report.build(written["condition"], records)
    assert rebuilt["aggregate"] == written["aggregate"]
    assert rebuilt["decision"] == written["decision"]
    assert (output / "report.md").read_text("utf-8") == report.render(written)
    stages = written["aggregate"]["all"]["stages"]
    answerable = sum(1 for c, _ in q.plan() if c.oracle.expected == "succeeded")
    assert stages["insufficient_inconsistent"] == 91 == len(records)
    assert written["aggregate"]["all"]["confusion"][SUC][INS] == answerable


def test_report_privacy(tmp_path: Path) -> None:
    leaky = reply(
        summary=SENTINEL,
        findings=[{"text": SENTINEL, "paths": [PATH]}],
        unknowns=[SENTINEL],
        risks=[SENTINEL],
    )
    extra = json.loads(reply(findings=[FINDING]))
    extra[SENTINEL] = SENTINEL
    records = [call(leaky), call(json.dumps(extra)), call(SENTINEL)]
    condition = cli.condition(
        "replay", cli.freeze(), {"head": "h"}, {"name": "m"}, "hw"
    )
    report.write(report.build(condition, records), tmp_path)
    for name in ("report.json", "report.md"):
        text = (tmp_path / name).read_text("utf-8")
        assert SENTINEL not in text
        assert CASE.question not in text
        assert PATH not in text  # no predicted paths are recorded
        assert str(q.ROOT) not in text
        for f in CASE.files:
            assert f.text not in text


# Live refusals (r2 preflight) ----------------------------------------------------


def live_argv(output: Path, digest: str = DIGEST) -> list[str]:
    return [
        "live", "--output", str(output), "--model", MODEL, "--hardware", "h",
        "--model-digest", digest, "--expect-branch", "b", "--expect-commit", "c",
    ]  # fmt: skip


def refuse_ollama(*args: object) -> object:
    raise PreflightError(PreflightFailure.OLLAMA_UNREACHABLE, "no")


@pytest.mark.parametrize(
    "patch",
    [
        ("analyst_version", lambda: "1.0.0"),
        ("definition_fingerprint", lambda: "0" * 64),
    ],
    ids=["version", "fingerprint"],
)
def test_live_refuses_a_different_analyst(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, patch: tuple[str, object]
) -> None:
    monkeypatch.setattr(q, *patch)
    monkeypatch.setattr(cli, "verify_ollama", refuse_ollama)
    output = tmp_path / "live"
    assert cli.main(live_argv(output)) == cq.PREFLIGHT_FAILED
    assert not output.exists()


def test_live_refuses_model_checkout_and_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(r2, "require_live_identity", lambda: None)  # past identity
    monkeypatch.setattr(cli, "verify_ollama", refuse_ollama)
    output = tmp_path / "live"
    assert cli.main(live_argv(output, "sha256:" + "a" * 64)) == cq.PREFLIGHT_FAILED
    monkeypatch.setattr(cq, "git", lambda args: {"rev-parse": "c", "branch": "b", "status": " M x"}[args[0]])  # fmt: skip
    assert cli.main(live_argv(output)) == cq.PREFLIGHT_FAILED
    monkeypatch.setattr(cq, "git_state", lambda *a: {"head": "h"})
    assert cli.main(live_argv(output)) == cq.PREFLIGHT_FAILED  # Ollama unreachable
    assert not output.exists()
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(SystemExit):
        cli.main(live_argv(existing))


def test_live_refuses_the_current_later_analyst(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def never(*args: object) -> object:
        raise AssertionError("refused before checkout or provider access")

    monkeypatch.setattr(cq, "git_state", never)
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    assert cli.main(live_argv(output)) == cq.PREFLIGHT_FAILED
    assert not output.exists()


def test_harness_is_evaluation_only() -> None:
    source = "\n".join(
        p.read_text("utf-8")
        for p in (q.HERE.parent / "analyst_insufficient_diag1").glob("*.py")
    )
    for forbidden in ("mutation", "AuthorizedEngineeringChecks", "CodingAgent",
                      "IndependentReviewer", "forgeai.worker"):  # fmt: skip
        assert forbidden not in source, forbidden
