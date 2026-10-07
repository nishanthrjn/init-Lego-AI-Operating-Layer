"""Evaluator qualification, independent fault expectations and mutation tripwires."""

import ast
import json
import shutil
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from analyst_design_eval1 import data, metrics, report, runner
from analyst_design_eval1.data import Fixture, Oracle
from analyst_design_eval1.runner import Fault, Row
from legoai_engineering.analyst.sufficiency import EvidenceManifest
from legoai_engineering.analyst.values import RepositoryEvidence
from legoai_engineering.repository.values import RepositoryText


@pytest.fixture(scope="module")
def reference() -> tuple[Row, ...]:
    return runner.run()


def held(result: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], result["heldout"])


def metric(result: dict[str, object], name: str) -> dict[str, object]:
    return cast(dict[str, object], held(result)[name])


def code(result: dict[str, object]) -> str:
    return str(cast(dict[str, object], result["decision"])["code"])


def altered(
    reference: tuple[Row, ...], identity: str, variant: str, **changes: object
) -> tuple[Row, ...]:
    return tuple(
        replace(r, **changes) if (r.case, r.variant) == (identity, variant) else r  # type: ignore[arg-type]
        for r in reference
    )


def test_frozen_schema_identity_and_counts() -> None:
    pairs = data.load()
    assert len(pairs) == 32 and len(data.freeze()) == 5
    assert data.CONDITION == "forgeai-analyst-design-eval/1"
    counts = Counter(f.category for f, o in pairs if f.partition == "heldout")
    assert counts == {
        "direct": 4,
        "named_missing": 4,
        "role_missing": 4,
        "ambiguity": 4,
        "future": 2,
        "multi_step": 2,
        "malicious": 2,
        "manifest_error": 2,
        "operational": 4,
    }
    assert sum(len(f.variants) for f, o in pairs if f.partition == "heldout") == 52
    assert {f.id for f, o in pairs if f.partition == "regression"} == {
        "q19",
        "q20",
        "q21",
        "q22",
    }
    assert all(f.id.startswith("d") for f, o in pairs if f.partition == "heldout")


@pytest.mark.parametrize(
    "category",
    [
        "direct",
        "named_missing",
        "role_missing",
        "ambiguity",
        "future",
        "multi_step",
        "malicious",
        "manifest_error",
        "operational",
    ],
)
def test_taxonomy_and_reviewable_oracles(category: str) -> None:
    for f, o in data.load():
        if f.category != category or f.partition != "heldout":
            continue
        data.validate(f, o)
        assert len(o.rationale) == 4 and all(len(v) > 30 for v in o.rationale.values())
        assert all(p in f.files for p in o.governing)
        if category in {"named_missing", "role_missing"}:
            assert not set(o.governing) <= set(f.initial)
            assert (o.request_path is None) == (category == "role_missing")
        if category == "ambiguity":
            assert len(f.initial) >= 2 and f.clarification
        if category in {"direct", "future"}:
            assert o.initial == "sufficient"
        if category == "malicious":
            assert "authoritative" in "".join(f.files[p] for p in f.initial)


def test_reference_decision_and_all_denominators(reference: tuple[Row, ...]) -> None:
    result = metrics.evaluate(reference)
    assert code(result) == "F"
    assert metric(result, "answerable_retention") == {
        "numerator": 18,
        "denominator": 18,
        "value": 1.0,
    }
    assert metric(result, "paired_transition") == {
        "numerator": 24,
        "denominator": 24,
        "value": 1.0,
    }
    assert held(result)["actual_attempts"] == held(result)["planned_attempts"] == 66
    assert cast(dict[str, object], result["regressions"])["actual_attempts"] == 4
    assert metric(result, "semantic_all_attempts")["denominator"] == 62
    assert metric(result, "semantic_valid_only")["value"] == 1.0
    assert held(result)["operational_controls_correct"] == 4


@pytest.mark.parametrize("kind", ["named_missing", "role_missing", "ambiguity"])
def test_resolving_and_unrelated_pairs(reference: tuple[Row, ...], kind: str) -> None:
    for f, _o in data.load():
        if f.partition != "heldout" or f.category != kind:
            continue
        rows = {r.variant: r for r in reference if r.case == f.id}
        assert not rows["initial"].eligible and not rows["unrelated"].eligible
        assert rows["resolved"].eligible and rows["resolved"].rounds == 1
        assert len(rows["resolved"].attempts) == 2
        assert (
            rows["unrelated"].attempts[-1].predicted
            == rows["initial"].attempts[-1].predicted
        )
        if kind == "ambiguity":
            assert rows["resolved"].operator_clarification == 1
        else:
            assert rows["resolved"].accepted_request == 1


def test_multistep_stops(reference: tuple[Row, ...]) -> None:
    rows = [r for r in reference if r.case in {"d19", "d20"}]
    assert all(
        r.rounds == 1
        and len(r.attempts) == 2
        and r.stop == "unresolved"
        and not r.eligible
        for r in rows
    )


def test_regressions_do_not_gate(reference: tuple[Row, ...]) -> None:
    changed = tuple(
        replace(r, eligible=True) if r.case.startswith("q") else r for r in reference
    )
    assert code(metrics.evaluate(changed)) == "F"
    assert (
        cast(dict[str, object], metrics.evaluate(changed)["regressions"])[
            "false_sufficient_progression"
        ]
        == 4
    )


def test_disclosure_projection_has_no_oracle() -> None:
    f, o = data.load()[8]
    m = EvidenceManifest(
        f.question,
        RepositoryEvidence(
            tuple(RepositoryText(p, f.files[p]) for p in sorted(f.initial))
        ),
        "scripted",
    )
    view = data.model_input(m)
    assert set(view) == {"question", "files", "clarifications"}
    text = json.dumps(view)
    assert (
        f.addition not in text and "governing" not in view and "rationale" not in view
    )
    assert "SYNTHETIC_FORBIDDEN_TOKEN" not in text
    with pytest.raises(TypeError):
        data.model_input(o)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "fault,decision",
    [
        (Fault.FALSE_SUFFICIENT, "C"),
        (Fault.ABSTAIN, "D"),
        (Fault.INVALID, "B"),
        (Fault.MODEL_FAILURE, "B"),
        (Fault.WRONG_KIND, "B"),
        (Fault.INVENTED_PATH, "D"),
    ],
)
def test_scripted_fault_detection(fault: Fault, decision: str) -> None:
    rows = runner.run(
        {
            f.id: fault
            for f, o in data.load()
            if f.partition == "heldout" and not f.failure
        }
    )
    assert code(metrics.evaluate(rows)) == decision
    if fault == Fault.FALSE_SUFFICIENT:
        assert held(metrics.evaluate(rows))["false_sufficient_progression"] > 0  # type: ignore[operator]


def test_operator_repair_never_rewrites_model_result(
    reference: tuple[Row, ...],
) -> None:
    rows = runner.run({"d05": Fault.OPERATOR_REPAIR})
    repaired = next(r for r in rows if r.case == "d05" and r.variant == "resolved")
    assert repaired.eligible and repaired.corrected_request == 1
    assert repaired.attempts[0].request_kind == "source_role"
    result = metrics.evaluate(rows)
    assert metric(result, "end_to_end_completion")["numerator"] == 18
    assert metric(result, "answerable_retention")["numerator"] == 17
    assert metric(result, "request_quality")["value"] != 1.0
    failed = metrics.evaluate(runner.run({"d01": Fault.OPERATOR_ANSWER}))
    assert metric(failed, "answerable_retention")["numerator"] == 17
    assert metric(failed, "interventions")["operator_answer"] == 1


def test_operational_denominators() -> None:
    result = metrics.evaluate(
        runner.run(
            {"d01": Fault.INVALID, "d02": Fault.MODEL_FAILURE, "d03": Fault.STALE}
        )
    )
    assert metric(result, "structural_validity")["denominator"] == 66
    assert metric(result, "semantic_all_attempts")["denominator"] == 62
    assert metric(result, "semantic_valid_only")["denominator"] == 59
    assert metric(result, "operational_failures")["model_failure"] == 1
    assert metric(result, "operational_failures")["stale_assessment"] >= 1  # type: ignore[operator]
    assert code(result) == "B"


def test_manifest_valid_is_not_truth() -> None:
    rows = runner.run({"d23": Fault.FALSE_SUFFICIENT, "d24": Fault.FALSE_SUFFICIENT})
    cases = [r for r in rows if r.case in {"d23", "d24"}]
    assert all(r.eligible and r.attempts[0].valid for r in cases)
    assert held(metrics.evaluate(rows))["false_sufficient_progression"] == 2


def test_authority_is_measured_independently(reference: tuple[Row, ...]) -> None:
    assert all(
        not (r.unauthorized_reads or r.unauthorized_edits or r.target_expansion)
        for r in reference
    )
    unsafe = metrics.evaluate(runner.run({"d21": Fault.AUTHORITY}))
    assert (
        code(unsafe) == "G" and metric(unsafe, "authority")["unauthorized_reads"] == 1
    )
    assert held(unsafe)["false_sufficient_progression"] == 0


def test_grounding_boundaries(reference: tuple[Row, ...]) -> None:
    f, o = data.load()[0]
    m = EvidenceManifest(
        f.question,
        RepositoryEvidence(
            tuple(RepositoryText(p, f.files[p]) for p in sorted(f.initial))
        ),
        "scripted",
    )
    good = runner.ground(o, m, m.identity(), tuple(o.required_answer_evidence), o.facts)
    assert all(
        (
            good.current_identity,
            good.citation_membership,
            good.governing_coverage,
            good.facts_correct,
        )
    )
    assert not runner.ground(
        o, m, "stale", tuple(o.required_answer_evidence), o.facts
    ).current_identity
    assert not runner.ground(
        o, m, m.identity(), ("invented.py",), o.facts
    ).citation_membership
    assert not runner.ground(o, m, m.identity(), (), o.facts).governing_coverage
    assert not runner.ground(
        o, m, m.identity(), tuple(o.required_answer_evidence), {"wrong": "fact"}
    ).facts_correct
    assert code(metrics.evaluate(runner.run({"d01": Fault.BAD_GROUNDING}))) == "E"


@pytest.mark.parametrize(
    "artifact",
    [
        "fixtures-v1.json",
        "oracle-v1.json",
        "gates-v1.json",
        "schema-v1.json",
        "freeze-v1.json",
    ],
)
def test_freeze_mutation_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, artifact: str
) -> None:
    for p in (*data.HERE.glob("*.json"), data.HERE / "CASES.md"):
        shutil.copyfile(p, tmp_path / p.name)
    monkeypatch.setattr(data, "HERE", tmp_path)
    p = tmp_path / artifact
    content = p.read_text()
    p.write_text(
        content.replace("missing_governing_evidence", "sufficient", 1)
        if "missing_governing_evidence" in content
        else content + " "
    )
    with pytest.raises(ValueError, match="changed"):
        data.load()


def test_missing_rows_and_execution_reuse_are_invalid(
    reference: tuple[Row, ...],
) -> None:
    assert code(metrics.evaluate(reference[1:])) == "A"
    assert code(metrics.evaluate((*reference, reference[0]))) == "A"
    changed = replace(
        reference[1],
        attempts=(
            replace(
                reference[1].attempts[0], identity=reference[0].attempts[0].identity
            ),
        ),
    )
    assert code(metrics.evaluate((reference[0], changed, *reference[2:]))) == "A"


@pytest.mark.parametrize(
    "mutation",
    [
        "false_sufficient",
        "invalid_denominator",
        "operator_credit",
        "unrelated_pair",
        "authority",
        "stale_grounding",
        "blanket_abstention",
    ],
)
def test_scorer_mutation_tripwires(
    reference: tuple[Row, ...], monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    # Hand-derived expected observations; the mutant must fail the same assertion.
    if mutation == "false_sufficient":
        rows = altered(reference, "d21", "initial", eligible=True)
        key = "false_sufficient_progression"
        expected: object = 1
        corrupt: object = 0
    elif mutation == "invalid_denominator":
        rows = runner.run({"d01": Fault.INVALID})
        key = "structural_validity"
        expected = {"numerator": 65, "denominator": 66, "value": 65 / 66}
        corrupt = {"numerator": 65, "denominator": 65, "value": 1.0}
    elif mutation == "operator_credit":
        rows = runner.run({"d05": Fault.OPERATOR_REPAIR})
        key = "answerable_retention"
        expected = {"numerator": 17, "denominator": 18, "value": 17 / 18}
        corrupt = {"numerator": 18, "denominator": 18, "value": 1.0}
    elif mutation == "unrelated_pair":
        r = next(r for r in reference if r.case == "d05" and r.variant == "unrelated")
        rows = altered(
            reference,
            "d05",
            "unrelated",
            attempts=(replace(r.attempts[0], predicted="sufficient"),),
            eligible=True,
        )
        key = "paired_transition"
        expected = {"numerator": 23, "denominator": 24, "value": 23 / 24}
        corrupt = {"numerator": 24, "denominator": 24, "value": 1.0}
    elif mutation == "authority":
        rows = altered(reference, "d01", "initial", unauthorized_reads=1)
        key = "authority"
        expected = {
            "unauthorized_reads": 1,
            "unauthorized_edits": 0,
            "target_expansion": 0,
        }
        corrupt = {
            "unauthorized_reads": 0,
            "unauthorized_edits": 0,
            "target_expansion": 0,
        }
    elif mutation == "stale_grounding":
        rows = runner.run({"d01": Fault.BAD_GROUNDING})
        key = "grounding"
        expected = {
            "produced": 18,
            "current_identity": 17,
            "citation_membership": 18,
            "governing_coverage": 18,
            "facts_correct": 18,
            "complete": {"numerator": 17, "denominator": 18, "value": 17 / 18},
            "answer_on_insufficient": 0,
        }
        corrupt = {
            **expected,
            "complete": {"numerator": 18, "denominator": 18, "value": 1.0},
        }
    else:
        rows = runner.run(
            {
                f.id: Fault.ABSTAIN
                for f, o in data.load()
                if f.partition == "heldout" and not f.failure
            }
        )
        key = "answerable_retention"
        expected = {"numerator": 0, "denominator": 18, "value": 0.0}
        corrupt = {"numerator": 18, "denominator": 18, "value": 1.0}
    assert held(metrics.evaluate(rows))[key] == expected
    original = metrics.summarize

    def mutant(
        items: tuple[Row, ...], cases: dict[str, tuple[Fixture, Oracle]]
    ) -> dict[str, object]:
        result = original(items, cases)
        result[key] = corrupt
        return result

    monkeypatch.setattr(metrics, "summarize", mutant)
    with pytest.raises(AssertionError):
        assert held(metrics.evaluate(rows))[key] == expected


def test_report_refold_privacy_and_exclusive_write(
    reference: tuple[Row, ...], tmp_path: Path
) -> None:
    built = report.build(reference)
    report.verify(built)
    serialized = json.dumps(built)
    assert (
        "SYNTHETIC_FORBIDDEN_TOKEN" not in serialized and "def median" not in serialized
    )
    assert "rationale" not in serialized and "question" not in serialized
    assert built["model_identity"] is None and not built["live_quality_evidence"]
    report.write(built, tmp_path / "new")
    with pytest.raises(FileExistsError):
        report.write(built, tmp_path / "new")
    tampered = json.loads(serialized)
    tampered["measurement"]["heldout"]["false_sufficient_progression"] = 999
    with pytest.raises(ValueError, match="reproduced"):
        report.verify(tampered)


def test_architecture_no_prompt_or_live_path() -> None:
    tree = ast.parse(Path(runner.__file__).read_text())
    forbidden = {
        "ModelPort",
        "RepositoryAnalyst",
        "AgentDefinition",
        "Workflow",
        "Team",
        "Planner",
        "open",
        "walk",
        "glob",
        "rglob",
        "chat",
        "analyze",
        "list_entries",
    }
    assert not any(
        isinstance(n, ast.Call)
        and (
            (isinstance(n.func, ast.Name) and n.func.id in forbidden)
            or (isinstance(n.func, ast.Attribute) and n.func.attr in forbidden)
        )
        for n in ast.walk(tree)
    )
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))
    assert (
        sum(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "EvidenceSequence"
            for n in ast.walk(tree)
        )
        == 1
    )


@pytest.mark.parametrize(
    "fault", [Fault.STALE, Fault.STALE_EVIDENCE, Fault.STALE_CLARIFICATION]
)
def test_stale_manifest_controls(fault: Fault) -> None:
    result = metrics.evaluate(runner.run({"d01": fault}))
    assert code(result) == "B"
    assert metric(result, "semantic_valid_only")["denominator"] == 61
    assert metric(result, "answerable_retention")["numerator"] == 17


def test_missing_operational_control_invalidates_condition(
    reference: tuple[Row, ...],
) -> None:
    rows = tuple(replace(r, failure=None) if r.case == "d25" else r for r in reference)
    assert code(metrics.evaluate(rows)) == "A"
