"""ADR-021 JSON document representation, from the decoder up through each Agent.

The decoder only recognizes the outer envelope; every existing parser and
validator still runs on the decoded text. Agent cases use the public APIs and
the real governed fake Model, so model calls, effects and statuses are the
production ones.
"""

import ast
import asyncio
import json
from pathlib import Path

import pytest
from bounded_coding import create_demo as create_coding
from governed_demo import create_governed_demo
from legoai.execution.agent.values import AgentExecutionStatus, AgentId
from legoai.kernel.effects import EffectExtent
from repository_analyst import create_demo as create_analyst

from legoai_engineering._json_document import json_document
from legoai_engineering.analyst.values import RepositoryAnalysisStatus
from legoai_engineering.coding.definition import coding_definition
from legoai_engineering.coding.values import CodingStatus, CodingTarget
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.reviewer.api import IndependentReviewer
from legoai_engineering.reviewer.values import (
    ReviewMaterial,
    ReviewRequest,
    ReviewStatus,
)

DOC = '{"a": [1, 2], "b": "x"}'


def fenced(document: str, label: str = "json", newline: str = "\n") -> str:
    return f"```{label}{newline}{document}{newline}```"


# --- Decoder ---------------------------------------------------------------


@pytest.mark.parametrize(
    "reply",
    [DOC, f"  \n{DOC}\n\t", "not json", "Here it is: " + DOC, ""],
    ids=["raw", "raw-whitespace", "prose", "prose-with-inline-json", "empty"],
)
def test_non_fenced_replies_are_returned_unchanged(reply: str) -> None:
    assert json_document(reply) is reply


@pytest.mark.parametrize(
    "reply",
    [
        fenced(DOC),
        fenced(DOC, label=""),
        fenced(DOC, newline="\r\n"),
        "\n  " + fenced(DOC) + "\n\n",
        fenced('{\n  "a": [1, 2],\n  "b": "x"\n}'),
        fenced('{"a": [1, 2], "b": "```x```"}'),  # backticks inside a string
    ],
    ids=[
        "json-label",
        "no-label",
        "crlf",
        "surrounding-whitespace",
        "multiline",
        "backticks-in-string",
    ],
)
def test_exact_fences_yield_the_document(reply: str) -> None:
    decoded = json_document(reply)
    assert decoded != reply
    assert json.loads(decoded) == json.loads(decoded.strip())  # one document


@pytest.mark.parametrize(
    "reply",
    [
        "Here is the JSON:\n" + fenced(DOC),
        fenced(DOC) + "\nHope this helps.",
        fenced(DOC, label="JSON"),
        fenced(DOC, label="jsonc"),
        fenced(DOC, label="json5"),
        fenced(DOC, label="python"),
        fenced(DOC, label="json "),
        fenced(DOC, label="json x"),
        "```json " + DOC + "\n```",
        "```" + DOC + "```",
        "```json\n" + DOC,
        "```json\n" + DOC + "\n``` end",
        "```json\n" + DOC + "\n````",
    ],
    ids=[
        "prose-before",
        "prose-after",
        "label-JSON",
        "label-jsonc",
        "label-json5",
        "label-python",
        "label-trailing-space",
        "text-after-label",
        "json-on-fence-line",
        "single-line-fence",
        "missing-closing-fence",
        "text-after-closing-fence",
        "four-backtick-close",
    ],
)
def test_other_envelopes_are_returned_unchanged_and_stay_invalid(reply: str) -> None:
    assert json_document(reply) is reply
    with pytest.raises(ValueError):
        json.loads(reply)


@pytest.mark.parametrize(
    "reply",
    [
        fenced(DOC) + "\n" + fenced(DOC),
        fenced(fenced(DOC)),
        "```json\n```",
        "```json\n\n```",
        fenced('{"a": '),
        fenced(DOC + "\n" + DOC),
        fenced(DOC + " trailing"),
    ],
    ids=[
        "two-fences",
        "nested-fences",
        "empty-fence-two-lines",
        "empty-fence",
        "malformed-json",
        "two-documents",
        "trailing-text",
    ],
)
def test_decoded_text_that_is_not_one_document_is_rejected(reply: str) -> None:
    with pytest.raises(ValueError):
        json.loads(json_document(reply))


def test_decoder_is_pure_standard_text_handling() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "legoai_engineering"
    tree = ast.parse((root / "_json_document.py").read_text(encoding="utf-8"))
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)]
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not names & {"open", "print", "eval", "exec", "loads", "search", "find"}
    assert not any("ollama" in name.lower() for name in names)  # provider-neutral


# --- Coding Agent ------------------------------------------------------------


def coding_reply(**fields: object) -> str:
    value: dict[str, object] = {
        "summary": "Change the text.",
        "changes": [
            {
                "path": "example.py",
                "operation": "update",
                "content": "new\n",
                "reason": "Meet the objective.",
            }
        ],
        "risks": [],
        "unknowns": ["Not executed."],
    }
    value.update(fields)
    return json.dumps(value)


def coding_change(**fields: object) -> list[dict[str, object]]:
    change: dict[str, object] = {
        "path": "example.py",
        "operation": "update",
        "content": "new\n",
        "reason": "Meet the objective.",
    }
    change.update(fields)
    return [change]


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "example.py").write_text("GREETING = 'hello'\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("def a(): return 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("from a import a\n", encoding="utf-8")
    return tmp_path


def propose(workspace: Path, reply: str):  # type: ignore[no-untyped-def]
    target = CodingTarget(RepositoryPath("example.py"), FileChangeKind.UPDATE)
    agent, request, model = create_coding(workspace, reply, (target,))
    return asyncio.run(agent.propose(request)), model


def test_coding_fenced_reply_equals_the_raw_reply(workspace: Path) -> None:
    raw, raw_model = propose(workspace, coding_reply())
    for reply in (fenced(coding_reply()), fenced(coding_reply(), label="")):
        result, model = propose(workspace, reply)
        assert result.status is CodingStatus.SUCCEEDED
        assert result.proposal == raw.proposal
        assert model.calls == raw_model.calls == 1
        assert result.agent_result is not None
        assert result.agent_result.model_execution is not None
        assert result.agent_result.model_execution.effect is EffectExtent.COMPLETED


INVALID_INSIDE_FENCE = {
    "duplicate-key": '{"summary":"a",' + coding_reply()[1:],
    "schema-extra-field": coding_reply(files=[]),
    "untargeted-path": coding_reply(changes=coding_change(path="other.py")),
    "invalid-path": coding_reply(changes=coding_change(path="exa?mple.py")),
    "wrong-operation": coding_reply(changes=coding_change(operation="create")),
    "content-over-limit": coding_reply(changes=coding_change(content="x" * 8193)),
}
REJECTED_ENVELOPES = {
    "prose-before": "Here:\n" + fenced(coding_reply()),
    "prose-after": fenced(coding_reply()) + "\nDone.",
    "unknown-label": fenced(coding_reply(), label="python"),
    "single-line": "```" + coding_reply() + "```",
    "two-fences": fenced(coding_reply()) + "\n" + fenced(coding_reply()),
    "nested": fenced(fenced(coding_reply())),
    "empty": "```json\n\n```",
    "malformed": fenced('{"summary": '),
    "two-documents": fenced(coding_reply() + "\n" + coding_reply()),
    "trailing-text": fenced(coding_reply() + " trailing"),
    "inline-json-in-prose": "The proposal is " + coding_reply(),
}


@pytest.mark.parametrize(
    "reply",
    [fenced(r) for r in INVALID_INSIDE_FENCE.values()]
    + list(REJECTED_ENVELOPES.values()),
    ids=[f"fenced-{k}" for k in INVALID_INSIDE_FENCE] + list(REJECTED_ENVELOPES),
)
def test_coding_rejections_keep_the_existing_status(
    workspace: Path, reply: str
) -> None:
    result, model = propose(workspace, reply)
    assert result.status is CodingStatus.OUTPUT_INVALID
    assert result.proposal is None and model.calls == 1  # no retry
    assert result.agent_result is not None
    assert result.agent_result.status is AgentExecutionStatus.SUCCEEDED
    assert result.agent_result.model_execution is not None
    assert result.agent_result.model_execution.effect is EffectExtent.COMPLETED


def test_output_size_is_validated_on_the_whole_fenced_reply(workspace: Path) -> None:
    limit = coding_definition().output_contract.max_bytes
    padded = coding_reply() + " " * (limit - len(coding_reply()))
    assert len(padded.encode()) == limit
    accepted, _ = propose(workspace, padded)
    assert accepted.status is CodingStatus.SUCCEEDED
    rejected, model = propose(workspace, fenced(padded))
    assert rejected.status is CodingStatus.OUTPUT_INVALID
    assert rejected.agent_result is not None
    assert rejected.agent_result.status is AgentExecutionStatus.OUTPUT_INVALID
    assert model.calls == 1


# --- Independent Reviewer ----------------------------------------------------


def review_reply(**changes: object) -> str:
    value: dict[str, object] = {
        "decision": "accept",
        "summary": "The textual proposal meets the supplied criterion.",
        "findings": [],
        "risks": [],
        "unknowns": [],
    }
    value.update(changes)
    return json.dumps(value)


def review(reply: str):  # type: ignore[no-untyped-def]
    demo = create_governed_demo(reply)
    request = ReviewRequest(
        AgentId("proposal-author"),
        "Evaluate the proposal.",
        ("Check input handling.",),
        "Convert the input string into an integer.",
        (ReviewMaterial("requirement", "Missing input must fail explicitly."),),
        demo.context,
    )
    return asyncio.run(IndependentReviewer(demo.runtime).review(request)), demo.model


def test_review_fenced_reply_equals_the_raw_reply() -> None:
    raw, _ = review(review_reply())
    for reply in (fenced(review_reply()), fenced(review_reply(), label="")):
        result, model = review(reply)
        assert result.status is ReviewStatus.COMPLETED
        assert result.review == raw.review and model.calls == 1


@pytest.mark.parametrize(
    "reply",
    [
        fenced(review_reply(decision="changes_required")),  # no blocking finding
        fenced(review_reply(decision="approve")),
        fenced(review_reply(extra=1)),
        fenced(review_reply()) + "\nThanks.",
        fenced(review_reply(), label="markdown"),
    ],
    ids=[
        "decision-inconsistent",
        "decision-invalid",
        "schema-invalid",
        "prose-after",
        "unknown-label",
    ],
)
def test_review_rejections_keep_the_existing_status(reply: str) -> None:
    result, model = review(reply)
    assert result.status is ReviewStatus.OUTPUT_INVALID
    assert result.review is None and model.calls == 1


# --- Repository Analyst ------------------------------------------------------


def analysis_reply(**changes: object) -> str:
    value: dict[str, object] = {
        "status": "succeeded",
        "summary": "A defines the behavior.",
        "relevant_files": ["a.py"],
        "findings": [{"text": "Definition supplied.", "paths": ["a.py"]}],
        "risks": [],
        "unknowns": ["Execution was not observed."],
    }
    value.update(changes)
    return json.dumps(value)


def analyze(workspace: Path, reply: str):  # type: ignore[no-untyped-def]
    analyst, request, model = create_analyst(workspace, reply)
    return asyncio.run(analyst.analyze(request)), model


def test_analysis_fenced_reply_equals_the_raw_reply(workspace: Path) -> None:
    raw, _ = analyze(workspace, analysis_reply())
    for reply in (fenced(analysis_reply()), fenced(analysis_reply(), label="")):
        result, model = analyze(workspace, reply)
        assert result.status is RepositoryAnalysisStatus.SUCCEEDED
        assert result.analysis == raw.analysis and model.calls == 1


@pytest.mark.parametrize(
    "reply",
    [
        fenced(analysis_reply(relevant_files=["invented.py"])),
        fenced(analysis_reply(extra="unexpected")),
        "Analysis:\n" + fenced(analysis_reply()),
    ],
    ids=["invented-path", "schema-invalid", "prose-before"],
)
def test_analysis_rejections_keep_the_existing_status(
    workspace: Path, reply: str
) -> None:
    result, model = analyze(workspace, reply)
    assert result.status is RepositoryAnalysisStatus.OUTPUT_INVALID
    assert result.analysis is None and model.calls == 1
