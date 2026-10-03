"""ENG-CODING-PROMPT-1: real governed requests and unchanged proposal rules."""

import asyncio
import json
from pathlib import Path

import pytest
from bounded_coding import create_demo
from legoai.intelligence.model.values import ChatRole
from legoai.kernel.effects import EffectExtent
from legoai.kernel.versions import Version

from legoai_engineering.coding.definition import coding_definition
from legoai_engineering.coding.values import CodingStatus, CodingTarget
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath

SHAPE = (
    '{"path":"<repository path>","operation":"<create-or-update>",'
    '"content":"<complete file content>","reason":"<brief explanation>"}'
)


def proposal(case: str = "valid") -> str:
    change: dict[str, object] = {
        "path": "example.py",
        "operation": "update",
        "content": "new\n",
        "reason": "Meet the objective.",
    }
    if case == "missing":
        del change["reason"]
    elif case == "blank":
        change["reason"] = " "
    elif case == "oversized":
        change["reason"] = "x" * 1025
    elif case == "type":
        change["reason"] = 7
    elif case == "extra":
        change["extra"] = "not permitted"
    elif case == "path":
        change["path"] = "../outside.py"
    elif case == "target":
        change["path"] = "other.py"
    elif case == "operation":
        change["operation"] = "create"
    elif case == "content":
        change["content"] = "x" * 8193
    value = {
        "summary": "Change text.",
        "changes": [change, change] if case == "duplicate_target" else [change],
        "risks": [],
        "unknowns": [],
    }
    result = json.dumps(value)
    return '{"summary":"duplicate",' + result[1:] if case == "duplicate_key" else result


def test_definition_version_and_guidance() -> None:
    definition = coding_definition()
    assert definition.behavior_version == Version(1, 0, 1)
    for text in (
        "Every change object MUST contain exactly these four keys: path, operation, content, reason.",
        "None of these four keys is optional.",
        "Reason is a brief explanation of how that specific change addresses the supplied objective and constraints.",
        "It is descriptive explanation, not authorization, evidence that checks ran, or verified correctness.",
        "Reason is nonblank text <=1024 bytes.",
        "Shape illustration only; replace the placeholders with actual values:",
        SHAPE,
    ):
        assert text in definition.instructions


def test_governed_request_and_user_payload(tmp_path: Path) -> None:
    (tmp_path / "example.py").write_bytes(b"old\n")
    target = CodingTarget(RepositoryPath("example.py"), FileChangeKind.UPDATE)
    agent, request, model = create_demo(tmp_path, proposal(), (target,))
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.SUCCEEDED
    assert result.agent_result is not None
    assert result.agent_result.definition == coding_definition()
    assert result.agent_result.definition.behavior_version == Version(1, 0, 1)
    assert model.last_request is not None and model.calls == 1
    system, user = model.last_request.messages
    assert system.role is ChatRole.SYSTEM and user.role is ChatRole.USER
    assert system.content == coding_definition().system_prompt
    assert SHAPE in system.content
    expected = json.dumps(
        {
            "objective": request.objective,
            "constraints": request.constraints,
            "targets": [
                {"path": "example.py", "operation": "update", "current_text": "old\n"}
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    assert user.content.encode() == expected.encode()


@pytest.mark.parametrize("fenced", [False, True])
@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "missing",
        "blank",
        "oversized",
        "type",
        "extra",
        "duplicate_key",
        "path",
        "target",
        "operation",
        "duplicate_target",
        "content",
    ],
)
def test_parser_contract_and_single_call(
    tmp_path: Path, case: str, fenced: bool
) -> None:
    path = tmp_path / "example.py"
    path.write_text("old\n", encoding="utf-8")
    output = proposal(case)
    if fenced:
        output = "```json\n" + output + "\n```"
    targets = (CodingTarget(RepositoryPath("example.py"), FileChangeKind.UPDATE),)
    agent, request, model = create_demo(tmp_path, output, targets)
    result = asyncio.run(agent.propose(request))
    assert model.calls == 1
    assert (
        result.agent_result is not None
        and result.agent_result.model_execution is not None
    )
    assert result.agent_result.model_execution.effect is EffectExtent.COMPLETED
    assert path.read_text(encoding="utf-8") == "old\n"
    if case != "valid":
        assert result.status is CodingStatus.OUTPUT_INVALID and result.proposal is None
    else:
        assert result.status is CodingStatus.SUCCEEDED and result.proposal is not None
        assert result.proposal.reasons == ("Meet the objective.",)
        plain_agent, plain_request, _ = create_demo(tmp_path, proposal(), targets)
        plain = asyncio.run(plain_agent.propose(plain_request))
        assert result.proposal == plain.proposal
