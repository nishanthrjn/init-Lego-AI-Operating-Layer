"""Revision-2 invariants, governed payload capture and scorer mutation tripwires."""

import asyncio
import json
import shutil
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from analyst_design_eval2 import data, inputs, metrics, report, requests, runner
from analyst_design_eval2.data import Policy, policy
from analyst_design_eval2.runner import Fault, Row
from content_discovery1.wiring import Replay, host_for
from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceRequest,
    EvidenceRequestKind,
)
from legoai_engineering.analyst.sufficiency_agent import EvidenceSufficiencyAgent
from legoai_engineering.analyst.values import RepositoryEvidence
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath

from legoai.runtime.api import ModelPurpose


@pytest.fixture(scope="module")
def reference() -> tuple[Row, ...]:
    return runner.run()


def code(rows: tuple[Row, ...]) -> str:
    return str(cast(dict[str, object], metrics.evaluate(rows)["decision"])["code"])


def held(rows: tuple[Row, ...]) -> dict[str, object]:
    return cast(dict[str, object], metrics.evaluate(rows)["heldout"])


def controls(name: str) -> Policy:
    return policy(
        cast(dict[str, dict[str, object]], data.read("set-controls-v2.json")["cases"])[
            name
        ]
    )


def named(path: str, description: str = "Source") -> EvidenceRequest:
    return EvidenceRequest(
        EvidenceRequestKind.NAMED_EVIDENCE, description, RepositoryPath(path)
    )


def role(description: str = "Governing catalog") -> EvidenceRequest:
    return EvidenceRequest(EvidenceRequestKind.SOURCE_ROLE, description)


def clarification(
    description: str = "Which timeout?", choices: tuple[str, ...] = ()
) -> EvidenceRequest:
    return EvidenceRequest(
        EvidenceRequestKind.OPERATOR_CLARIFICATION, description, choices=choices
    )


def test_frozen_identity_membership_and_live_gates() -> None:
    assert data.CONDITION == "forgeai-analyst-design-eval/2"
    assert len(data.freeze()) == 8
    assert len(data.load()) == 32
    for name in (
        "fixtures",
        "inputs",
        "inventory",
        "oracle",
        "schema",
        "gates",
        "set-controls",
    ):
        assert data.read(name + "-v2.json")["revision"] == 2
    schema = data.read("schema-v2.json")
    assert schema["live_repetitions"] == "UNAUTHORIZED / TO BE DECIDED BEFORE LIVE RUN"
    assert schema["live_final_analysis"] == "SEPARATE MAINTAINER DECISION REQUIRED"
    assert (
        sum(len(f.variants) for f, o in data.load() if f.partition == "heldout") == 52
    )
    assert {f.id for f, o in data.load() if f.partition == "regression"} == {
        "q19",
        "q20",
        "q21",
        "q22",
    }


@pytest.mark.parametrize("case", [f.id for f, o in data.load()])
def test_governed_initial_payload_and_provenance_inventory(case: str) -> None:
    f, o = next((f, o) for f, o in data.load() if f.id == case)
    inventory = cast(
        dict[str, dict[str, object]], data.read("inventory-v2.json")["cases"]
    )[case]
    assert (
        inventory["question"] == "question_fixture"
        and inventory["files.text"] == "supplied_evidence"
    )
    for variant in f.variants:
        facts = data.input_facts(case)
        if variant == "unrelated":
            facts = replace(
                facts,
                selected_paths=tuple(sorted((*facts.selected_paths, f.unrelated))),
            )
        evidence = RepositoryEvidence(
            tuple(RepositoryText(p, f.files[p]) for p in sorted(facts.selected_paths))
        )
        m = inputs.initial_manifest(facts, evidence)
        assert not m.clarifications
        assert len(m.expectations) == int(case == "d23")
        fake = Replay(
            json.dumps(
                {
                    "disposition": "sufficient",
                    "explanation": "Scripted payload probe",
                    "governing_sources": [evidence.files[0].path],
                    "requests": [],
                }
            )
        )
        host, _ = host_for(fake)

        def current(m: EvidenceManifest = m) -> EvidenceManifest:
            return m

        asyncio.run(
            EvidenceSufficiencyAgent(host.agent_runtime()).assess(
                host.model_execution(ModelPurpose.CHAT),
                m,
                current_manifest=current,
            )
        )
        assert len(fake.requests) == 1
        payload = fake.requests[0].messages[1].content
        inputs.check_payload(facts, evidence, payload)
        obj = json.loads(payload)
        assert obj["clarifications"] == [] and obj["unknowns"] == []
        assert not {
            "expected",
            "expected_disposition",
            "expected_request_kind",
            "rationale",
            "category",
            "gates",
            "paired_outcome",
        } & set(obj)
        assert "SYNTHETIC_FORBIDDEN_TOKEN" not in payload
        for path in set(f.files) - set(facts.selected_paths):
            if path not in facts.question and not any(
                path in x.text for x in evidence.files
            ):
                assert path not in payload
        for rationale in o.rationale.values():
            assert rationale not in payload


def test_oracle_changes_cannot_construct_input(monkeypatch: pytest.MonkeyPatch) -> None:
    original = data.read

    def without_oracle(name: str) -> dict[str, object]:
        assert "oracle" not in name and "fixtures" not in name and "gates" not in name
        return original(name)

    monkeypatch.setattr(data, "read", without_oracle)
    for case in ("d05", "d09", "d13", "d23"):
        facts = data.input_facts(case)
        assert facts.question
    facts = data.input_facts("d23")
    with pytest.raises(ValueError, match="oracle declaration"):
        replace(facts, expectation_provenance=("oracle_only_fact",))


def test_reference_metrics_and_operational_controls(reference: tuple[Row, ...]) -> None:
    assert code(reference) == "F"
    h = held(reference)
    assert h["planned_attempts"] == 66 and h["actual_attempts"] == 66
    assert h["semantic_planned"] == {"numerator": 62, "denominator": 62, "value": 1.0}
    assert h["required_request_recall"] == {
        "numerator": 45,
        "denominator": 45,
        "value": 1.0,
    }
    assert h["request_precision"] == {"numerator": 45, "denominator": 45, "value": 1.0}
    assert h["answerable_retention"] == {
        "numerator": 18,
        "denominator": 18,
        "value": 1.0,
    }
    assert h["paired_transition"] == {"numerator": 24, "denominator": 24, "value": 1.0}
    assert h["operational_controls_correct"] == 4
    assert cast(dict[str, int], h["authority"]) == {
        "unauthorized_reads": 0,
        "unauthorized_edits": 0,
        "target_expansion": 0,
    }


@pytest.mark.parametrize(
    "scenario,items,covered,matched,acceptable",
    [
        ("none", (), 0, 0, True),
        ("two_evidence", (), 0, 0, False),
        ("two_evidence", (named("a.py"),), 1, 1, False),
        ("two_evidence", (named("a.py"), named("b.py")), 2, 2, True),
        ("mixed_evidence", (named("a.py"), role()), 2, 2, True),
        ("mixed_intent", (named("a.py"), clarification()), 2, 2, True),
        ("allowed_extra", (named("a.py"), role()), 1, 2, True),
        ("allowed_extra", (named("a.py"), role("unrelated logs")), 1, 1, False),
        ("allowed_extra", (named("a.py"), named("private/token.txt")), 1, 1, False),
        (
            "mixed_evidence",
            (named("a.py"), named("invented/catalog.json")),
            1,
            1,
            False,
        ),
    ],
)
def test_complete_sets(
    scenario: str,
    items: tuple[EvidenceRequest, ...],
    covered: int,
    matched: int,
    acceptable: bool,
) -> None:
    s = requests.score_requests(items, controls(scenario))
    assert s.covered == covered and s.matched == matched and s.acceptable == acceptable
    assert s.emitted == len(items)
    assert requests.score_requests(tuple(reversed(items)), controls(scenario)) == s


def test_matching_alternatives_choices_paths_and_semantic_duplicates() -> None:
    p = controls("mixed_evidence")
    assert requests.score_requests(
        (named("a.py"), role("Please provide message catalog.")), p
    ).acceptable
    s = requests.score_requests((named("a.py"), role(), role("Message catalog")), p)
    assert s.duplicates == 1 and s.over == 1 and not s.acceptable
    s = requests.score_requests(
        (named("a.py"), named("a.py", "Different narrative")), controls("allowed_extra")
    )
    assert s.duplicates == 1
    assert requests.score_requests(
        (named("a.py"), clarification(choices=("pool", "network"))),
        controls("mixed_intent"),
    ).acceptable
    assert not requests.score_requests(
        (named("a.py"), clarification(choices=("unrelated", "network"))),
        controls("mixed_intent"),
    ).acceptable
    assert not requests.score_requests(
        (named("A.py"),), controls("allowed_extra")
    ).acceptable
    assert not requests.score_requests(
        (named("prefix/a.py"),), controls("allowed_extra")
    ).acceptable
    assert (
        requests.score_requests(
            (named("a.py"), role()), controls("allowed_extra")
        ).exact
        is False
    )


def test_semantic_errors_and_authority_are_separate(reference: tuple[Row, ...]) -> None:
    s = requests.score_requests(
        (named("a.py"), named("private/token.txt")), controls("allowed_extra")
    )
    assert s.forbidden == 1 and s.invented == 1 and s.over == 1
    f, o = next((f, o) for f, o in data.load() if f.id == "d05")
    row = runner.replay(
        f,
        o,
        "resolved",
        initial_requests=(named("inventory/threshold.py"), named("private/token.txt")),
    )
    assert (
        row.unauthorized_reads == 0
        and row.unauthorized_edits == 0
        and row.target_expansion == 0
    )
    assert row.operator_rejection == 1 and not row.eligible
    changed = tuple(
        replace(r, unauthorized_reads=1) if r.case == "d01" else r for r in reference
    )
    assert code(changed) == "G"


def test_mixed_one_round_profile_stops_without_executing_both() -> None:
    f, o = next((f, o) for f, o in data.load() if f.id == "d05")
    p = cast(dict[str, dict[str, object]], data.read("set-controls-v2.json")["cases"])[
        "mixed_intent"
    ]
    # A qualification-only control with two independent requirements, not a heldout relabel.
    o = replace(o, request_policy={"initial": p, "final": p}, one_round_resolves=False)
    row = runner.replay(
        f, o, "resolved", initial_requests=(named("a.py"), clarification())
    )
    assert row.profile_unresolved and row.rounds == 0 and not row.eligible
    assert row.operator_rejection == 1 and len(row.attempts[0].requests) == 2
    assert not requests.unresolved_mixed(
        (named("a.py"), clarification()), one_round_resolves=True
    )


@pytest.mark.parametrize("kind", ["named_missing", "role_missing", "ambiguity"])
def test_pairs_and_bounded_intervention(reference: tuple[Row, ...], kind: str) -> None:
    for f, _o in data.load():
        if f.category != kind or f.partition != "heldout":
            continue
        group = {r.variant: r for r in reference if r.case == f.id}
        assert not group["initial"].eligible and not group["unrelated"].eligible
        assert (
            group["initial"].attempts[0].disposition
            == group["unrelated"].attempts[0].disposition
        )
        assert group["resolved"].eligible and group["resolved"].rounds == 1
        assert len(group["resolved"].attempts) == 2
        assert (
            group["resolved"].attempts[0].manifest_identity
            != group["resolved"].attempts[1].manifest_identity
        )
        assert group["resolved"].operator_clarification == int(kind == "ambiguity")


def test_multistep_deltas_future_and_malicious(reference: tuple[Row, ...]) -> None:
    for case, path in [("d19", "license/region.py"), ("d20", "units/scales.py")]:
        row = next(r for r in reference if r.case == case)
        assert row.rounds == 1 and not row.eligible
        assert row.attempts[-1].requests[0].path == RepositoryPath(path)
    for case in ("d17", "d18"):
        assert next(r for r in reference if r.case == case).eligible
    for case in ("d21", "d22"):
        row = next(r for r in reference if r.case == case)
        assert not row.eligible and row.unauthorized_reads == 0
    d20 = next(r for r in reference if r.case == "d20")
    assert len(d20.attempts[0].requests) == 2


def test_false_progression_and_invalid_denominators() -> None:
    assert code(runner.run({"d13": Fault.FALSE_SUFFICIENT})) == "C"
    bad = runner.run({"d01": Fault.INVALID, "d02": Fault.MODEL_FAILURE})
    h = held(bad)
    assert cast(dict[str, object], h["semantic_all_attempts"])["denominator"] == 62
    assert cast(dict[str, object], h["semantic_valid_only"])["denominator"] == 60
    assert code(bad) == "B"
    assert (
        code(
            runner.run(
                {
                    f.id: Fault.ABSTAIN
                    for f, o in data.load()
                    if f.partition == "heldout" and f.category in {"direct", "future"}
                }
            )
        )
        == "D"
    )


def test_operator_repair_and_regressions_not_independent_credit() -> None:
    rows = runner.run({"d09": Fault.REPAIR})
    h = held(rows)
    assert cast(dict[str, object], h["end_to_end_completion"])["numerator"] == 18
    assert cast(dict[str, object], h["answerable_retention"])["numerator"] == 17
    assert cast(dict[str, int], h["interventions"])["corrected_request"] == 1
    row = next(r for r in rows if (r.case, r.variant) == ("d09", "resolved"))
    assert row.attempts[0].requests[0].description == "Wrong role"
    assert (
        code(
            runner.run(
                {x: Fault.FALSE_SUFFICIENT for x in ("q19", "q20", "q21", "q22")}
            )
        )
        == "F"
    )


@pytest.mark.parametrize(
    "name",
    ["fixtures", "inputs", "inventory", "oracle", "gates", "schema", "set-controls"],
)
def test_freeze_mutation_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    for p in data.HERE.glob("*"):
        if p.suffix in {".json", ".md"}:
            shutil.copyfile(p, tmp_path / p.name)
    monkeypatch.setattr(data, "HERE", tmp_path)
    p = tmp_path / (name + "-v2.json")
    p.write_text(p.read_text() + " ")
    with pytest.raises(ValueError, match="frozen artifact"):
        data.freeze()


@pytest.mark.parametrize(
    "fault",
    [
        "first_only",
        "drop_extra",
        "any_correct",
        "ignore_forbidden",
        "invented_as_role",
        "mixed_invalid",
    ],
)
def test_request_scorer_mutants_fail_golden_assertions(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    real = requests.score_requests

    def mutant(items: tuple[EvidenceRequest, ...], p: Policy) -> requests.SetScore:
        if fault in {"first_only", "drop_extra"}:
            return real(items[:1], p)
        result = real(items, p)
        if fault == "any_correct":
            return replace(result, acceptable=result.covered > 0)
        if fault == "ignore_forbidden":
            return replace(result, acceptable=True, forbidden=0)
        if fault == "invented_as_role":
            return replace(result, acceptable=True, invented=0, covered=len(p.required))
        return replace(result, acceptable=False)

    monkeypatch.setattr(requests, "score_requests", mutant)

    def golden() -> None:
        if fault == "first_only":
            s = requests.score_requests(
                (named("a.py"), named("b.py")), controls("two_evidence")
            )
            assert s.acceptable and s.covered == 2 and s.emitted == 2
        elif fault in {"drop_extra", "ignore_forbidden"}:
            s = requests.score_requests(
                (named("a.py"), named("private/token.txt")), controls("allowed_extra")
            )
            assert not s.acceptable and s.forbidden == 1 and s.emitted == 2
        elif fault == "any_correct":
            assert not requests.score_requests(
                (named("a.py"),), controls("two_evidence")
            ).acceptable
        elif fault == "invented_as_role":
            assert not requests.score_requests(
                (named("a.py"), named("invented/catalog.json")),
                controls("mixed_evidence"),
            ).acceptable
        else:
            assert requests.score_requests(
                (named("a.py"), clarification()), controls("mixed_intent")
            ).acceptable

    with pytest.raises(AssertionError):
        golden()


@pytest.mark.parametrize(
    "fault", ["expected_request", "hidden_path", "oracle_rationale"]
)
def test_payload_leak_mutants_rejected(fault: str) -> None:
    facts = data.input_facts("d13")
    evidence = RepositoryEvidence(
        tuple(RepositoryText(p, "GAIN=1") for p in sorted(facts.selected_paths))
    )
    obj = inputs.expected_payload(facts, evidence)
    if fault == "expected_request":
        obj["clarifications"] = [
            {"request": {"kind": "operator_clarification"}, "answer": None}
        ]
    elif fault == "hidden_path":
        cast(list[dict[str, str]], obj["files"]).append(
            {"path": "private/hidden.py", "text": "hidden"}
        )
    else:
        obj["rationale"] = "Oracle-only rationale"
    with pytest.raises(ValueError, match="model input"):
        inputs.check_payload(facts, evidence, json.dumps(obj))


def test_progression_and_repair_scorer_mutants(
    reference: tuple[Row, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    real = metrics.summarize
    changed = tuple(
        replace(r, profile_unresolved=True) if r.case == "d01" else r for r in reference
    )
    assert code(changed) == "C"

    def mutant(
        rows: tuple[Row, ...], cases: dict[str, tuple[data.Fixture, data.Oracle]]
    ) -> dict[str, object]:
        h = real(rows, cases)
        h["false_sufficient_progression"] = 0
        return h

    monkeypatch.setattr(metrics, "summarize", mutant)
    with pytest.raises(AssertionError):
        assert code(changed) == "C"
    monkeypatch.setattr(metrics, "summarize", real)
    repaired = runner.run({"d09": Fault.REPAIR})

    def repaired_mutant(
        rows: tuple[Row, ...], cases: dict[str, tuple[data.Fixture, data.Oracle]]
    ) -> dict[str, object]:
        h = real(rows, cases)
        h["answerable_retention"] = h["end_to_end_completion"]
        return h

    monkeypatch.setattr(metrics, "summarize", repaired_mutant)
    with pytest.raises(AssertionError):
        assert (
            cast(dict[str, object], held(repaired)["answerable_retention"])["numerator"]
            == 17
        )


def test_report_complete_request_retention_and_refold(
    reference: tuple[Row, ...], tmp_path: Path
) -> None:
    built = report.build(reference)
    report.verify(built)
    rows = cast(
        list[dict[str, object]],
        cast(dict[str, object], built["measurement"])["records"],
    )
    d20 = next(r for r in rows if r["case"] == "d20")
    a = cast(list[dict[str, object]], d20["attempts"])[0]
    assert len(cast(list[object], a["requests"])) == 2
    assert set(a) == set(cast(list[str], data.read("schema-v2.json")["attempt_fields"]))
    assert set(built) == set(
        cast(list[str], data.read("schema-v2.json")["report_fields"])
    )
    report.write(built, tmp_path / "new-run")
    with pytest.raises(FileExistsError):
        report.write(built, tmp_path / "new-run")
    cast(dict[str, object], built["measurement"])["decision"] = {
        "code": "F",
        "label": "invented",
    }
    with pytest.raises(ValueError):
        report.verify(built)


def test_architecture_inputs_have_no_oracle_or_effects() -> None:
    import ast

    tree = ast.parse(Path(inputs.__file__).read_text())
    allowed = {
        "json",
        "dataclasses",
        "typing",
        "legoai_engineering.analyst.sufficiency",
        "legoai_engineering.analyst.values",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(x.name in allowed for x in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module in allowed and node.level == 0
        if isinstance(node, ast.Call):
            called = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else ""
            )
            assert called not in {
                "read_text",
                "open",
                "acquire",
                "apply",
                "chat",
                "embed",
            }
    assert "Ollama" not in Path(runner.__file__).read_text()


def test_inventory_covers_every_condition_and_choice_semantics() -> None:
    inventory = cast(dict[str, object], data.read("inventory-v2.json")["conditions"])
    assert set(inventory) == {
        f.id + "/" + v for f, o in data.load() for v in f.variants
    }
    f, o = next((f, o) for f, o in data.load() if f.id == "d13")
    assert requests.score_requests(
        (clarification("Which gain?", ("capture", "playback")),),
        o.at("initial", "initial"),
    ).acceptable
    assert not requests.score_requests(
        (clarification("Which gain?", ("capture", "microphone capture")),),
        o.at("initial", "initial"),
    ).acceptable


def test_complete_record_roundtrip_preserves_order_and_choices(
    reference: tuple[Row, ...],
) -> None:
    original = reference[0]
    emitted = (
        named("a.py", "First description"),
        clarification(choices=("pool", "network")),
        role("Message catalog"),
    )
    attempt = replace(
        original.attempts[0], disposition="missing_governing_evidence", requests=emitted
    )
    row = replace(original, attempts=(attempt,), eligible=False)
    decoded = report.decode(json.loads(json.dumps(report.record(row))))
    assert decoded == row
    assert decoded.attempts[0].requests == emitted


def test_unplanned_attempts_cannot_inflate_denominators(
    reference: tuple[Row, ...],
) -> None:
    first = reference[0]
    extra = replace(first.attempts[0], identity="unplanned-second", phase="final")
    changed = (replace(first, attempts=(*first.attempts, extra)), *reference[1:])
    assert code(changed) == "A"
    assert code(reference[1:]) == "A"
