"""Bounded evidence and structured output; all model calls use real M7 wiring."""

import asyncio
import json
import sys
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from legoai.intelligence.model.ports import ModelResponseUncertainError
from legoai.kernel.effects import EffectExtent
from repository_analyst import create_demo

from legoai_engineering.analyst._composition import AuthorizedRepositoryEvidence
from legoai_engineering.analyst.values import (
    AcquisitionFailure,
    RepositoryAnalysisStatus,
    RepositoryEvidence,
)
from legoai_engineering.repository.errors import WorkspaceBoundaryError
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath


def answer(**changes: object) -> str:
    result: dict[str, object] = {
        "status": "succeeded",
        "summary": "A defines the behavior.",
        "relevant_files": ["a.py"],
        "findings": [{"text": "Definition supplied.", "paths": ["a.py"]}],
        "risks": [],
        "unknowns": ["Execution was not observed."],
    }
    result.update(changes)
    return json.dumps(result)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_text("def a(): return 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("from a import a\n", encoding="utf-8")
    return tmp_path


def test_success_ordering_one_call_and_no_mutation(workspace: Path) -> None:
    before = {p.name: p.read_bytes() for p in workspace.iterdir()}
    prompts = []
    for targets in (
        (RepositoryPath("b.py"), RepositoryPath("a.py")),
        (RepositoryPath("a.py"), RepositoryPath("b.py")),
    ):
        analyst, request, model = create_demo(workspace, answer(), targets=targets)
        result = asyncio.run(analyst.analyze(request))
        assert result.status is RepositoryAnalysisStatus.SUCCEEDED
        assert result.evidence is not None
        assert tuple(f.path for f in result.evidence.files) == ("a.py", "b.py")
        assert model.calls == 1 and model.last_request is not None
        prompts.append(model.last_request.messages)
        assert result.agent_result is not None
        assert result.agent_result.model_execution is not None
        assert result.agent_result.model_execution.effect is EffectExtent.COMPLETED
    assert prompts[0] == prompts[1]
    assert before == {p.name: p.read_bytes() for p in workspace.iterdir()}


# The public host pins one selected binding; ambiguity is covered in Core M7 tests.
@pytest.mark.parametrize("count", [0])
def test_routing_failure_never_calls_model(workspace: Path, count: int) -> None:
    analyst, request, model = create_demo(workspace, answer(), route_count=count)
    result = asyncio.run(analyst.analyze(request))
    assert result.status is RepositoryAnalysisStatus.MODEL_FAILURE
    assert model.calls == 0


@pytest.mark.parametrize(
    "output",
    [
        "not JSON",
        "[]",
        '{"status":"succeeded","status":"succeeded"}',
        answer(relevant_files=["invented.py"]),
        answer(relevant_files=["../outside"]),
        answer(findings=[{"text": "guess", "paths": ["missing.py"]}]),
        answer(extra="unexpected"),
        answer(summary="x" * 2049),
        answer(risks=["risk"] * 9),
        answer(findings=[{"text": "guess", "paths": []}]),
    ],
    ids=[
        "syntax",
        "array",
        "duplicate",
        "invented",
        "escape",
        "fake-finding",
        "extra",
        "summary-budget",
        "array-budget",
        "uncited",
    ],
)
def test_malformed_or_uncited_output_is_rejected(workspace: Path, output: str) -> None:
    analyst, request, model = create_demo(workspace, output)
    result = asyncio.run(analyst.analyze(request))
    assert result.status is RepositoryAnalysisStatus.OUTPUT_INVALID
    assert result.analysis is None and model.calls == 1
    assert result.agent_result is not None
    assert result.agent_result.model_execution is not None
    assert result.agent_result.model_execution.effect is EffectExtent.COMPLETED


def test_unknowns_are_explicit(workspace: Path) -> None:
    analyst, request, _ = create_demo(
        workspace,
        answer(status="insufficient_evidence", findings=[], relevant_files=[]),
    )
    result = asyncio.run(analyst.analyze(request))
    assert result.status is RepositoryAnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.analysis is not None and result.analysis.unknowns


def test_denied_and_missing_stop_before_model(workspace: Path) -> None:
    for allowed, expected in (
        (False, AcquisitionFailure.DENIED),
        (True, AcquisitionFailure.UNAVAILABLE),
    ):
        analyst, request, model = create_demo(
            workspace,
            answer(),
            read_allowed=allowed,
            targets=(RepositoryPath("missing.py"),),
        )
        result = asyncio.run(analyst.analyze(request))
        assert result.acquisition_failure is expected
        assert result.analysis is None
        assert result.agent_result is None
        assert model.calls == 0


@pytest.mark.parametrize("path", ["../outside", "/absolute", "C:/outside"])
def test_m2_path_boundary(path: str) -> None:
    with pytest.raises(WorkspaceBoundaryError):
        RepositoryPath(path)


def test_symlink_escape_is_rejected_before_model(
    workspace: Path, tmp_path: Path
) -> None:
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.write_text("private", encoding="utf-8")
    try:
        (workspace / "link").symlink_to(outside)
    except OSError as error:
        if sys.platform == "win32" and error.winerror == 1314:
            pytest.skip("Windows symlink privilege unavailable; enable Developer Mode")
        raise
    analyst, request, model = create_demo(
        workspace, answer(), targets=(RepositoryPath("link"),)
    )
    result = asyncio.run(analyst.analyze(request))
    assert result.acquisition_failure is AcquisitionFailure.BOUNDARY
    assert model.calls == 0


def test_evidence_and_prompt_budgets(workspace: Path) -> None:
    with pytest.raises(ValueError):
        RepositoryEvidence((RepositoryText("a", "x" * 8193),))
    with pytest.raises(ValueError):
        RepositoryEvidence(tuple(RepositoryText(str(i), "x" * 8192) for i in range(4)))
    # Control-character escaping grows the JSON beyond M7's input budget.
    (workspace / "a.py").write_text("\t" * 8192, encoding="utf-8")
    (workspace / "b.py").write_text("\t" * 8192, encoding="utf-8")
    analyst, request, model = create_demo(workspace, answer())
    result = asyncio.run(analyst.analyze(request))
    assert result.acquisition_failure is AcquisitionFailure.BUDGET
    assert model.calls == 0


def test_question_and_request_bounds(workspace: Path) -> None:
    _, request, _ = create_demo(workspace, answer())
    with pytest.raises(ValueError):
        replace(request, question="x" * 2049)
    with pytest.raises(ValueError):
        replace(request, targets=(RepositoryPath("a.py"),) * 2)
    with pytest.raises(ValueError):
        replace(request, targets=())


def test_model_uncertainty_is_preserved_without_retry(workspace: Path) -> None:
    analyst, request, model = create_demo(workspace, answer())
    model.error = ModelResponseUncertainError("response unavailable")
    result = asyncio.run(analyst.analyze(request))
    assert result.status is RepositoryAnalysisStatus.MODEL_FAILURE
    assert result.analysis is None
    assert result.agent_result is not None
    assert result.agent_result.model_execution is not None
    assert result.agent_result.model_execution.effect is EffectExtent.UNKNOWN
    assert model.calls == 1


def test_denied_selection_cannot_read_workspace(workspace: Path) -> None:
    for read_allowed in (False, True):
        analyst, request, model = create_demo(
            workspace, answer(), read_allowed=read_allowed
        )
        reader = analyst.evidence_reader
        assert isinstance(reader, AuthorizedRepositoryEvidence)
        with patch.object(
            type(reader.workspace),
            "read_text",
            side_effect=AssertionError("denied read"),
        ):
            if read_allowed:
                request = replace(request, targets=(RepositoryPath("ungranted.py"),))
            result = asyncio.run(analyst.analyze(request))
        assert result.acquisition_failure is AcquisitionFailure.DENIED
        assert model.calls == 0


@pytest.mark.parametrize("output", ["x" * 16385, "\ud800"], ids=["size", "encoding"])
def test_m7_output_boundary_remains_authoritative(workspace: Path, output: str) -> None:
    analyst, request, model = create_demo(workspace, output)
    result = asyncio.run(analyst.analyze(request))
    assert result.status is RepositoryAnalysisStatus.OUTPUT_INVALID
    assert result.analysis is None
    assert model.calls == 1


def test_result_cannot_misrepresent_success(workspace: Path) -> None:
    analyst, request, _ = create_demo(workspace, answer())
    result = asyncio.run(analyst.analyze(request))
    with pytest.raises(ValueError):
        replace(result, analysis=None)
    with pytest.raises(ValueError):
        replace(result, status=RepositoryAnalysisStatus.MODEL_FAILURE)
    with pytest.raises(ValueError):
        replace(result, acquisition_failure=AcquisitionFailure.DENIED)
    with pytest.raises(ValueError):
        replace(result, status=RepositoryAnalysisStatus.INSUFFICIENT_EVIDENCE)


def test_utf8_evidence_and_selection_limits(workspace: Path) -> None:
    with pytest.raises(ValueError):
        RepositoryEvidence((RepositoryText("a", "é" * 4097),))
    _, request, _ = create_demo(workspace, answer())
    with pytest.raises(ValueError):
        replace(request, targets=(RepositoryPath("\ud800"),))
    with pytest.raises(ValueError):
        replace(request, targets=tuple(RepositoryPath(str(i)) for i in range(9)))
    with pytest.raises(ValueError):
        replace(request, targets=(RepositoryPath("A.py"), RepositoryPath("a.py")))


def test_workspace_limit_fails_before_disclosure(workspace: Path) -> None:
    (workspace / "a.py").write_text("x" * 8193, encoding="utf-8")
    analyst, request, model = create_demo(workspace, answer())
    result = asyncio.run(analyst.analyze(request))
    assert result.acquisition_failure is AcquisitionFailure.BUDGET
    assert result.evidence is None
    assert result.agent_result is None
    assert model.calls == 0


def test_expired_read_authority_cannot_release_acquired_evidence(
    workspace: Path,
) -> None:
    analyst, request, model = create_demo(workspace, answer())
    reader = analyst.evidence_reader
    assert isinstance(reader, AuthorizedRepositoryEvidence)
    now = reader.security_context.established_at
    times = iter((now, now, now + timedelta(hours=2)))
    analyst = replace(
        analyst, evidence_reader=replace(reader, clock=lambda: next(times))
    )
    result = asyncio.run(analyst.analyze(request))
    assert result.acquisition_failure is AcquisitionFailure.DENIED
    assert result.evidence is None
    assert result.agent_result is None
    assert model.calls == 0
