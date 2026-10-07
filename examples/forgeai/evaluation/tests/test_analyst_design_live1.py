"""Offline live-harness qualification: no Ollama, no final analysis."""

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
from analyst_design_eval2 import data, metrics, runner
from analyst_design_eval2.inputs import initial_manifest
from analyst_design_live1 import harness, identity, measurement, runtime, sequence
from analyst_design_live1.storage import Store
from forgeai_eval.preflight import ServingIdentity
from legoai_engineering.analyst.sufficiency import (
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyResult,
    SufficiencyDisposition,
)
from legoai_engineering.analyst.values import RepositoryEvidence
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath


@pytest.fixture(scope="module")
def reference() -> tuple[runner.Row, ...]:
    return runner.run()


def manifest(case: str = "d01") -> tuple[Any, Any]:
    f, _ = next((f, o) for f, o in data.load() if f.id == case)
    facts = data.input_facts(case)
    evidence = RepositoryEvidence(
        tuple(RepositoryText(p, f.files[p]) for p in sorted(facts.selected_paths))
    )
    return f, initial_manifest(facts, evidence)


def output(m: Any, f: Any, variant: str, phase: str) -> str:
    o = next(o for x, o in data.load() if x.id == f.id)
    disposition = o.initial if phase == "initial" else o.expected[variant]
    return json.dumps(
        {
            "disposition": disposition,
            "explanation": "Offline fixture response",
            "governing_sources": [m.evidence.files[0].path],
            "requests": [
                {
                    "kind": c.kind,
                    "description": c.alternatives[0]
                    if c.alternatives
                    else "Supply referenced source",
                    "path": c.path,
                    "choices": [],
                }
                for c in o.at(phase, variant).required
            ]
            if disposition != "sufficient"
            else [],
        }
    )


def probe(url: str, model: str, digest: str) -> ServingIdentity:
    assert (url, model, digest) == (identity.URL, identity.MODEL, identity.MODEL_DIGEST)
    return ServingIdentity(identity.VERSION, model, digest)


def repo(*args: str) -> str:
    return "abcdef" if args[0] == "rev-parse" else ""


def test_identity_preflight_zero_calls(tmp_path: Path) -> None:
    value = identity.preflight(tmp_path / "run", probe=probe, repository=repo)
    assert value["agent_version"] == "1.0.0"
    assert value["report"] == identity.REPORT
    assert value["N"] == 1 and value["full_calls"] == 68 and value["smoke_calls"] == 6
    assert value["smoke"] == ["d01", "d05", "d09", "d13", "d20", "d21"]
    assert (
        value["call_seconds"] == 600
        and value["smoke_seconds"] == 1800
        and value["full_seconds"] == 21600
    )
    assert value["commit"] == "abcdef"
    assert (
        value["final_analysis_calls"] == 0
        and not value["retry"]
        and not value["fallback"]
    )
    assert value["model_digest"] == identity.MODEL_DIGEST
    assert len(value["prompt_digest"]) == 64 and len(value["agent_fingerprint"]) == 64


@pytest.mark.parametrize(
    "key", list(json.loads((identity.HERE / "pins.json").read_text()))
)
def test_frozen_pin_mismatch(monkeypatch: pytest.MonkeyPatch, key: str) -> None:
    original = identity.digest
    monkeypatch.setattr(
        identity, "digest", lambda p: "bad" if p == identity.ROOT / key else original(p)
    )
    with pytest.raises(ValueError, match="FROZEN_IDENTITY_MISMATCH"):
        identity.binding()


@pytest.mark.parametrize(
    "url",
    [
        "https://remote.example",
        "http://localhost:11434",
        "http://user:secret@127.0.0.1:11434",
        "http://127.0.0.1:11434/api",
        "http://[::1]:11434",
    ],
)
def test_no_remote_or_credentials(tmp_path: Path, url: str) -> None:
    with pytest.raises(ValueError, match="LOCAL_CREDENTIAL"):
        identity.preflight(tmp_path / "new", url=url, probe=probe, repository=repo)


@pytest.mark.parametrize("field", ["model_name", "model_digest", "ollama_version"])
def test_provider_identity_mismatch(tmp_path: Path, field: str) -> None:
    def wrong(*args: str) -> ServingIdentity:
        return replace(probe(*args), **{field: "wrong"})

    with pytest.raises(ValueError, match="REVIEW_REQUIRED|MODEL_IDENTITY"):
        identity.preflight(tmp_path / "new", probe=wrong, repository=repo)


def test_dirty_and_uncommitted_refusal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="DIRTY"):
        identity.preflight(
            tmp_path / "new", probe=probe, repository=lambda *args: "M dirty"
        )

    def uncommitted(*args: str) -> str:
        if args[0] == "cat-file":
            raise ValueError("uncommitted")
        return repo(*args)

    with pytest.raises(ValueError, match="uncommitted"):
        identity.preflight(tmp_path / "new", probe=probe, repository=uncommitted)


def test_storage_overwrite_and_identity(tmp_path: Path) -> None:
    path = tmp_path / "unique"
    store = Store(path)
    with pytest.raises(FileExistsError):
        Store(path)
    with pytest.raises(ValueError, match="OUTPUT"):
        identity.preflight(path, probe=probe, repository=repo)
    store.finish(
        {
            "report_identity": identity.REPORT,
            "mode": "PREFLIGHT",
            "provenance": {},
            "calls": 0,
            **measurement.interpret((), complete=False),
        }
    )
    with pytest.raises(FileExistsError):
        store.finish(
            {
                "report_identity": identity.REPORT,
                "mode": "PREFLIGHT",
                "provenance": {},
                "calls": 0,
                **measurement.interpret((), complete=False),
            }
        )
    assert json.loads((path / "run.json").read_text())["run_id"] == store.run_id


def test_actual_governed_agent_complete_condition_parity(
    reference: tuple[runner.Row, ...],
) -> None:
    calls = []

    async def assess(m: Any, f: Any, v: str, phase: str) -> EvidenceSufficiencyResult:
        calls.append((f.id, v, phase))
        value, digest = await runtime.governed(
            m, runtime.projection(m, f, v, phase), 1, output(m, f, v, phase)
        )
        assert digest is not None
        return value

    async def all_rows() -> tuple[runner.Row, ...]:
        return tuple(
            [
                await sequence.run_row(f, o, v, assess)
                for f, o in data.load()
                for v in f.variants
            ]
        )

    observed = asyncio.run(all_rows())
    assert len(calls) == 68
    assert not any(c[0] in {"d27", "d28"} for c in calls)
    assert sum(len(r.attempts) for r in observed) == 70
    assert all(not r.grounding.produced for r in observed)
    actual = measurement.interpret(observed, complete=True)
    assert actual["sufficiency_profile_outcome"].endswith("SUPPORTED")
    for part, alias in [("heldout", "heldout"), ("regression", "regressions")]:
        expected = cast(dict[str, Any], metrics.evaluate(reference)[alias]).copy()
        expected.pop("grounding")
        assert actual["metrics"][part] == expected
    assert (
        actual["grounding_status"] == actual["final_answer_grounding"] == "NOT_MEASURED"
    )
    assert actual["revision_2_aggregate_verdict"] == "NOT_APPLICABLE"


@pytest.mark.parametrize(
    "fault,outcome",
    [
        (runner.Fault.FALSE_SUFFICIENT, "UNSAFE"),
        (runner.Fault.ABSTAIN, "USEFULNESS_FAILED"),
        (runner.Fault.INVALID, "CONTRACT_FAILED"),
        (runner.Fault.MODEL_FAILURE, "RUNTIME_FAILED"),
    ],
)
def test_outcomes(fault: runner.Fault, outcome: str) -> None:
    rows = runner.run(
        {"d01": fault} if fault is not runner.Fault.FALSE_SUFFICIENT else {"d05": fault}
    )
    assert (
        measurement.interpret(rows, complete=True)["sufficiency_profile_outcome"]
        == measurement.PREFIX + outcome
    )


def test_precedence_and_incomplete_denominators(
    reference: tuple[runner.Row, ...],
) -> None:
    unsafe = replace(reference[0], unauthorized_reads=1)
    v = measurement.interpret((unsafe,), complete=False, runtime_failures=("timeout",))
    assert (
        v["sufficiency_profile_outcome"].endswith("UNSAFE")
        and v["run_completeness"] == "INCOMPLETE"
    )
    assert v["metrics"]["planned"]["semantic"] == 62
    assert v["metrics"]["heldout"]["status"] == "UNAVAILABLE_INCOMPLETE_PARTITION"
    assert measurement.interpret((), complete=False)[
        "sufficiency_profile_outcome"
    ].endswith("INCOMPLETE")
    assert measurement.interpret(reference, complete=True, smoke=True)[
        "sufficiency_profile_outcome"
    ].endswith("INCOMPLETE")


def test_conditional_stop_keeps_planned_denominator(
    reference: tuple[runner.Row, ...],
) -> None:
    rows = runner.run({"d05": runner.Fault.INVALID})
    v = measurement.interpret(rows, complete=True)
    assert v["metrics"]["heldout"]["semantic_planned"]["denominator"] == 62
    assert v["metrics"]["heldout"]["required_request_recall"]["denominator"] == 45


def test_regressions_nongating(reference: tuple[runner.Row, ...]) -> None:
    rows = runner.run({"q19": runner.Fault.ABSTAIN})
    assert measurement.interpret(rows, complete=True)[
        "sufficiency_profile_outcome"
    ].endswith("SUPPORTED")


def test_multi_and_mixed_no_repair(reference: tuple[runner.Row, ...]) -> None:
    row = next(r for r in reference if r.case == "d20")
    assert len(row.attempts[0].requests) == 2 and row.rounds == 1 and not row.eligible
    f, o = next((f, o) for f, o in data.load() if f.id == "d05")

    async def assess(m: Any, f: Any, v: str, phase: str) -> EvidenceSufficiencyResult:
        from legoai_engineering.analyst.sufficiency import (
            EvidenceRequest,
            EvidenceRequestKind,
        )

        reqs = (
            EvidenceRequest(
                EvidenceRequestKind.NAMED_EVIDENCE,
                "Referenced source",
                RepositoryPath(f.addition),
            ),
            EvidenceRequest(
                EvidenceRequestKind.OPERATOR_CLARIFICATION, "Which behavior?"
            ),
        )
        return EvidenceSufficiencyResult(
            assessment=EvidenceSufficiencyAssessment(
                m,
                SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE,
                "Mixed needs",
                (RepositoryPath(m.evidence.files[0].path),),
                reqs,
            )
        )

    row = asyncio.run(sequence.run_row(f, o, "resolved", assess))
    assert (
        len(row.attempts[0].requests) == 2
        and not row.eligible
        and row.rounds == 0
        and row.corrected_request == 0
    )


@pytest.mark.parametrize(
    "key",
    [
        "expected_disposition",
        "expected_request_kind",
        "hidden_path",
        "category",
        "gates",
        "rationale",
        "grounding",
    ],
)
def test_leakage_guard_before_model(key: str) -> None:
    f, m = manifest()
    expected = runtime.projection(m, f, "initial", "initial")
    expected[key] = "oracle value"
    with pytest.raises(ValueError, match="LEAKAGE"):
        asyncio.run(
            runtime.governed(m, expected, 1, output(m, f, "initial", "initial"))
        )


def test_supervised_agent_and_timeout() -> None:
    f, m = manifest()
    expected = runtime.projection(m, f, "initial", "initial")
    result, digest = runtime.supervised(
        m, expected, 10, output=output(m, f, "initial", "initial")
    )
    assert result.assessment and digest
    with pytest.raises(runtime.CallStopped, match="timeout"):
        runtime.supervised(
            m, expected, 0.0001, output=output(m, f, "initial", "initial")
        )
    with pytest.raises(runtime.CallStopped, match="deadline"):
        runtime.supervised(m, expected, 0, output=output(m, f, "initial", "initial"))


def test_smoke_order_no_followup_and_budget(
    tmp_path: Path, reference: tuple[runner.Row, ...]
) -> None:
    seen: list[str] = []

    def call(
        m: Any, expected: Any, timeout: float
    ) -> tuple[EvidenceSufficiencyResult, str]:
        case = identity.SMOKE[len(seen)]
        seen.append(case)
        o = next(o for f, o in data.load() if f.id == case)
        requests = tuple(
            runner.scripted_request(c) for c in o.at("initial", "initial").required
        )
        return EvidenceSufficiencyResult(
            assessment=EvidenceSufficiencyAssessment(
                m,
                SufficiencyDisposition(o.initial),
                "Offline",
                (RepositoryPath(m.evidence.files[0].path),),
                requests,
            )
        ), "digest"

    report = asyncio.run(
        harness.execute(
            "SMOKE", Store(tmp_path / "smoke"), {}, "test-approval", call=call
        )
    )
    from analyst_design_live1.storage import verify_smoke

    verify_smoke(report, {})
    damaged = json.loads(json.dumps(report))
    damaged["records"][0]["attempts"][0]["valid"] = False
    with pytest.raises(ValueError, match="smoke"):
        verify_smoke(damaged, {})
    assert seen == list(identity.SMOKE) and report["calls"] == 6
    assert (
        report["smoke_status"]
        == "SMOKE_PASS — FULL RUN STILL REQUIRES EXPLICIT APPROVAL"
    )
    assert report["sufficiency_profile_outcome"].endswith("INCOMPLETE")
    assert all(len(r["attempts"]) == 1 and r["rounds"] == 0 for r in report["records"])
    assert all("grounding" not in r for r in report["records"])


@pytest.mark.parametrize("reason", ["timeout", "interrupted", "deadline"])
def test_interrupt_no_retry_and_custody(tmp_path: Path, reason: str) -> None:
    calls = []

    def fail(*args: Any) -> Any:
        calls.append(1)
        raise runtime.CallStopped(reason, "SERVER_EFFECT_UNKNOWN")

    report = asyncio.run(
        harness.execute("SMOKE", Store(tmp_path / reason), {}, "approval", call=fail)
    )
    assert (
        len(calls) == 1
        and report["calls"] == 1
        and report["run_completeness"] == "INCOMPLETE"
    )
    assert report["in_flight_disposition"] == "SERVER_EFFECT_UNKNOWN"
    assert (tmp_path / reason / "call-001-started.json").exists()
    assert (tmp_path / reason / "report.json").exists()


def test_architecture() -> None:
    for p in identity.HERE.glob("*.py"):
        text = p.read_text()
        for prohibited in [
            "claim_scripted_analysis(",
            "RepositoryAnalyst(",
            "evaluate(",
            "os.walk(",
            "rglob(",
            "mutation import",
        ]:
            assert prohibited not in text
    assert (
        "EvidenceSufficiencyAgent(guard).assess"
        in (identity.HERE / "runtime.py").read_text()
    )
    assert "EvidenceSequence(" in (identity.HERE / "sequence.py").read_text()
    assert (
        "AuthorizedRepositoryEvidence(" in (identity.HERE / "sequence.py").read_text()
    )


def test_full_controller_68_calls_and_report(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    calls = []

    def call(
        m: Any, expected: Any, timeout: float
    ) -> tuple[EvidenceSufficiencyResult, str | None]:
        f = next(
            f for f, o in data.load() if m.question in {f.question, f.revised_question}
        )
        phase = (
            "final"
            if (
                m.clarifications
                or (f.addition and f.addition in {x.path for x in m.evidence.files})
            )
            else "initial"
        )
        variant = (
            "resolved" if phase == "final" and "resolved" in f.variants else "initial"
        )
        calls.append(f.id)
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                asyncio.run,
                runtime.governed(m, expected, timeout, output(m, f, variant, phase)),
            ).result()

    result = asyncio.run(
        harness.execute(
            "FULL",
            Store(tmp_path / "full"),
            {"commit": "offline"},
            "approval",
            call=call,
        )
    )
    assert result["calls"] == len(calls) == 68
    lifecycle = result["execution_lifecycle"]
    assert (
        lifecycle["planned"] == lifecycle["attempted"] == lifecycle["completed"] == 68
    )
    assert lifecycle["never_attempted"] == lifecycle["attempted_no_result"] == []
    assert len(lifecycle["completed_result"]) == 68
    assert result["sufficiency_profile_outcome"].endswith("SUPPORTED"), result[
        "reasons"
    ]
    assert len(result["planned_slots"]) == 70 and all(
        s["status"] == "RECORDED" for s in result["planned_slots"]
    )
    assert len(result["records"]) == 56 and result["mode"] == "FULL"
    assert result["smoke_status"] is None


def test_wall_budget_before_launch(tmp_path: Path) -> None:
    def forbidden(*args: Any) -> Any:
        raise AssertionError("must not launch")

    result = asyncio.run(
        harness.execute(
            "FULL",
            Store(tmp_path / "deadline"),
            {},
            "approval",
            call=forbidden,
            clock=lambda: 21601,
            started=0,
        )
    )
    assert result["calls"] == 0 and result["run_completeness"] == "INCOMPLETE"
    assert len(result["planned_slots"]) == 70


def test_preflight_modes_no_escalation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(harness, "preflight", lambda directory: {"commit": "offline"})

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("no assessment allowed")

    monkeypatch.setattr(harness, "execute", forbidden)
    result = harness.run("PREFLIGHT", tmp_path / "preflight", "approval")
    assert result["calls"] == 0
    with pytest.raises(ValueError, match="passing smoke"):
        harness.run("FULL", tmp_path / "full", "approval")
    with pytest.raises(ValueError, match="authorization"):
        harness.run("SMOKE", tmp_path / "smoke", "")


def test_preflight_refusal_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refusal(directory: Path) -> Any:
        raise ValueError("RUNTIME_IDENTITY_REVIEW_REQUIRED")

    monkeypatch.setattr(harness, "preflight", refusal)
    result = harness.run("SMOKE", tmp_path / "refused", "approval")
    assert (
        result["calls"] == 0
        and result["stop_reason"] == "RUNTIME_IDENTITY_REVIEW_REQUIRED"
    )
    assert result["revision_2_aggregate_verdict"] == "NOT_APPLICABLE"


def test_regression_semantic_failure_not_safety_gate(
    reference: tuple[runner.Row, ...],
) -> None:
    rows = runner.run({"q19": runner.Fault.FALSE_SUFFICIENT})
    assert measurement.interpret(rows, complete=True)[
        "sufficiency_profile_outcome"
    ].endswith("SUPPORTED")


def test_condition_membership_guard(reference: tuple[runner.Row, ...]) -> None:
    with pytest.raises(ValueError, match="membership"):
        measurement.measurements(reference + (reference[0],))
    r = reference[0]
    with pytest.raises(ValueError, match="phase"):
        measurement.measurements(
            (replace(r, attempts=(replace(r.attempts[0], phase="final"),)),)
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("grounding_status", 1.0),
        ("final_answer_grounding", 0.0),
        ("revision_2_aggregate_verdict", "F"),
        ("report_identity", "forgeai-analyst-design-report/2"),
    ],
)
def test_report_boundary_rejects_false_claims(
    tmp_path: Path, field: str, value: Any
) -> None:
    store = Store(tmp_path / "report")
    report = {
        "report_identity": identity.REPORT,
        "mode": "PREFLIGHT",
        "provenance": {},
        "calls": 0,
        **measurement.interpret((), complete=False),
    }
    report[field] = value
    with pytest.raises(ValueError):
        store.finish(report)


def test_offline_live_provider_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORGEAI_LIVE1_OFFLINE", "1")
    f, m = manifest()
    with pytest.raises(ValueError, match="OFFLINE_PROVIDER_FORBIDDEN"):
        asyncio.run(
            runtime.governed(m, runtime.projection(m, f, "initial", "initial"), 1)
        )


def test_uniform_smoke_refuses_continuation(tmp_path: Path) -> None:
    # Uniform insufficiency avoids unsafe progression but still blocks smoke.
    from legoai_engineering.analyst.sufficiency import (
        EvidenceRequest,
        EvidenceRequestKind,
    )

    def call(
        m: Any, expected: Any, timeout: float
    ) -> tuple[EvidenceSufficiencyResult, str]:
        return EvidenceSufficiencyResult(
            assessment=EvidenceSufficiencyAssessment(
                m,
                SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE,
                "Need context",
                (),
                (EvidenceRequest(EvidenceRequestKind.SOURCE_ROLE, "Unknown role"),),
            )
        ), "digest"

    result = asyncio.run(
        harness.execute("SMOKE", Store(tmp_path / "uniform"), {}, "approval", call=call)
    )
    assert result["calls"] == 6 and result["smoke_status"] == "SMOKE_CONDITION_INVALID"
    assert not result["sufficiency_profile_outcome"].endswith("SUPPORTED")


def test_prerequisite_rejection_is_contract_failure() -> None:
    f, o = next((f, o) for f, o in data.load() if f.id == "d23")

    async def assess(m: Any, f: Any, v: str, phase: str) -> EvidenceSufficiencyResult:
        from legoai_engineering.analyst.sufficiency import SufficiencyFailure

        return EvidenceSufficiencyResult(failure=SufficiencyFailure.PREREQUISITES_UNMET)

    row = asyncio.run(sequence.run_row(f, o, "initial", assess))
    assert not row.attempts[0].valid
    assert measurement.interpret((row,), complete=False)[
        "sufficiency_profile_outcome"
    ].endswith("CONTRACT_FAILED")


def test_midrun_identity_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    bound = identity.binding()
    bound["commit"] = "commit"
    monkeypatch.setattr(
        identity, "git", lambda *args: "dirty" if args[0] == "status" else "commit"
    )
    with pytest.raises(ValueError, match="RUNTIME_CHANGED"):
        identity.verify_before_call(bound)
    monkeypatch.setattr(
        identity, "git", lambda *args: "" if args[0] == "status" else "commit"
    )
    bound["prompt_digest"] = "wrong"
    with pytest.raises(ValueError, match="IDENTITY_CHANGED"):
        identity.verify_before_call(bound)
