"""Read-only Coding references: disclosure through authorized reads, never scope."""

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest
from bounded_coding import create_demo
from governed_demo import StaticModel

from legoai_engineering.agent_output import OutputRejection
from legoai_engineering.analyst.authorized import AuthorizedRepositoryEvidence
from legoai_engineering.analyst.values import AcquisitionFailure, RepositoryEvidence
from legoai_engineering.coding.api import CodingAgent
from legoai_engineering.coding.authorized import AuthorizedCodingEvidence
from legoai_engineering.coding.values import (
    MAX_REFERENCE_BYTES,
    MAX_REFERENCE_TOTAL_BYTES,
    CodingEvidence,
    CodingFile,
    CodingRequest,
    CodingResult,
    CodingStatus,
    CodingTarget,
)
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath

TARGET = CodingTarget(RepositoryPath("pkg/new.py"), FileChangeKind.CREATE)
STYLE = "from pkg.old import value\n\n\ndef old() -> int:\n    return 1\n"


def output(*paths: str) -> str:
    return json.dumps(
        {
            "summary": "Create the module.",
            "changes": [
                {
                    "path": path,
                    "operation": "create" if path == "pkg/new.py" else "update",
                    "content": "def new() -> int:\n    return 2\n",
                    "reason": "Follow the disclosed style.",
                }
                for path in paths or ("pkg/new.py",)
            ],
            "risks": [],
            "unknowns": [],
        }
    )


def references(values: tuple[str, ...]) -> tuple[RepositoryPath, ...]:
    return tuple(RepositoryPath(value) for value in values)


def agent_with(
    root: Path,
    text: str,
    refs: tuple[str, ...],
    *,
    allowed: tuple[str, ...] | None = None,
    reader: bool = True,
) -> tuple[CodingAgent, CodingRequest, StaticModel]:
    (root / "pkg").mkdir(exist_ok=True)
    agent, request, model = create_demo(root, text, (TARGET,))
    acquisition = agent.evidence_reader
    assert type(acquisition) is AuthorizedCodingEvidence
    scope = references(allowed if allowed is not None else refs)
    context = replace(acquisition.reads, allowed_paths=scope) if reader else None
    return (
        replace(
            agent, evidence_reader=AuthorizedCodingEvidence(acquisition.reads, context)
        ),
        replace(request, references=references(refs)),
        model,
    )


def write(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))


def test_references_reach_the_prompt_sorted_exact_and_separate(tmp_path: Path) -> None:
    write(
        tmp_path,
        {"pkg/old.py": STYLE, "pyproject.toml": "[tool.mypy]\nstrict = true\n"},
    )
    agent, request, model = agent_with(
        tmp_path, output(), ("pyproject.toml", "pkg/old.py")
    )
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.SUCCEEDED, result
    assert model.last_request is not None
    sent = json.loads(model.last_request.messages[-1].content)
    assert list(sent) == ["objective", "constraints", "targets", "read_only_context"]
    assert sent["targets"] == [
        {"path": "pkg/new.py", "operation": "create", "current_text": None}
    ]
    assert sent["read_only_context"] == [
        {"path": "pkg/old.py", "text": STYLE},
        {"path": "pyproject.toml", "text": "[tool.mypy]\nstrict = true\n"},
    ]
    assert result.evidence is not None
    assert result.evidence.reference_paths == references(
        ("pkg/old.py", "pyproject.toml")
    )


def test_reference_in_a_proposal_is_out_of_scope(tmp_path: Path) -> None:
    write(tmp_path, {"pkg/old.py": STYLE})
    agent, request, _ = agent_with(
        tmp_path, output("pkg/new.py", "pkg/old.py"), ("pkg/old.py",)
    )
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.OUTPUT_INVALID and result.proposal is None
    assert result.diagnostic is not None
    assert result.diagnostic.rejection is OutputRejection.PATH_OUT_OF_SCOPE
    assert (tmp_path / "pkg/old.py").read_bytes() == STYLE.encode()
    assert not (tmp_path / "pkg/new.py").exists()


@pytest.mark.parametrize(
    ("refs", "allowed", "reader"),
    [
        (("pkg/old.py",), ("other.py",), True),
        (("pkg/old.py",), None, False),
    ],
    ids=["other-scope", "no-reader"],
)
def test_reference_outside_disclosure_scope_is_denied_before_model(
    tmp_path: Path,
    refs: tuple[str, ...],
    allowed: tuple[str, ...] | None,
    reader: bool,
) -> None:
    write(tmp_path, {"pkg/old.py": STYLE, "other.py": "x = 1\n"})
    agent, request, model = agent_with(
        tmp_path, output(), refs, allowed=allowed, reader=reader
    )
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.INVALID_REQUEST
    assert result.acquisition_failure is AcquisitionFailure.DENIED
    assert model.calls == 0


def test_reference_scope_never_authorizes_a_target(tmp_path: Path) -> None:
    write(tmp_path, {"pkg/old.py": STYLE})
    agent, request, model = agent_with(tmp_path, output(), ("pkg/old.py",))
    update = CodingTarget(RepositoryPath("pkg/old.py"), FileChangeKind.UPDATE)
    smuggled = replace(request, targets=(update,), references=())
    result = asyncio.run(agent.propose(smuggled))
    assert result.acquisition_failure is AcquisitionFailure.DENIED
    assert model.calls == 0


@pytest.mark.parametrize(
    ("files", "refs", "failure"),
    [
        ({}, ("pkg/missing.py",), AcquisitionFailure.UNAVAILABLE),
        ({"pkg/old.py": STYLE}, ("pkg",), AcquisitionFailure.UNAVAILABLE),
        (
            {"pkg/big.py": "x" * (MAX_REFERENCE_BYTES + 1)},
            ("pkg/big.py",),
            AcquisitionFailure.BUDGET,
        ),
        (
            {f"pkg/p{n}.py": "y" * 6000 for n in range(3)},
            ("pkg/p0.py", "pkg/p1.py", "pkg/p2.py"),
            AcquisitionFailure.BUDGET,
        ),
    ],
    ids=["missing", "directory", "file-bound", "total-bound"],
)
def test_unreadable_or_oversized_reference_fails_closed(
    tmp_path: Path,
    files: dict[str, str],
    refs: tuple[str, ...],
    failure: AcquisitionFailure,
) -> None:
    write(tmp_path, files)
    agent, request, model = agent_with(tmp_path, output(), refs)
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.INVALID_REQUEST
    assert result.acquisition_failure is failure
    assert model.calls == 0


@pytest.mark.parametrize(
    "refs",
    [
        tuple(f"r{n}.py" for n in range(9)),
        ("a.py", "a.py"),
        ("a.py", "A.py"),
        ("pkg/new.py",),
        ("PKG/New.py",),
        (".env",),
        ("pkg/.secret",),
    ],
    ids=[
        "count",
        "duplicate",
        "alias",
        "target",
        "target-alias",
        "hidden",
        "hidden-part",
    ],
)
def test_request_reference_validation(tmp_path: Path, refs: tuple[str, ...]) -> None:
    _, request, _ = create_demo(tmp_path, output(), (TARGET,))
    with pytest.raises(ValueError):
        replace(request, references=references(refs))


def test_request_references_require_repository_paths(tmp_path: Path) -> None:
    _, request, _ = create_demo(tmp_path, output(), (TARGET,))
    with pytest.raises(TypeError):
        replace(request, references=("a.py",))  # type: ignore[arg-type]


def test_evidence_reference_bounds_and_disjointness() -> None:
    file = CodingFile(TARGET, None)
    small = RepositoryEvidence((RepositoryText("a.py", "a\n"),))
    assert CodingEvidence((file,), small).reference_paths == references(("a.py",))
    assert CodingEvidence((file,)).reference_paths == ()
    overlap = RepositoryEvidence((RepositoryText("pkg/new.py", "a\n"),))
    total = RepositoryEvidence(
        tuple(RepositoryText(f"r{n}.py", "z" * 6000) for n in range(3))
    )
    assert 3 * 6000 > MAX_REFERENCE_TOTAL_BYTES
    for bad in (overlap, total):
        with pytest.raises(ValueError):
            CodingEvidence((file,), bad)


def test_result_references_must_match_the_request(tmp_path: Path) -> None:
    write(tmp_path, {"pkg/old.py": STYLE})
    agent, request, _ = agent_with(tmp_path, output(), ("pkg/old.py",))
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.SUCCEEDED
    with pytest.raises(ValueError):
        CodingResult(
            result.status,
            replace(request, references=()),
            result.evidence,
            result.agent_result,
            result.proposal,
        )


def test_no_references_keeps_the_original_reader_contract(tmp_path: Path) -> None:
    agent, request, model = create_demo(tmp_path, output(), (TARGET,))
    (tmp_path / "pkg").mkdir()
    acquisition = agent.evidence_reader
    assert type(acquisition) is AuthorizedCodingEvidence
    assert acquisition.references is None and request.references == ()
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.SUCCEEDED
    assert model.last_request is not None
    assert "read_only_context" not in json.loads(
        model.last_request.messages[-1].content
    )
    assert isinstance(acquisition.reads, AuthorizedRepositoryEvidence)
