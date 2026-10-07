"""PARSER-DIAGNOSTICS-1: closed invalid-output labels; no Agent change, no text."""

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from analyst_design_live1 import harness, output_diagnostics, runtime
from analyst_design_live1.diagnostics import (
    ChildDiagnostics,
    ChildStage,
    FailureCategory,
)
from analyst_design_live1.identity import ROOT, digest
from analyst_design_live1.output_diagnostics import (
    Branch,
    LengthClass,
    OutputDiagnosis,
    RejectionCode,
    classify_reply,
    diagnose,
    document,
    length_class,
)
from analyst_design_live1.storage import Store
from content_discovery1.wiring import Replay, host_for
from legoai_engineering._json_document import json_document
from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceSufficiencyResult,
    SufficiencyFailure,
)
from legoai_engineering.analyst.sufficiency_agent import EvidenceSufficiencyAgent
from legoai_engineering.analyst.sufficiency_definition import (
    evidence_sufficiency_definition,
)
from test_analyst_design_live1 import manifest, output
from test_analyst_design_live1_fix import context_with

from legoai.execution.agent.ports import AgentDefinition, AgentRequest, AgentResult
from legoai.runtime.api import ModelPurpose

CANARY = "PARSER_DIAGNOSTIC_CANARY_MUST_NOT_PERSIST"
SUPPLIED = "sensor/stats.py"  # d01's only supplied path
SMOKE2 = ROOT / "examples/forgeai/live1-smoke-227bdd3cec0b"
PREFLIGHT2 = ROOT / "examples/forgeai/live1-preflight-9bdb9f5867b6"
DIAGNOSTIC2 = (
    ROOT / "planning/FORGEAI-ANALYST-DESIGN-LIVE-1-SMOKE-FAILURE-DIAGNOSTIC-2.md"
)


def reply(**changes: Any) -> str:
    value: dict[str, Any] = {
        "disposition": "sufficient",
        "explanation": "The supplied implementation determines the result.",
        "governing_sources": [SUPPLIED],
        "requests": [],
    }
    value.update(changes)
    return json.dumps(value)


def request(**changes: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "kind": "source_role",
        "description": "governing implementation",
        "path": None,
        "choices": [],
    }
    value.update(changes)
    return value


def missing(*requests: dict[str, Any], **changes: Any) -> str:
    return reply(
        disposition="missing_governing_evidence",
        governing_sources=[],
        requests=list(requests),
        **changes,
    )


class Recording:
    """Public AgentRuntimePort decorator: keeps the returned result for the test."""

    def __init__(self, inner: Any) -> None:
        self.inner, self.calls = inner, 0
        self.result: AgentResult | None = None

    async def run(
        self, definition: AgentDefinition, request: AgentRequest
    ) -> AgentResult:
        self.calls += 1
        result: AgentResult = await self.inner.run(definition, request)
        self.result = result
        return result


def agent(
    text: str, m: EvidenceManifest | None = None
) -> tuple[EvidenceSufficiencyResult, OutputDiagnosis | None, Replay, Recording]:
    """The real governed Agent path with one fixed reply, then the observer."""
    if m is None:
        _, m = manifest()
    model = Replay(text)
    host, _ = host_for(model)
    recording = Recording(host.agent_runtime())
    result = asyncio.run(
        EvidenceSufficiencyAgent(recording).assess(
            host.model_execution(ModelPurpose.CHAT), m, current_manifest=lambda: m
        )
    )
    return result, diagnose(result.failure, recording.result, m), model, recording


INVALID: dict[str, tuple[str, RejectionCode]] = {
    "prose": ("I think it is sufficient.", RejectionCode.NON_JSON_DOCUMENT),
    "prose_around_json": (
        "Answer: " + reply() + " thanks",
        RejectionCode.NON_JSON_DOCUMENT,
    ),
    "trailing_prose": (reply() + " done", RejectionCode.NON_JSON_DOCUMENT),
    "malformed_fence": ("```json\n" + reply(), RejectionCode.NON_JSON_DOCUMENT),
    "malformed_json": (
        '{"disposition": "sufficient",',
        RejectionCode.JSON_DECODE_INVALID,
    ),
    "multiple_documents": (
        reply() + "\n" + reply(),
        RejectionCode.MULTIPLE_JSON_DOCUMENTS,
    ),
    "duplicate_key": (
        '{"disposition":"sufficient",' + reply()[1:],
        RejectionCode.DUPLICATE_JSON_KEY,
    ),
    "top_level_array": ("[]", RejectionCode.FIELD_SET_INVALID),
    "missing_field": (
        json.dumps({"disposition": "sufficient", "explanation": "x", "requests": []}),
        RejectionCode.FIELD_SET_INVALID,
    ),
    "unknown_field": (
        reply()[:-1] + ',"confidence":1}',
        RejectionCode.FIELD_SET_INVALID,
    ),
    "requests_type": (reply(requests="none"), RejectionCode.FIELD_TYPE_INVALID),
    "disposition_type": (reply(disposition=3), RejectionCode.FIELD_TYPE_INVALID),
    "explanation_type": (reply(explanation=None), RejectionCode.FIELD_TYPE_INVALID),
    "sources_type": (
        reply(governing_sources=SUPPLIED),
        RejectionCode.FIELD_TYPE_INVALID,
    ),
    "invalid_disposition": (
        reply(disposition="maybe"),
        RejectionCode.DISPOSITION_INVALID,
    ),
    "source_not_supplied": (
        reply(governing_sources=["other/file.py"]),
        RejectionCode.GOVERNING_SOURCES_INVALID,
    ),
    "source_syntax": (
        reply(governing_sources=["../escape.py"]),
        RejectionCode.GOVERNING_SOURCES_INVALID,
    ),
    "source_duplicate": (
        reply(governing_sources=[SUPPLIED, SUPPLIED]),
        RejectionCode.GOVERNING_SOURCES_INVALID,
    ),
    "too_many_requests": (
        missing(*(request(description=f"role {i}") for i in range(9))),
        RejectionCode.REQUEST_SET_INVALID,
    ),
    "request_missing_field": (
        missing({"kind": "source_role", "description": "x", "path": None}),
        RejectionCode.REQUEST_SET_INVALID,
    ),
    "request_not_object": (missing("role"), RejectionCode.REQUEST_SET_INVALID),  # type: ignore[arg-type]
    "duplicate_requests": (
        missing(request(), request()),
        RejectionCode.REQUEST_SET_INVALID,
    ),
    "invalid_kind": (
        missing(request(kind="explore")),
        RejectionCode.REQUEST_KIND_INVALID,
    ),
    "named_without_path": (
        missing(request(kind="named_evidence")),
        RejectionCode.REQUEST_PATH_INVALID,
    ),
    "role_with_path": (
        missing(request(path="tables/zones.tsv")),
        RejectionCode.REQUEST_PATH_INVALID,
    ),
    "named_path_syntax": (
        missing(request(kind="named_evidence", path="/abs/path.py")),
        RejectionCode.REQUEST_PATH_INVALID,
    ),
    "single_clarification_choice": (
        reply(
            disposition="unresolved_ambiguity",
            governing_sources=[],
            requests=[request(kind="operator_clarification", choices=["capture"])],
        ),
        RejectionCode.REQUEST_CHOICES_INVALID,
    ),
    "role_with_choices": (
        missing(request(choices=["a", "b"])),
        RejectionCode.REQUEST_CHOICES_INVALID,
    ),
    "duplicate_choices": (
        reply(
            disposition="unresolved_ambiguity",
            governing_sources=[],
            requests=[request(kind="operator_clarification", choices=["a", "a", "b"])],
        ),
        RejectionCode.REQUEST_CHOICES_INVALID,
    ),
    "explanation_oversize": (
        reply(explanation="x" * 2049),
        RejectionCode.VALUE_BOUND_EXCEEDED,
    ),
    "explanation_blank": (reply(explanation="  "), RejectionCode.VALUE_BOUND_EXCEEDED),
    "description_blank": (
        missing(request(description=" ")),
        RejectionCode.VALUE_BOUND_EXCEEDED,
    ),
    "choice_oversize": (
        reply(
            disposition="unresolved_ambiguity",
            governing_sources=[],
            requests=[request(kind="operator_clarification", choices=["a", "b" * 257])],
        ),
        RejectionCode.VALUE_BOUND_EXCEEDED,
    ),
    "sufficient_with_request": (
        reply(requests=[request()]),
        RejectionCode.DISPOSITION_REQUEST_INCOHERENT,
    ),
    "sufficient_without_citation": (
        reply(governing_sources=[]),
        RejectionCode.DISPOSITION_REQUEST_INCOHERENT,
    ),
    "ambiguity_without_clarification": (
        reply(
            disposition="unresolved_ambiguity",
            governing_sources=[],
            requests=[request()],
        ),
        RejectionCode.DISPOSITION_REQUEST_INCOHERENT,
    ),
    "missing_without_evidence_request": (
        missing(request(kind="operator_clarification")),
        RejectionCode.DISPOSITION_REQUEST_INCOHERENT,
    ),
}
VALID = {
    "sufficient": reply(),
    "fenced": "```json\n" + reply() + "\n```",
    "role_request": missing(request()),
    "mixed": missing(request(), request(kind="operator_clarification")),
    "clarification_choices": reply(
        disposition="unresolved_ambiguity",
        governing_sources=[],
        requests=[request(kind="operator_clarification", choices=["a", "b"])],
    ),
}


# A, V: valid output is accepted by the Agent and never diagnosed --------------


@pytest.mark.parametrize("case", sorted(VALID))
def test_valid_output_bypasses_diagnostics(case: str) -> None:
    result, diagnosis, model, recording = agent(VALID[case])
    assert result.assessment is not None and result.failure is None
    assert diagnosis is None
    _, m = manifest()
    assert classify_reply(VALID[case], m) is None  # parity in the accepting direction
    assert len(model.requests) == recording.calls == 1


# B-N: every representable invalid shape, through the real Agent ----------------


@pytest.mark.parametrize("case", sorted(INVALID))
def test_invalid_output_classification_and_agent_parity(case: str) -> None:
    text, code = INVALID[case]
    result, diagnosis, model, recording = agent(text)
    # The Agent is authoritative and unchanged: still INVALID_OUTPUT, no result.
    assert result.failure is SufficiencyFailure.INVALID_OUTPUT
    assert result.assessment is None
    assert diagnosis == OutputDiagnosis(
        code, length_class(text), Branch.AGENT_PARSE, False
    )
    assert len(model.requests) == recording.calls == 1  # no retry, no second call


def test_core_output_contract_classification() -> None:
    for text in ("   ", "x" * 32769):
        result, diagnosis, model, _ = agent(text)
        assert result.failure is SufficiencyFailure.INVALID_OUTPUT
        assert diagnosis == OutputDiagnosis(
            RejectionCode.CORE_OUTPUT_CONTRACT,
            LengthClass.UNAVAILABLE,
            Branch.CORE_OUTPUT_CONTRACT,
            False,
        )
        assert len(model.requests) == 1


def test_prerequisites_classification() -> None:
    _, base = manifest()
    m = EvidenceManifest(
        base.question,
        base.evidence,
        base.provenance,
        base.expectations,
        base.clarifications,
        ("declared unknown prerequisite",),
    )
    result, diagnosis, _, _ = agent(reply(), m)
    assert result.failure is SufficiencyFailure.PREREQUISITES_UNMET
    assert diagnosis == OutputDiagnosis(
        RejectionCode.PREREQUISITES_UNMET,
        LengthClass.SMALL,
        Branch.AGENT_PREREQUISITES,
        False,
    )


# P, Q: unknown fallback and disagreement never override the Agent -------------


def test_unknown_fallback_when_classifier_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(text: str, m: Any) -> Any:
        raise RuntimeError(CANARY)

    monkeypatch.setattr(output_diagnostics, "classify_reply", broken)
    result, diagnosis, _, _ = agent("not json")
    assert result.failure is SufficiencyFailure.INVALID_OUTPUT
    assert diagnosis is not None
    assert diagnosis.code is RejectionCode.UNKNOWN_INVALID_OUTPUT
    assert diagnosis.disagreement is True
    assert CANARY not in json.dumps(diagnosis.record())


def test_disagreement_keeps_agent_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(output_diagnostics, "classify_reply", lambda text, m: None)
    result, diagnosis, _, _ = agent("not json")
    assert result.failure is SufficiencyFailure.INVALID_OUTPUT  # not a semantic result
    assert result.assessment is None
    assert diagnosis is not None
    assert diagnosis.record() == {
        "invalid_output_rejection_code": "UNKNOWN_INVALID_OUTPUT",
        "output_length_class": "SMALL",
        "invalid_output_branch": "AGENT_PARSE",
        "diagnostic_disagreement": True,
    }


def test_other_failures_and_success_are_not_diagnosed() -> None:
    _, m = manifest()
    for failure in (
        None,
        SufficiencyFailure.MODEL_FAILURE,
        SufficiencyFailure.STALE_ASSESSMENT,
        SufficiencyFailure.BUDGET_EXHAUSTED,
    ):
        assert diagnose(failure, None, m) is None


# Taxonomy, length buckets and the mirrored ADR-021 envelope ---------------------


def test_closed_taxonomies_and_length_buckets() -> None:
    assert {c.value for c in RejectionCode} >= {
        "CORE_OUTPUT_CONTRACT", "NON_JSON_DOCUMENT", "MULTIPLE_JSON_DOCUMENTS",
        "JSON_DECODE_INVALID", "FIELD_SET_INVALID", "FIELD_TYPE_INVALID",
        "DISPOSITION_INVALID", "GOVERNING_SOURCES_INVALID", "REQUEST_SET_INVALID",
        "REQUEST_KIND_INVALID", "REQUEST_PATH_INVALID", "REQUEST_CHOICES_INVALID",
        "VALUE_BOUND_EXCEEDED", "DISPOSITION_REQUEST_INCOHERENT",
        "PREREQUISITES_UNMET", "UNKNOWN_INVALID_OUTPUT",
    }  # fmt: skip
    assert len(RejectionCode) == 17 and len(Branch) == 3
    assert [c.value for c in LengthClass] == ["SMALL", "MEDIUM", "LARGE", "UNAVAILABLE"]
    assert length_class(None) is LengthClass.UNAVAILABLE
    assert length_class("x") is LengthClass.SMALL
    assert length_class("x" * 1024) is LengthClass.SMALL
    assert length_class("x" * 1025) is LengthClass.MEDIUM
    assert length_class("é" * 4096) is LengthClass.MEDIUM  # bytes, not characters
    assert length_class("x" * 8193) is LengthClass.LARGE
    with pytest.raises(TypeError):
        OutputDiagnosis(
            "NON_JSON_DOCUMENT",  # type: ignore[arg-type]
            LengthClass.SMALL,
            Branch.AGENT_PARSE,
            False,
        )


@pytest.mark.parametrize(
    "text",
    [
        reply(),
        "```json\n" + reply() + "\n```",
        "```\n" + reply() + "\n```",
        "  ```json\r\n" + reply() + "\n```  ",
        "```json\n" + reply(),
        "```python\n" + reply() + "\n```",
        "```json\n```",
    ],
)
def test_document_mirror_matches_adr021(text: str) -> None:
    assert document(text) == json_document(text)


# R, S: content-free custody through the real spawned child and storage ---------


def test_spawn_invalid_output_persists_closed_fields_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = runtime.supervised
    text = '{"disposition": "' + CANARY + '", "explanation": "' + CANARY + '"'

    def invalid(m: Any, expected: Any, timeout: float, *, observe: Any) -> Any:
        return original(m, expected, 10, output=text, observe=observe)

    monkeypatch.setattr(harness, "supervised", invalid)
    report = asyncio.run(
        harness.execute(
            "SMOKE",
            Store(tmp_path / "invalid"),
            {},
            "offline",
            call=invalid,
            before_call=lambda: None,
        )
    )
    assert report["smoke_status"] == "SMOKE_CONTRACT_FAILURE"  # precedence unchanged
    assert report["stop_reason"] == "invalid_output"
    assert report["calls"] == 1  # no retry and no diagnostic call
    finish = json.loads((tmp_path / "invalid/call-001-finished.json").read_text())
    assert finish["failure"] == "invalid_output"
    expected = {
        "invalid_output_rejection_code": "JSON_DECODE_INVALID",
        "output_length_class": "SMALL",
        "invalid_output_branch": "AGENT_PARSE",
        "diagnostic_disagreement": False,
    }
    assert expected.items() <= finish["child_diagnostics"].items()
    assert expected.items() <= report["timings"][0]["child_diagnostics"].items()
    prompt = evidence_sufficiency_definition().system_prompt
    for path in (tmp_path / "invalid").iterdir():
        content = path.read_text(encoding="utf-8")
        assert CANARY not in content, path.name
        assert prompt[:80] not in content, path.name
        assert "Traceback" not in content and "JSONDecodeError" not in content
        assert "Expecting" not in content  # json exception message
    assert CANARY not in json.dumps(report)


def test_successful_call_records_have_no_output_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = runtime.supervised
    f, _ = manifest()

    def valid(m: Any, expected: Any, timeout: float, *, observe: Any) -> Any:
        return original(
            m, expected, 10, output=output(m, f, "initial", "initial"), observe=observe
        )

    monkeypatch.setattr(harness, "supervised", valid)
    report = asyncio.run(
        harness.execute(
            "SMOKE",
            Store(tmp_path / "valid"),
            {},
            "offline",
            call=valid,
            before_call=lambda: None,
        )
    )
    diagnostics = report["timings"][0]["child_diagnostics"]
    assert "invalid_output_rejection_code" not in diagnostics
    assert set(diagnostics) == set(ChildDiagnostics().record())


def broken_child(
    pipe: Any, m: Any, expected: Any, timeout: float, output: str | None
) -> None:
    diagnosis = OutputDiagnosis(
        RejectionCode.NON_JSON_DOCUMENT, LengthClass.SMALL, Branch.AGENT_PARSE, False
    )
    for stage in ChildStage:
        pipe.send(("stage", stage))
    if output == "extra":  # diagnosis attached to a non-diagnosed failure
        result = EvidenceSufficiencyResult(failure=SufficiencyFailure.MODEL_FAILURE)
        pipe.send(("result", result, None, diagnosis))
    elif output == "absent":  # invalid output without its diagnosis
        result = EvidenceSufficiencyResult(failure=SufficiencyFailure.INVALID_OUTPUT)
        pipe.send(("result", result, None, None))
    else:
        result = EvidenceSufficiencyResult(failure=SufficiencyFailure.INVALID_OUTPUT)
        pipe.send(("result", result, None, {"code": CANARY}))
    pipe.close()


@pytest.mark.parametrize("mode", ["extra", "absent", "untyped"])
def test_envelope_diagnosis_must_be_closed_and_consistent(
    monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    context_with(monkeypatch, broken_child)
    _, m = manifest()
    with pytest.raises(runtime.CallStopped) as caught:
        runtime.supervised(m, {}, 10, output=mode)
    record = caught.value.diagnostics.record()
    assert record["child_failure_category"] == FailureCategory.INVALID_RESULT
    assert "invalid_output_rejection_code" not in record
    assert CANARY not in json.dumps(record)


# T, U: history is preserved; d09 remains a semantic miss, not a contract failure


HISTORY2 = {
    SMOKE2
    / "report.json": "8fdb5a8376103bbc9df5f44a342f9954bd7ce6add7bfe38dda74ac1692124dde",
    SMOKE2
    / "report.md": "d6ef39c349ad1035982afac4c097d8c2ef6af346f9050a9831ddf2ccb04b6ed6",
    SMOKE2
    / "run.json": "ae45af7fe116eae65294f0ec49ce21946f07af7b01a3c84f041c64aef7196f11",
    PREFLIGHT2
    / "report.json": "4cafdcf07b4b3dc215a7f650575a6897617c55837c85370315821113e99d8edb",
    PREFLIGHT2
    / "report.md": "4a02f2640ca563c70d1c031e09811fe0fcfcfc841c35192359b4420e68c1018d",
    PREFLIGHT2
    / "run.json": "14b5f3634903bbf99b1173ec91b7e41dec230c308bb27c4041d6631f0580f159",
}


def test_historical_smoke2_unchanged_and_d13_cause_unknown() -> None:
    text = DIAGNOSTIC2.read_text(encoding="utf-8")
    for path, value in HISTORY2.items():
        assert value in text  # recorded in the committed diagnostic
        assert hashlib.sha256(path.read_bytes()).hexdigest() == value, path.name
    listing = "".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()} *{p.name}\n"
        for p in sorted(SMOKE2.iterdir(), key=lambda p: p.name)
    )
    inventory = "68f4e1ae6a637010ab38ce361717a6d3a17c9f104d6e4b9f25ff9201539ecf6a"
    assert inventory in text
    assert hashlib.sha256(listing.encode()).hexdigest() == inventory
    report = json.loads((SMOKE2 / "report.json").read_text(encoding="utf-8"))
    assert report["run_id"] == "cafee55d-7032-4115-828a-8a6b2d14363a"
    assert report["smoke_status"] == "SMOKE_CONTRACT_FAILURE"
    d13 = next(t for t in report["timings"] if t["case"] == "d13")
    assert d13["failure"] == "invalid_output"
    # No backfill: the historical record carries no rejection code.
    assert "invalid_output_rejection_code" not in d13["child_diagnostics"]
    assert "CAUSE NOT ESTABLISHED" in text


def test_d09_remains_semantic_request_quality_failure() -> None:
    report = json.loads((SMOKE2 / "report.json").read_text(encoding="utf-8"))
    d09 = next(r for r in report["records"] if r["case"] == "d09")
    attempt = d09["attempts"][0]
    assert attempt["valid"] is True and attempt["failure"] is None
    assert attempt["disposition"] == "missing_governing_evidence"
    assert [(q["kind"], q["path"]) for q in attempt["requests"]] == [
        ("named_evidence", "mail/routing_table.json")
    ]
    counts = next(
        x["metrics"]["request_counts"]
        for x in report["metrics"]["observed_condition_metrics"]
        if x["case"] == "d09"
    )
    assert (counts["invented"], counts["under"], counts["over"]) == (1, 1, 1)
    oracle = json.loads(
        (
            ROOT / "examples/forgeai/evaluation/analyst_design_eval2/oracle-v2.json"
        ).read_text(encoding="utf-8")
    )
    entry = next(
        x
        for x in (oracle["cases"] if "cases" in oracle else oracle)
        if x["id"] == "d09"
    )
    assert [r["kind"] for r in entry["request_policy"]["initial"]["required"]] == [
        "source_role"
    ]
    # The same shape is structurally valid for the unchanged Agent: no diagnosis.
    f, m = manifest("d09")
    shape = missing(
        request(
            kind="named_evidence",
            description="The routing table that maps postcodes to depots",
            path="mail/routing_table.json",
        )
    )
    result, diagnosis, _, _ = agent(shape, m)
    assert result.assessment is not None and diagnosis is None


# V, W, X: no Agent, prompt, parser, evaluator or profile change; offline only --


def test_agent_evaluator_and_profile_sources_match_pins() -> None:
    pins = json.loads(
        (ROOT / "examples/forgeai/evaluation/analyst_design_live1/pins.json").read_text(
            encoding="utf-8"
        )
    )
    for relative, expected in pins.items():
        assert digest(ROOT / relative) == expected, relative
    source = (
        ROOT / "examples/forgeai/evaluation/analyst_design_live1/output_diagnostics.py"
    ).read_text(encoding="utf-8")
    for forbidden in ("legoai.reference", "_composition", "ModelPort", "write_text"):
        assert forbidden not in source, forbidden
    for private in ("from legoai_engineering._", "sufficiency_agent import _"):
        assert private not in source
