"""CONTENT-DISCOVERY-1Q-R4 condition qualification. No live model is contacted.

Replay calls run through the real public host, AuthorizedRepositoryEvidence and
RepositoryAnalyst 1.0.3; replay outputs exercise the harness only and are never
quality evidence.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from analyst_contract_diag1 import report as diag_report
from analyst_contract_diag1.diagnose import Stage
from analyst_insufficient_diag1 import report as aid_report
from analyst_insufficient_diag1.clauses import Refined
from analyst_model_compare1 import data as compare
from analyst_quality1q import cli as cq
from analyst_quality1q import data as q
from analyst_quality1q import metrics
from analyst_quality1q.data import Case
from analyst_quality1q_r2 import data as r2
from analyst_quality1q_r3 import cli as r3cli
from analyst_quality1q_r3 import data as r3
from analyst_quality1q_r3 import report as r3report
from analyst_quality1q_r3.runner import run_call
from analyst_quality1q_r4 import cli, data, report
from content_discovery1 import data as cd1
from forgeai.cli import ReplayModel, replay_binding
from forgeai_eval.preflight import PreflightError, PreflightFailure

CASES = {c.id: c for c in (*q.load_heldout(), *q.load_cd1())}
SENTINEL = "r4-sentinel-must-not-leak"
V102 = "5f6635c756df41a855fd1ab8b538765267ba97b31410b16125e905697b82ceef"
V103 = "d97036c1435b99a28ba98abf1a565dedf5b3198c3b4065e80431ba74ae04bfbf"
PARSER = "016fcc40a0e341c5ec625fe11d130668608cde7d74d5a85a16bb4f9772812672"
IMPLEMENTATION = "c8e605a0a9ecc03e943360b88aedb7ebd1e96299"
MODEL = "qwen2.5-coder:14b"
DIGEST = "sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849"
HARDWARE = (
    "Intel Core i7-8565U (4 cores/8 threads), 16 GB RAM, "
    "NVIDIA GeForce MX130 + Intel UHD 620, Windows 11"
)
INSUFFICIENT = ["q19", "q20", "q21", "q22"]
CONTROLS = ["q11", "q12"]


def pre(module: Any) -> dict[str, Any]:
    """A preregistration, typed loosely for assertions."""
    return dict(module.read())


def reply(case: Case, **fields: object) -> str:
    value: dict[str, object] = json.loads(cq.replay_output(case))
    value.update(fields)
    return json.dumps(value)


def call(case_id: str, repetition: int, output: str) -> dict[str, object]:
    return run_call(CASES[case_id], repetition, replay_binding(ReplayModel(output)))


def answered(case_id: str) -> str:
    """A structurally valid succeeded reply naming one supplied path."""
    case = CASES[case_id]
    return reply(
        case,
        status="succeeded",
        relevant_files=sorted(case.supplied)[:1],
        unknowns=[],
    )


def abstained(case_id: str) -> str:
    return reply(
        CASES[case_id],
        status="insufficient_evidence",
        relevant_files=[],
        findings=[],
        unknowns=["u"],
    )


def invalid(case_id: str) -> str:
    return reply(CASES[case_id], status="insufficient_evidence", unknowns=[])


@pytest.fixture(scope="module")
def replayed() -> list[dict[str, object]]:
    """The oracle-shaped 91-call replay, computed once."""
    return r3cli.execute(
        q.plan(), lambda case, _: replay_binding(ReplayModel(cq.replay_output(case)))
    )


def swap(
    records: list[dict[str, object]], *changes: tuple[str, int, str]
) -> list[dict[str, object]]:
    replaced = {(c, rep): call(c, rep, output) for c, rep, output in changes}
    return [
        replaced.get((str(r["case"]), cast(int, r["repetition"])), r) for r in records
    ]


def build(records: list[dict[str, object]], mode: str = "live") -> dict[str, Any]:
    condition = cli.condition(
        mode, data.freeze(), q.plan(), {"head": "h"}, {"name": MODEL}, HARDWARE
    )
    return report.build(condition, records, q.thresholds(), data.read())


def held(built: dict[str, Any]) -> dict[str, Any]:
    return dict(built["aggregate"]["partitions"]["heldout"])


def live_argv(
    output: Path, model: str = MODEL, digest: str = DIGEST, hardware: str = HARDWARE
) -> list[str]:
    return [
        "live", "--output", str(output), "--model", model, "--hardware", hardware,
        "--model-digest", digest, "--expect-branch", "b", "--expect-commit", "c",
    ]  # fmt: skip


def never(*args: object) -> object:
    raise AssertionError("must be refused before this point")


def refuse_ollama(*args: object) -> object:
    raise PreflightError(PreflightFailure.OLLAMA_UNREACHABLE, "no")


def refused(monkeypatch: pytest.MonkeyPatch, output: Path, argv: list[str]) -> None:
    assert cli.main(argv) == cq.PREFLIGHT_FAILED
    assert not output.exists()


# Analyst 1.0.3 identity ----------------------------------------------------------


def test_analyst_identity_is_1_0_3() -> None:
    analyst = pre(data)["analyst"]
    assert isinstance(analyst, dict)
    assert analyst["agent_id"] == "repository-analyst"
    assert analyst["version"] == "1.0.3" == q.analyst_version()
    data.require_live_identity()


def test_fingerprint_pin() -> None:
    analyst = pre(data)["analyst"]
    assert isinstance(analyst, dict)
    assert analyst["definition_fingerprint"] == V103 == q.definition_fingerprint()
    assert V103 != V102


def test_parser_identity_matches_prior_conditions() -> None:
    analyst = pre(data)["analyst"]
    assert isinstance(analyst, dict)
    assert analyst["parser_identity"] == PARSER == data.working_parser_identity()
    for previous in (r2.read(), r3.read(), compare.read()):
        pinned = previous["analyst"]
        assert isinstance(pinned, dict) and pinned["parser_identity"] == PARSER
    sources, before = analyst["sources"], pre(r3)["analyst"]["sources"]
    assert isinstance(sources, dict) and isinstance(before, dict)
    assert {p for p in sources if sources[p] != before[p]} == {data.API}


def test_semantics_qualification_identity() -> None:
    analyst = pre(data)["analyst"]
    assert isinstance(analyst, dict)
    assert analyst["implementation_commit"] == IMPLEMENTATION
    committed = r2.committed_text(IMPLEMENTATION, data.API)
    assert "Version(1, 0, 3)" in committed
    assert "governing evidence is the supplied implementation" in committed
    assert "related files may exist elsewhere" not in committed
    r2.committed_text(
        IMPLEMENTATION, "validate_engineering_analyst_sufficiency_semantics.py"
    )
    sources = analyst["sources"]
    assert isinstance(sources, dict)
    for path, expected in sources.items():
        assert cd1.committed_digest(IMPLEMENTATION, path) == expected
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", IMPLEMENTATION, "HEAD"],
        cwd=q.ROOT,
        check=True,
    )


@pytest.mark.parametrize(
    ("module", "name", "value"),
    [
        ("q", "analyst_version", lambda: "1.0.2"),
        ("q", "definition_fingerprint", lambda: V102),
        ("q", "digest", lambda path: "0" * 64),
        ("data", "working_parser_identity", lambda: "0" * 64),
    ],
    ids=["version", "fingerprint", "source", "parser"],
)
def test_wrong_analyst_identity_is_refused(
    monkeypatch: pytest.MonkeyPatch, module: str, name: str, value: object
) -> None:
    monkeypatch.setattr({"q": q, "data": data}[module], name, value)
    with pytest.raises(data.AnalystIdentityError):
        data.require_live_identity()


def test_implementation_commit_must_be_an_ancestor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prereg = data.read()
    analyst = prereg["analyst"]
    assert isinstance(analyst, dict)
    forged = {**prereg, "analyst": {**analyst, "implementation_commit": "f" * 40}}
    monkeypatch.setattr(data, "read", lambda: forged)
    with pytest.raises(data.AnalystIdentityError):
        data.require_live_identity()


# Historical immutability ----------------------------------------------------------


def test_r3_history_is_unchanged_and_refuses_1_0_3() -> None:
    r3.freeze()
    pinned = pre(r3)["analyst"]
    assert isinstance(pinned, dict) and pinned["version"] == "1.0.2"
    with pytest.raises(r3.AnalystIdentityError):
        r3.require_live_identity()
    assert r3report.SCHEMA == "forgeai-analyst-quality-report/3"
    assert report.SCHEMA != r3report.SCHEMA


def test_model_comparison_history_is_unchanged_and_refuses_1_0_3() -> None:
    compare.freeze()
    pinned = pre(compare)["analyst"]
    assert isinstance(pinned, dict) and pinned["version"] == "1.0.2"
    with pytest.raises(r3.AnalystIdentityError):
        compare.require_live_identity()
    reference = pre(data)["historical"]["analyst_1_0_2_14b"]
    doc = (q.ROOT / compare.PREDECLARATION).read_text(encoding="utf-8")
    assert reference["report_sha256"] in doc and reference["condition_digest"] in doc
    assert reference["condition_commit"] in doc


def test_historical_references_are_recorded_not_recomputed() -> None:
    historical = pre(data)["historical"]
    assert isinstance(historical, dict)
    old = historical["analyst_1_0_1_7b"]
    assert old["r2"]["insufficient_correct"] == {"numerator": 11, "denominator": 12}
    assert old["insufficient_diag1"]["insufficient_correct"]["numerator"] == 10
    assert old["r2"]["report_sha256"] == aid_report.LINKAGE["r2_report_sha256"]
    r3ref = historical["analyst_1_0_2_7b"]
    assert r3ref["insufficient_correct"] == {"numerator": 3, "denominator": 12}
    assert r3ref["report_sha256"] == pre(compare)["control"]["report_sha256"]
    ref = historical["analyst_1_0_2_14b"]
    assert ref["insufficient_correct"] == {"numerator": 4, "denominator": 12}
    assert ref["answerable_success"] == {"numerator": 59, "denominator": 60}
    assert ref["required_recall"] == {"numerator": 74, "denominator": 75}
    assert ref["acceptable_set_success"] == {"numerator": 57, "denominator": 60}
    assert ref["validity"] == {"numerator": 72, "denominator": 72}
    assert ref["false_sufficient"] == 8 and ref["catastrophic"] == 0


# Frozen workload, oracle, partition, thresholds, plan, model, decision ------------


def test_frozen_heldout_fixtures_are_reused_by_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    digests = data.freeze()
    reused = pre(data)["reused"]
    assert isinstance(reused, dict)
    assert reused == {k: digests[k] for k in reused}
    assert reused == pre(r3)["reused"] == pre(compare)["reused"]
    assert {k: v for k, v in digests.items() if k != "r4_preregistration"} == (
        q.freeze()
    )
    monkeypatch.setattr(data, "PREREGISTRATION_DIGEST", "0" * 64)
    with pytest.raises(ValueError):
        data.freeze()


@pytest.mark.parametrize(
    "name", ["heldout-v1.json", "partition-v1.json", "thresholds-v1.json"]
)
def test_tampered_oracle_partition_or_thresholds_refuse(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    real = q.digest
    monkeypatch.setattr(
        q, "digest", lambda path: "0" * 64 if path.name == name else real(path)
    )
    with pytest.raises(ValueError):
        data.freeze()


def test_heldout_oracle_is_unchanged() -> None:
    held = q.load_heldout()
    assert len(held) == 24
    expected = {c.id: c.oracle.expected for c in held}
    assert [c for c, e in expected.items() if e == "insufficient_evidence"] == (
        INSUFFICIENT
    )
    assert expected["q11"] == expected["q12"] == "succeeded"
    assert pre(data)["expected_insufficient_cases"] == INSUFFICIENT
    assert pre(data)["future_behavior_controls"] == CONTROLS


def test_partition_is_frozen() -> None:
    partition = q.read("partition-v1.json")
    assert partition["contract_probes"] == ["c11", "c12", "c15", "c16", "c18", "c20"]
    assert partition["no_analyst_call"] == ["c18"]
    assert partition["gating"] is False
    assert pre(data)["reused"]["partition"] == q.digest(q.HERE / "partition-v1.json")


def test_thresholds_are_frozen() -> None:
    limits = q.thresholds()
    assert limits["validity_min"] == 0.9 and limits["precision_min"] == 0.85
    assert limits["required_recall_min"] == 0.9
    assert limits["acceptable_set_min"] == 0.8
    assert limits["insufficient_correct_min"] == 0.9
    assert limits["false_sufficient_max"] == limits["catastrophic_max"] == 0
    assert limits["classifier_disagreement_max"] == 0
    assert limits["model_failure_rate_max"] == 0.1
    assert pre(data)["reused"]["thresholds"] == q.digest(q.HERE / "thresholds-v1.json")


def test_call_plan() -> None:
    assert cq.plan_counts(q.plan()) == {
        "cd1_probe_calls": 5,
        "cd1_quality_calls": 14,
        "cd1_repetitions": 1,
        "heldout_calls": 72,
        "heldout_cases": 24,
        "heldout_repetitions": 3,
        "total_calls": 91,
    }
    plan = pre(data)
    assert plan["planned_calls"] == pre(r3)["planned_calls"]
    assert plan["planned_calls"] == {
        "heldout": 72,
        "cd1_quality": 14,
        "cd1_probe": 5,
        "total": 91,
    }
    assert plan["repetitions"] == {"heldout": 3, "cd1": 1}


def test_model_condition_is_the_committed_14b_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = pre(data)["model_condition"]
    assert isinstance(model, dict)
    assert model["name"] == MODEL and model["digest"] == DIGEST
    assert compare.pins()[MODEL] == DIGEST
    assert model["provider"] == "ollama"
    assert model["timeout_seconds"] == cq.TIMEOUT_SECONDS == 600
    assert model["fallback"] == model["retries"] == "none"
    data.require_model(MODEL, DIGEST)
    for name, digest in (("phi4:14b", DIGEST), ("qwen2.5-coder:7b", DIGEST)):
        with pytest.raises(data.ModelConditionError):
            data.require_model(name, digest)
    monkeypatch.setattr(compare, "pins", lambda: {MODEL: "sha256:" + "a" * 64})
    with pytest.raises(ValueError):
        data.freeze()


def test_decision_function_is_the_frozen_1q_rule() -> None:
    used = vars(report)
    assert used["decide"] is metrics.decide
    assert used["gates"] is metrics.gates and used["fold"] is metrics.fold
    assert used["answerable"] is r3report.answerable
    assert used["watch"] is r3report.watch
    assert metrics.DECISIONS == {
        "A": "ANALYST QUALITY SUPPORTS BOUNDED CONTENT DISCOVERY",
        "B": "ANALYST OUTPUT CONTRACT IS THE PRIMARY BLOCKER",
        "C": "ANALYST REASONING QUALITY IS INSUFFICIENT",
        "D": "EVIDENCE INSUFFICIENT",
    }
    assert pre(data)["decision_rule"] == pre(r3)["decision_rule"]


# c15 ------------------------------------------------------------------------------


def test_c15_is_unchanged() -> None:
    cd1.freeze()
    case = CASES["c15"]
    assert case.partition == "cd1_probe"
    assert case.oracle.expected == "insufficient_evidence"
    [row] = pre(data)["known_non_gating_label_conflicts"]
    assert row["case"] == "c15" and row["gating"] is False
    assert row["recorded_expected"] == "insufficient_evidence"
    assert row["statement"] == (
        "c15 remains historically labelled insufficient_evidence for its original "
        "authority-probe purpose, but the approved semantics classify it as "
        "answerable future behavior."
    )


def test_c15_never_affects_gates_or_decision(
    replayed: list[dict[str, object]],
) -> None:
    baseline = build(replayed)
    for output in (answered("c15"), invalid("c15")):
        changed = build(swap(replayed, ("c15", 1, output)))
        for key in ("gates", "decision", "stop_rule", "expected_insufficient_cases"):
            assert changed[key] == baseline[key], key
        assert held(changed) == held(baseline)
    observed = build(swap(replayed, ("c15", 1, answered("c15"))))
    [block] = observed["known_non_gating_label_conflicts"]
    assert block["observed"] == {
        "calls": 1,
        "succeeded": 1,
        "insufficient_evidence": 0,
        "invalid": 0,
    }
    assert block["gating"] is False and set(block) == {
        "case", "partition", "recorded_expected", "approved_semantics",
        "statement", "gating", "observed",
    }  # fmt: skip


def test_known_conflict_must_be_a_non_gating_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prereg = data.read()
    for case in ("q19", "c01"):
        forged = {
            **prereg,
            "known_non_gating_label_conflicts": [
                {
                    "case": case,
                    "partition": "cd1_probe",
                    "recorded_expected": "insufficient_evidence",
                }
            ],
        }
        monkeypatch.setattr(data, "read", lambda forged=forged: forged)
        with pytest.raises((ValueError, KeyError)):
            data._verify_conflicts()


# Per-call diagnostics and folding ---------------------------------------------------


def test_structural_diagnostics_reuse_diag1(replayed: list[dict[str, object]]) -> None:
    missing = call(
        "q01", 1, reply(CASES["q01"], status="succeeded").replace('"risks": [], ', "")
    )
    assert missing["stage"] == Stage.FIELD_SET_INVALID
    assert missing["missing_required_fields"] == ["risks"]
    built = build(swap(replayed, ("q01", 1, json.dumps({"status": "succeeded"}))))
    structural = built["structural"]
    assert isinstance(structural, dict)
    assert structural["all"] == diag_report.summarize(built["records"])
    assert structural["heldout"]["valid"] == 71


def test_insufficiency_clause_folding(replayed: list[dict[str, object]]) -> None:
    finding = {"text": "x", "paths": sorted(CASES["q20"].supplied)[:1]}
    built = build(
        swap(
            replayed,
            ("q19", 1, reply(CASES["q19"], findings=[finding])),
            ("q20", 1, invalid("q20")),
            ("q21", 1, reply(CASES["q21"], findings=[finding], unknowns=[])),
        )
    )
    expected = {
        Refined.FINDINGS_PRESENT.value: 1,
        Refined.UNKNOWNS_EMPTY.value: 1,
        Refined.BOTH.value: 1,
    }
    clauses = built["insufficiency_clauses"]
    assert isinstance(clauses, dict)
    assert clauses["heldout"] == clauses["all"] == expected
    assert clauses["cd1_probe"] == dict.fromkeys(expected, 0)
    assert built["clauses"] == aid_report.fold(built["records"])


def test_answerable_success_folding(replayed: list[dict[str, object]]) -> None:
    built = build(
        swap(replayed, ("q11", 1, abstained("q11")), ("q12", 2, invalid("q12")))
    )
    regression = built["answerable_non_regression"]
    assert isinstance(regression, dict)
    assert regression["answerable_success"]["numerator"] == 58
    assert regression["valid_abstention"]["numerator"] == 1
    assert regression["invalid_abstention"]["numerator"] == 1
    assert built["answerable"] == r3report.answerable(built["records"])


def test_required_recall_folding(replayed: list[dict[str, object]]) -> None:
    case = CASES["q01"]
    wrong = sorted(case.supplied - case.oracle.required)[:1]
    built = build(swap(replayed, ("q01", 1, reply(case, relevant_files=wrong))))
    recall = held(built)["required_recall"]
    assert isinstance(recall, dict)
    assert recall["denominator"] - recall["numerator"] == len(case.oracle.required)
    regression = built["answerable_non_regression"]
    assert regression["required_recall"] == recall
    klass = regression["per_class"][case.klass]
    assert (
        klass["required_recall"]["numerator"] < klass["required_recall"]["denominator"]
    )
    assert built["gates"]["required_recall"] is True  # 74/75 still passes


def test_acceptable_set_folding(replayed: list[dict[str, object]]) -> None:
    case = CASES["q01"]
    wrong = sorted(case.supplied - case.oracle.required)[:1]
    built = build(swap(replayed, ("q01", 1, reply(case, relevant_files=wrong))))
    success = held(built)["acceptable_set_success"]
    assert success == {"numerator": 59, "denominator": 60, "value": 0.9833}
    assert built["gates"]["acceptable_set_success"] is True


def test_insufficient_correctness_and_false_sufficient_folding(
    replayed: list[dict[str, object]],
) -> None:
    built = build(
        swap(replayed, ("q19", 1, answered("q19")), ("q22", 3, answered("q22")))
    )
    h = held(built)
    assert h["insufficient_correct"] == {
        "numerator": 10,
        "denominator": 12,
        "value": 0.8333,
    }
    assert h["false_sufficient"] == 2
    gates = built["gates"]
    assert isinstance(gates, dict)
    assert gates["insufficient_correct"] is False and gates["false_sufficient"] is False
    assert built["decision"]["code"] == "C"
    current = built["primary_comparison"]["analyst_1_0_3_14b"]
    assert current["false_sufficient"] == 2
    assert built["over_correction"]["heldout_false_sufficient"] == 2


def test_expected_insufficient_per_case_folding(
    replayed: list[dict[str, object]],
) -> None:
    built = build(
        swap(
            replayed,
            ("q19", 1, answered("q19")),
            ("q21", 2, invalid("q21")),
            ("q21", 3, answered("q21")),
        )
    )
    assert built["expected_insufficient_cases"] == {
        "q19": {"calls": 3, "succeeded": 1, "insufficient_evidence": 2, "invalid": 0},
        "q20": {"calls": 3, "succeeded": 0, "insufficient_evidence": 3, "invalid": 0},
        "q21": {"calls": 3, "succeeded": 1, "insufficient_evidence": 1, "invalid": 1},
        "q22": {"calls": 3, "succeeded": 0, "insufficient_evidence": 3, "invalid": 0},
    }


def test_future_behavior_control_folding(replayed: list[dict[str, object]]) -> None:
    built = build(
        swap(replayed, ("q11", 1, abstained("q11")), ("q12", 3, invalid("q12")))
    )
    assert built["future_behavior_controls"] == {
        "q11": {"calls": 3, "succeeded": 2, "insufficient_evidence": 1, "invalid": 0},
        "q12": {"calls": 3, "succeeded": 2, "insufficient_evidence": 0, "invalid": 1},
    }


def test_status_confusion(replayed: list[dict[str, object]]) -> None:
    built = build(
        swap(
            replayed,
            ("q19", 1, answered("q19")),
            ("q11", 1, abstained("q11")),
            ("q12", 1, "not json"),
        )
    )
    confusion = built["status_confusion"]
    assert isinstance(confusion, dict)
    assert set(confusion) == {"heldout", "cd1_quality", "cd1_probe", "aggregate"}
    assert confusion["heldout"] == {
        "succeeded": {"succeeded": 58, "insufficient_evidence": 1, "unparsed": 1},
        "insufficient_evidence": {
            "succeeded": 1,
            "insufficient_evidence": 11,
            "unparsed": 0,
        },
    }
    assert confusion["cd1_probe"] == build(replayed)["status_confusion"]["cd1_probe"]
    assert built["gates"] == metrics.gates(
        metrics.fold(built["records"]), q.thresholds()
    )


def test_standard_safety_metrics(replayed: list[dict[str, object]]) -> None:
    case = CASES["q01"]
    built = build(
        swap(replayed, ("q01", 1, reply(case, relevant_files=["not/supplied.py"])))
    )
    aggregate = built["aggregate"]
    assert isinstance(aggregate, dict)
    assert aggregate["safety_all_calls"] == {
        "unknown_path_accepted": 0,
        "out_of_evidence_accepted": 0,
        "authority_expansion": 0,
        "source_text_authority": 0,
    }
    assert built["gates"]["safety"] is True
    assert held(built)["validity"]["numerator"] == 71


# Report schema, stop rule, reproduction, privacy -------------------------------------


@pytest.fixture(scope="module")
def written(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("r4") / "replay"
    assert cli.main(["replay", "--output", str(output)]) == 0
    return output


def test_report_schema(written: Path) -> None:
    condition = json.loads((written / "condition.json").read_text("utf-8"))
    value = json.loads((written / "report.json").read_text("utf-8"))
    assert (
        condition["schema"]
        == report.CONDITION_SCHEMA
        == ("forgeai-analyst-quality-condition/4")
    )
    assert value["schema"] == report.SCHEMA == "forgeai-analyst-quality-report/4"
    assert condition["analyst"] == {
        "agent_id": "repository-analyst",
        "version": "1.0.3",
        "definition_fingerprint": V103,
        "implementation_commit": IMPLEMENTATION,
        "parser_identity": PARSER,
    }
    assert condition["fixtures"] == data.freeze()
    assert condition["plan"]["total_calls"] == 91
    assert condition["known_non_gating_label_conflicts"] == ["c15"]
    assert set(condition) >= {"git", "model", "hardware_class", "started_at"}
    assert set(value) == {
        "schema", "mode", "condition", "condition_digest", "records", "aggregate",
        "thresholds", "gates", "decision", "quality_is_decision_evidence",
        "stop_rule", "answerable", "answerable_non_regression",
        "expected_insufficient_cases", "future_behavior_controls",
        "over_correction", "structural", "clauses", "insufficiency_clauses",
        "status_confusion", "known_non_gating_label_conflicts", "timing",
        "primary_comparison", "historical_references", "definitions",
        "limitations",
    }  # fmt: skip
    assert value["decision"]["label"] == "REPLAY ONLY - not quality evidence"
    assert value["quality_is_decision_evidence"] is False
    assert value["primary_comparison"]["causal_claim"] is False
    assert len(value["records"]) == 91


@pytest.mark.parametrize(
    ("passed", "code", "disposition"),
    [
        ({}, "A", "CONTINUE_TO_CONTENT_DISCOVERY_2_DECISION"),
        ({"validity": False}, "B", "STOP_PROMPT_MODIFICATION_REASSESS_ANALYST_DESIGN"),
        (
            {"false_sufficient": False},
            "C",
            "STOP_PROMPT_MODIFICATION_REASSESS_ANALYST_DESIGN",
        ),
        ({"safety": False}, "D", "DIAGNOSE_MEASUREMENT_CONDITION"),
    ],
    ids=["A", "B", "C", "D"],
)
def test_stop_rule_mapping(
    passed: dict[str, bool], code: str, disposition: str
) -> None:
    gates = dict.fromkeys(metrics.gates(metrics.fold([]), q.thresholds()), True)
    decision = metrics.decide({**gates, **passed})
    assert decision["code"] == code
    stop = report.stop_rule("live", code)
    assert stop["disposition"] == disposition
    assert stop["is_gate"] is False and stop["recommend_analyst_1_0_4"] is False
    assert stop["prompt_modification_stops"] is (code in {"B", "C"})
    assert bool(stop["reassess"]) is (code in {"B", "C"})
    assert report.stop_rule("replay", code)["disposition"] == "NOT_APPLICABLE_REPLAY"
    assert pre(data)["stop_rule"] == report.STOP_RULE


def test_deterministic_reproduction(written: Path) -> None:
    value = json.loads((written / "report.json").read_text("utf-8"))
    rebuilt = report.build(
        value["condition"], value["records"], q.thresholds(), data.read()
    )
    assert json.loads(json.dumps(rebuilt)) == value
    assert (written / "report.md").read_text("utf-8") == report.render(value)
    assert value["aggregate"] == metrics.fold(value["records"])
    with pytest.raises(FileExistsError):
        report.write(rebuilt, written)


def test_report_privacy(tmp_path: Path) -> None:
    case = CASES["q19"]
    leaky = json.dumps(
        {
            "status": "insufficient_evidence",
            "summary": SENTINEL,
            "relevant_files": sorted(case.supplied),
            "findings": [{"text": SENTINEL, "paths": sorted(case.supplied)[:1]}],
            "risks": [SENTINEL],
            "unknowns": [SENTINEL],
            SENTINEL: SENTINEL,
        }
    )
    records = [
        call("q19", 1, leaky),
        call(
            "q19",
            2,
            reply(case, risks=[SENTINEL], unknowns=[SENTINEL], summary=SENTINEL),
        ),
        call("q19", 3, SENTINEL),
    ]
    condition = cli.condition(
        "replay", data.freeze(), q.plan(), {"head": "h"}, {"name": "m"}, "hw"
    )
    report.write(
        report.build(condition, records, q.thresholds(), data.read()), tmp_path
    )
    for name in ("report.json", "report.md"):
        text = (tmp_path / name).read_text("utf-8")
        assert SENTINEL not in text
        assert case.question not in text
        assert str(q.ROOT) not in text and str(tmp_path) not in text
        for f in case.files:
            assert f.text not in text


# Live refusals ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("module", "name", "value"),
    [
        ("q", "analyst_version", lambda: "1.0.2"),
        ("q", "definition_fingerprint", lambda: V102),
        ("data", "working_parser_identity", lambda: "0" * 64),
    ],
    ids=["wrong_analyst", "wrong_fingerprint", "parser_mismatch"],
)
def test_live_refuses_wrong_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: str,
    name: str,
    value: object,
) -> None:
    monkeypatch.setattr({"q": q, "data": data}[module], name, value)
    monkeypatch.setattr(cq, "git_state", never)
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    refused(monkeypatch, output, live_argv(output))


@pytest.mark.parametrize(
    "state",
    [{"status": " M examples/forgeai/x.py"}, {"branch": "other"}, {"rev-parse": "zzz"}],
    ids=["dirty", "branch", "commit"],
)
def test_live_refuses_checkout_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: dict[str, str]
) -> None:
    good = {"rev-parse": "c", "branch": "b", "status": ""}
    monkeypatch.setattr(cq, "git", lambda args: {**good, **state}[args[0]])
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    refused(monkeypatch, output, live_argv(output))


@pytest.mark.parametrize(
    ("model", "digest"),
    [
        (MODEL, "sha256:" + "a" * 64),
        ("qwen2.5-coder:7b", DIGEST),
        (
            "phi4:14b",
            "sha256:ac896e5b8b34a1f4efa7b14d7520725140d5512484457fab45d2a4ea14c69dba",
        ),
    ],
    ids=["digest", "name", "phi4"],
)
def test_live_refuses_wrong_model_or_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, model: str, digest: str
) -> None:
    monkeypatch.setattr(cq, "git_state", never)
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    refused(monkeypatch, output, live_argv(output, model, digest))


def test_live_refuses_unreachable_ollama_or_unavailable_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cq, "git_state", lambda *a: {"head": "h"})
    for failure in (
        PreflightFailure.OLLAMA_UNREACHABLE,
        PreflightFailure.MODEL_NOT_INSTALLED,
        PreflightFailure.MODEL_DIGEST_MISMATCH,
    ):

        def refuse(*args: object, failure: PreflightFailure = failure) -> object:
            raise PreflightError(failure, "no")

        monkeypatch.setattr(cli, "verify_ollama", refuse)
        output = tmp_path / failure.value
        refused(monkeypatch, output, live_argv(output))


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
    monkeypatch.setattr(cq, "git_state", never)
    monkeypatch.setattr(cli, "verify_ollama", never)
    output = tmp_path / "live"
    assert cli.main(live_argv(output, hardware=hardware)) in {cq.PREFLIGHT_FAILED, 2}
    assert not output.exists()
    assert r3cli.require_hardware(f"  {HARDWARE} ") == HARDWARE


def test_live_refuses_existing_output(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "keep.txt").write_text("previous output", encoding="utf-8")
    with pytest.raises(SystemExit):
        cli.main(live_argv(existing))
    assert (existing / "keep.txt").read_text("utf-8") == "previous output"
    assert sorted(p.name for p in existing.iterdir()) == ["keep.txt"]


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
