"""CONTENT-DISCOVERY-1Q-R3 condition qualification. No live model is contacted.

Replay calls run through the real public host, AuthorizedRepositoryEvidence and
RepositoryAnalyst 1.0.2; replay outputs exercise the harness only and are never
quality evidence.
"""

import json
from pathlib import Path

import pytest
from analyst_contract_diag1 import report as diag_report
from analyst_contract_diag1.diagnose import Stage
from analyst_insufficient_diag1 import report as aid_report
from analyst_insufficient_diag1.clauses import Abstention, Refined
from analyst_insufficient_diag1.runner import run_call as aid_call
from analyst_quality1q import cli as cq
from analyst_quality1q import data as q
from analyst_quality1q import metrics
from analyst_quality1q.classify import Category
from analyst_quality1q.harness import CallResult
from analyst_quality1q_r2 import data as r2
from analyst_quality1q_r2.runner import run_call as r2_call
from analyst_quality1q_r3 import cli, data, report
from analyst_quality1q_r3.runner import run_call
from content_discovery1 import data as cd1
from forgeai.cli import ReplayModel, replay_binding
from forgeai_eval.preflight import PreflightError, PreflightFailure

CASE = {c.id: c for c in q.load_heldout()}["q23"]
REQUIRED = sorted(CASE.oracle.required)
SENTINEL = "r3-sentinel-must-not-leak"
V100 = "924bdaac617c51341b56d27bb3aef53a7e37dd358d85e37f43bdf4e5c9a659b7"
V101 = "f99564e6a483eb91f8d9221f0206ea358251c74295608115c1253103125c2cc0"
V102 = "5f6635c756df41a855fd1ab8b538765267ba97b31410b16125e905697b82ceef"
IMPLEMENTATION = "f1cd2b69ca6c7cdcf0c9cd19ba8f349253f0379b"
MODEL = "qwen2.5-coder:7b"
DIGEST = "sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364"
HARDWARE = "Windows 11 laptop, 16-core CPU, 32 GB RAM, 8 GB GPU"


def reply(*, drop: tuple[str, ...] = (), **fields: object) -> str:
    value: dict[str, object] = {
        "status": "succeeded",
        "summary": "Synthetic replay for R3 qualification.",
        "relevant_files": REQUIRED,
        "findings": [],
        "risks": [],
        "unknowns": [],
    }
    value.update(fields)
    for name in drop:
        del value[name]
    return json.dumps(value)


def record(output: str) -> dict[str, object]:
    return run_call(CASE, 1, replay_binding(ReplayModel(output)))


def live_argv(
    output: Path, digest: str = DIGEST, hardware: str = HARDWARE
) -> list[str]:
    return [
        "live", "--output", str(output), "--model", MODEL, "--hardware", hardware,
        "--model-digest", digest, "--expect-branch", "b", "--expect-commit", "c",
    ]  # fmt: skip


def never(*args: object) -> object:
    raise AssertionError("must be refused before this point")


def refuse_ollama(*args: object) -> object:
    raise PreflightError(PreflightFailure.OLLAMA_UNREACHABLE, "no")


# Analyst 1.0.2 identity and qualification ------------------------------------


def pretend_pinned(monkeypatch: pytest.MonkeyPatch) -> None:
    """Present exactly the preregistered 1.0.2 identity so that later preflight
    steps are reached; the working-tree Analyst is a later version."""
    analyst = data.read()["analyst"]
    assert isinstance(analyst, dict)
    sources = analyst["sources"]
    assert isinstance(sources, dict)
    real = q.digest

    def digest(path: Path) -> str:
        relative = path.resolve().relative_to(q.ROOT).as_posix()
        return str(sources[relative]) if relative in sources else real(path)

    monkeypatch.setattr(q, "analyst_version", lambda: "1.0.2")
    monkeypatch.setattr(q, "definition_fingerprint", lambda: V102)
    monkeypatch.setattr(q, "digest", digest)


def test_analyst_identity_is_pinned_to_1_0_2(monkeypatch: pytest.MonkeyPatch) -> None:
    analyst = data.read()["analyst"]
    assert isinstance(analyst, dict)
    assert analyst["version"] == "1.0.2"
    assert analyst["definition_fingerprint"] == V102
    assert V102 not in {V100, V101}
    assert analyst["implementation_commit"] == IMPLEMENTATION
    # A later Analyst may not be sampled under this frozen 1.0.2 condition.
    assert q.analyst_version() != "1.0.2"
    assert q.definition_fingerprint() != V102
    with pytest.raises(data.AnalystIdentityError):
        data.require_live_identity()
    pretend_pinned(monkeypatch)
    data.require_live_identity()  # the pinned 1.0.2 identity itself still passes


def test_parser_identity_is_unchanged_from_1_0_1() -> None:
    analyst = data.read()["analyst"]
    previous = r2.read()["analyst"]
    assert isinstance(analyst, dict) and isinstance(previous, dict)
    current = r2.parser_identity((q.ROOT / data.API).read_text(encoding="utf-8"))
    assert current == analyst["parser_identity"] == previous["parser_identity"]
    sources, before = analyst["sources"], previous["sources"]
    assert isinstance(sources, dict) and isinstance(before, dict)
    assert {p for p in sources if sources[p] != before[p]} == {data.API}


def test_sufficiency_prompt_qualification_identity() -> None:
    committed = r2.committed_text(IMPLEMENTATION, data.API)
    assert "Version(1, 0, 2)" in committed
    assert "Status decision policy" in committed
    analyst = data.read()["analyst"]
    assert isinstance(analyst, dict)
    sources = analyst["sources"]
    assert isinstance(sources, dict)
    assert sources[data.API] == cd1.committed_digest(IMPLEMENTATION, data.API)


@pytest.mark.parametrize(
    ("module", "name", "value"),
    [
        ("q", "analyst_version", lambda: "1.0.1"),
        ("q", "analyst_version", lambda: "1.0.3"),
        ("q", "definition_fingerprint", lambda: V101),
        ("q", "definition_fingerprint", lambda: "0" * 64),
        ("q", "digest", lambda path: "0" * 64),
        ("data", "working_parser_identity", lambda: "0" * 64),
    ],
    ids=[
        "version_1_0_1",
        "version_1_0_3",
        "fingerprint_1_0_1",
        "fingerprint",
        "source",
        "parser",
    ],
)
def test_wrong_analyst_identity_is_refused(
    monkeypatch: pytest.MonkeyPatch, module: str, name: str, value: object
) -> None:
    pretend_pinned(monkeypatch)
    monkeypatch.setattr({"q": q, "data": data}[module], name, value)
    with pytest.raises(data.AnalystIdentityError):
        data.require_live_identity()


def test_implementation_commit_must_be_an_ancestor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pre = data.read()
    analyst = pre["analyst"]
    assert isinstance(analyst, dict)
    pretend_pinned(monkeypatch)
    forged = {**pre, "analyst": {**analyst, "implementation_commit": "f" * 40}}
    monkeypatch.setattr(data, "read", lambda: forged)
    with pytest.raises(data.AnalystIdentityError):
        data.require_live_identity()


# Historical immutability -------------------------------------------------------


def test_historical_conditions_are_pinned_and_refuse_1_0_2() -> None:
    cd1.freeze()
    q.freeze()
    r2.freeze()
    with pytest.raises(q.AnalystIdentityError):
        q.require_live_identity()  # 1Q is 1.0.0
    with pytest.raises(r2.AnalystIdentityError):
        r2.require_live_identity()  # r2 and DIAG-1 are 1.0.1
    previous = r2.read()["analyst"]
    assert isinstance(previous, dict) and previous["version"] == "1.0.1"
    assert aid_report.LINKAGE["r2_report_sha256"] == (
        "e5a0efd31ff391ccafcc70d6f57bdca6ca8f69c994c28f3e99ab2671c199e49c"
    )


def test_historical_references_are_recorded_not_recomputed() -> None:
    historical = data.read()["historical"]
    assert isinstance(historical, dict)
    assert historical["1q"]["validity_all"] == {"numerator": 0, "denominator": 91}
    r2_ref, diag_ref = historical["r2"], historical["diag1"]
    assert isinstance(r2_ref, dict) and isinstance(diag_ref, dict)
    assert r2_ref["answerable_success"] == {"numerator": 13, "denominator": 60}
    assert r2_ref["heldout_validity"] == {"numerator": 59, "denominator": 72}
    assert diag_ref["answerable_success"] == {"numerator": 17, "denominator": 60}
    assert diag_ref["valid_abstention"] == {"numerator": 31, "denominator": 60}
    assert diag_ref["invalid_abstention"] == {"numerator": 12, "denominator": 60}
    assert diag_ref["insufficient_findings_present"] == {
        "numerator": 12,
        "denominator": 12,
    }
    assert r2_ref["report_sha256"] == aid_report.LINKAGE["r2_report_sha256"]


# Frozen workload, call plan, model, decision -----------------------------------


def test_frozen_inputs_are_reused_by_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    digests = data.freeze()
    reused = data.read()["reused"]
    assert isinstance(reused, dict)
    assert reused == {k: digests[k] for k in reused}
    assert {k: v for k, v in digests.items() if k != "r3_preregistration"} == (
        q.freeze()
    )
    assert reused["heldout"] == q.read("manifest-v1.json")["heldout-v1.json"]
    monkeypatch.setattr(data, "PREREGISTRATION_DIGEST", "0" * 64)
    with pytest.raises(ValueError):
        data.freeze()


def test_tampered_oracle_input_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    real = q.digest
    monkeypatch.setattr(
        q,
        "digest",
        lambda path: "0" * 64 if path.name == "heldout-v1.json" else real(path),
    )
    with pytest.raises(ValueError):
        data.freeze()


def test_partition_and_call_plan() -> None:
    assert cq.plan_counts(q.plan()) == {
        "cd1_probe_calls": 5,
        "cd1_quality_calls": 14,
        "cd1_repetitions": 1,
        "heldout_calls": 72,
        "heldout_cases": 24,
        "heldout_repetitions": 3,
        "total_calls": 91,
    }
    partition = q.read("partition-v1.json")
    assert partition["no_analyst_call"] == ["c18"]
    pre = data.read()
    assert pre["planned_calls"] == {
        "heldout": 72,
        "cd1_quality": 14,
        "cd1_probe": 5,
        "total": 91,
    }
    assert pre["repetitions"] == {"heldout": 3, "cd1": 1}


def test_thresholds_are_frozen() -> None:
    limits = q.thresholds()
    assert limits["validity_min"] == 0.9 and limits["precision_min"] == 0.85
    assert limits["required_recall_min"] == 0.9
    assert limits["acceptable_set_min"] == 0.8
    assert limits["insufficient_correct_min"] == 0.9
    assert limits["false_sufficient_max"] == limits["catastrophic_max"] == 0
    assert limits["classifier_disagreement_max"] == 0
    assert limits["model_failure_rate_max"] == 0.1
    assert data.read()["reused"]["thresholds"] == q.digest(  # type: ignore[index]
        q.HERE / "thresholds-v1.json"
    )


def test_model_condition_is_frozen() -> None:
    model = data.read()["model_condition"]
    assert model == q.read("preregistration-v1.json")["model_condition"]
    assert isinstance(model, dict)
    assert model["name"] == MODEL and model["digest"] == DIGEST
    assert model["timeout_seconds"] == cq.TIMEOUT_SECONDS == 600
    assert model["fallback"] == model["retries"] == "none"


def test_decision_function_is_the_frozen_1q_rule() -> None:
    used = vars(report)
    assert used["decide"] is metrics.decide
    assert used["gates"] is metrics.gates and used["fold"] is metrics.fold
    assert set(metrics.DECISIONS) == {"A", "B", "C", "D"}
    assert metrics.DECISIONS["B"] == "ANALYST OUTPUT CONTRACT IS THE PRIMARY BLOCKER"


# Per-call diagnostics -------------------------------------------------------------


def test_structural_diagnostics_reuse_diag1() -> None:
    missing = record(reply(drop=("risks",)))
    assert missing["stage"] == Stage.FIELD_SET_INVALID
    assert missing["missing_required_fields"] == ["risks"]
    assert missing["category"] == Category.SCHEMA_INVALID
    assert missing["coarse_consistent"] is True and missing["refined"] is None
    fenced = record("```json\n" + reply() + "\n```")
    assert fenced["representation"] == "fenced_json" and fenced["valid"] is True
    output = reply(status="insufficient_evidence", findings=[], unknowns=["u"])
    ours = record(output)
    theirs = r2_call(CASE, 1, replay_binding(ReplayModel(output)))
    assert {k: ours[k] for k in theirs} == {
        k: v for k, v in theirs.items() if k != "seconds"
    } | {"seconds": ours["seconds"]}


def test_clause_diagnostics_reuse_insufficient_diag1() -> None:
    finding = {"text": "x", "paths": REQUIRED[:1]}
    for fields, refined in (
        ({"findings": [finding], "unknowns": ["u"]}, Refined.FINDINGS_PRESENT),
        ({"findings": [], "unknowns": []}, Refined.UNKNOWNS_EMPTY),
        ({"findings": [finding], "unknowns": []}, Refined.BOTH),
    ):
        output = reply(status="insufficient_evidence", **fields)
        ours = record(output)
        theirs = aid_call(CASE, 1, replay_binding(ReplayModel(output)))
        assert ours["refined"] == theirs["refined"] == refined
        for key in ("findings_count", "unknowns_count", "abstention", "actual_status"):
            assert ours[key] == theirs[key], key
        assert ours["abstention"] == Abstention.INVALID_ABSTENTION


def test_relevance_and_safety_metrics_are_the_1q_functions() -> None:
    ours = record(reply())
    expected = metrics.score(
        CASE,
        1,
        CallResult(
            "succeeded",
            Category.VALID,
            tuple(REQUIRED),
            tuple(REQUIRED),
            tuple(sorted(CASE.supplied)),
            ours["seconds"],  # type: ignore[arg-type]
        ),
    )
    assert {k: ours[k] for k in expected} == expected
    for key in (
        "unknown_path_accepted",
        "out_of_evidence_accepted",
        "authority_expansion",
        "source_text_authority",
    ):
        assert ours[key] == 0


# Folding ----------------------------------------------------------------------------


def row(
    expected: str, abstention: str, partition: str = "heldout"
) -> dict[str, object]:
    return {"partition": partition, "expected": expected, "abstention": abstention}


def test_answerable_and_abstention_folding() -> None:
    rows = (
        [row("succeeded", "valid_success")] * 20
        + [row("succeeded", "valid_abstention")] * 25
        + [row("succeeded", "invalid_abstention")] * 10
        + [row("succeeded", "other_invalid")] * 5
        + [row("insufficient_evidence", "valid_abstention")] * 12
        + [row("succeeded", "valid_success", "cd1_quality")] * 7
    )
    folded = report.answerable(rows)
    assert folded["calls"] == 60
    assert folded["answerable_success_rate"] == {
        "numerator": 20,
        "denominator": 60,
        "value": 0.3333,
    }
    assert folded["valid_abstention"]["numerator"] == 25  # type: ignore[index]
    assert folded["invalid_abstention"]["numerator"] == 10  # type: ignore[index]
    assert folded["other_invalid"]["numerator"] == 5  # type: ignore[index]
    assert folded["total_abstention"]["numerator"] == 35  # type: ignore[index]


def test_replay_report_schema_and_reproduction(tmp_path: Path) -> None:
    output = tmp_path / "replay"
    assert cli.main(["replay", "--output", str(output)]) == 0
    condition = json.loads((output / "condition.json").read_text("utf-8"))
    written = json.loads((output / "report.json").read_text("utf-8"))
    assert condition["schema"] == report.CONDITION_SCHEMA
    assert condition["analyst"]["version"] == q.analyst_version()
    assert condition["analyst"]["definition_fingerprint"] == q.definition_fingerprint()
    assert condition["fixtures"] == data.freeze()
    assert set(written) == {
        "schema", "mode", "condition", "condition_digest", "records", "aggregate",
        "thresholds", "gates", "decision", "quality_is_decision_evidence",
        "structural", "clauses", "answerable", "over_correction",
        "historical_comparison", "definitions", "limitations",
    }  # fmt: skip
    assert written["schema"] == report.SCHEMA
    assert written["decision"]["label"] == "REPLAY ONLY - not quality evidence"
    records = written["records"]
    assert len(records) == 91
    historical = data.read()["historical"]
    rebuilt = report.build(written["condition"], records, q.thresholds(), historical)  # type: ignore[arg-type]
    for key in (
        "aggregate", "gates", "decision", "structural", "clauses", "answerable",
        "over_correction", "historical_comparison", "condition_digest",
    ):  # fmt: skip
        assert rebuilt[key] == written[key], key
    assert written["aggregate"] == metrics.fold(records)
    assert written["clauses"] == aid_report.fold(records)
    assert written["structural"]["all"] == diag_report.summarize(records)
    assert (output / "report.md").read_text("utf-8") == report.render(written)
    # Oracle-shaped replay answers every case as expected.
    assert written["answerable"]["answerable_success_rate"]["numerator"] == 60
    assert written["answerable"]["total_abstention"]["numerator"] == 0
    watch = written["over_correction"]
    assert watch["expected_insufficient_to_succeeded"]["heldout"] == {
        "expected_insufficient": 12,
        "answered_succeeded": 0,
    }
    assert watch["heldout_false_sufficient"] == 0
    held = written["clauses"]["partitions"]["heldout"]["confusion"]
    assert held == {
        "succeeded": {"succeeded": 60, "insufficient_evidence": 0, "unparsed": 0},
        "insufficient_evidence": {
            "succeeded": 0,
            "insufficient_evidence": 12,
            "unparsed": 0,
        },
    }


def test_report_privacy(tmp_path: Path) -> None:
    leaky = json.dumps(
        {
            "status": "insufficient_evidence",
            "summary": SENTINEL,
            "relevant_files": REQUIRED,
            "findings": [{"text": SENTINEL, "paths": REQUIRED}],
            "risks": [SENTINEL],
            "unknowns": [SENTINEL],
            SENTINEL: SENTINEL,
        }
    )
    records = [
        record(leaky),
        record(reply(risks=[SENTINEL], unknowns=[SENTINEL], summary=SENTINEL)),
        record(SENTINEL),
    ]
    condition = cli.condition(
        "replay", data.freeze(), q.plan(), {"head": "h"}, {"name": "m"}, "hw"
    )
    historical = data.read()["historical"]
    assert isinstance(historical, dict)
    report.write(report.build(condition, records, q.thresholds(), historical), tmp_path)
    for name in ("report.json", "report.md"):
        text = (tmp_path / name).read_text("utf-8")
        assert SENTINEL not in text
        assert CASE.question not in text
        assert str(q.ROOT) not in text and str(tmp_path) not in text
        for f in CASE.files:
            assert f.text not in text


# Live refusals ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "value"),
    [("analyst_version", lambda: "1.0.1"), ("definition_fingerprint", lambda: V101)],
    ids=["version", "fingerprint"],
)
def test_live_refuses_wrong_analyst(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, value: object
) -> None:
    pretend_pinned(monkeypatch)
    monkeypatch.setattr(q, name, value)
    monkeypatch.setattr(cq, "git_state", never)
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    assert cli.main(live_argv(output)) == cq.PREFLIGHT_FAILED
    assert not output.exists()


def test_live_refuses_parser_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pretend_pinned(monkeypatch)
    monkeypatch.setattr(data, "working_parser_identity", lambda: "0" * 64)
    monkeypatch.setattr(cq, "git_state", never)
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    assert cli.main(live_argv(output)) == cq.PREFLIGHT_FAILED
    assert not output.exists()


@pytest.mark.parametrize(
    "state",
    [{"status": " M examples/forgeai/x.py"}, {"branch": "other"}, {"rev-parse": "zzz"}],
    ids=["dirty", "branch", "commit"],
)
def test_live_refuses_checkout_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: dict[str, str]
) -> None:
    pretend_pinned(monkeypatch)
    good = {"rev-parse": "c", "branch": "b", "status": ""}
    monkeypatch.setattr(cq, "git", lambda args: {**good, **state}[args[0]])
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    assert cli.main(live_argv(output)) == cq.PREFLIGHT_FAILED
    assert not output.exists()


@pytest.mark.parametrize(
    ("model", "digest"),
    [(MODEL, "sha256:" + "a" * 64), ("qwen2.5-coder:3b", DIGEST)],
    ids=["digest", "name"],
)
def test_live_refuses_wrong_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, model: str, digest: str
) -> None:
    pretend_pinned(monkeypatch)
    monkeypatch.setattr(cq, "git_state", never)
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    argv = live_argv(output, digest)
    argv[argv.index(MODEL)] = model
    assert cli.main(argv) == cq.PREFLIGHT_FAILED
    assert not output.exists()


@pytest.mark.parametrize(
    "hardware",
    [
        "<REAL HARDWARE DESCRIPTION>",
        "<actual hardware description>",
        "<same hardware class as 1Q>",
        "TBD",
        "unknown",
        "placeholder machine",
        "  ",
    ],
)
def test_live_refuses_placeholder_hardware(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hardware: str
) -> None:
    pretend_pinned(monkeypatch)
    monkeypatch.setattr(cq, "git_state", never)
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    with pytest.raises(cli.HardwareError):
        cli.require_hardware(hardware)
    assert cli.main(live_argv(output, hardware=hardware)) in {cq.PREFLIGHT_FAILED, 2}
    assert not output.exists()
    assert cli.require_hardware(f"  {HARDWARE} ") == HARDWARE


def test_live_refuses_unreachable_ollama_and_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pretend_pinned(monkeypatch)
    monkeypatch.setattr(cq, "git_state", lambda *a: {"head": "h"})
    monkeypatch.setattr(cli, "verify_ollama", refuse_ollama)
    output = tmp_path / "live"
    assert cli.main(live_argv(output)) == cq.PREFLIGHT_FAILED
    assert not output.exists()
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "keep.txt").write_text("previous output", encoding="utf-8")
    with pytest.raises(SystemExit):
        cli.main(live_argv(existing))
    assert (existing / "keep.txt").read_text("utf-8") == "previous output"


def test_live_refuses_the_current_later_analyst(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cq, "git_state", never)
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    assert cli.main(live_argv(output)) == cq.PREFLIGHT_FAILED
    assert not output.exists()


def test_harness_is_evaluation_only() -> None:
    source = "\n".join(p.read_text("utf-8") for p in data.HERE.glob("*.py"))
    for forbidden in (
        "mutation",
        "AuthorizedEngineeringChecks",
        "CodingAgent",
        "IndependentReviewer",
        "forgeai.worker",
    ):
        assert forbidden not in source, forbidden
