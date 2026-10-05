"""ENG-ANALYST-PROMPT-1: real governed requests and unchanged parser rules."""

import asyncio
import json
from pathlib import Path

import pytest
from legoai.intelligence.model.values import ChatRole
from legoai.kernel.effects import EffectExtent
from legoai.kernel.versions import Version
from repository_analyst import create_demo

from legoai_engineering.analyst.api import repository_analyst_definition
from legoai_engineering.analyst.values import RepositoryAnalysisStatus

FIELDS = ("status", "summary", "relevant_files", "findings", "risks", "unknowns")
SHAPE = (
    '{"status":"<succeeded-or-insufficient_evidence>",'
    '"summary":"<brief summary>","relevant_files":["<supplied relative path>"],'
    '"findings":[{"text":"<finding>","paths":["<supplied relative path>"]}],'
    '"risks":["<risk>"],"unknowns":["<unknown>"]}'
)
SHAPE_LEAD = "Shape illustration only; replace the placeholders with actual values: "


def answer(*, drop: tuple[str, ...] = (), **changes: object) -> str:
    result: dict[str, object] = {
        "status": "succeeded",
        "summary": "A defines the behavior.",
        "relevant_files": ["a.py"],
        "findings": [{"text": "Definition supplied.", "paths": ["a.py"]}],
        "risks": [],
        "unknowns": ["Execution was not observed."],
    }
    result.update(changes)
    for name in drop:
        del result[name]
    return json.dumps(result)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_bytes(b"def a(): return 1\n")
    (tmp_path / "b.py").write_bytes(b"from a import a\n")
    return tmp_path


def sentences(text: str) -> list[str]:
    return [s.strip() for s in text.replace(SHAPE, "").split(". ") if s.strip()]


def test_definition_version_and_guidance() -> None:
    definition = repository_analyst_definition()
    assert definition.agent_id.value == "repository-analyst"
    assert definition.behavior_version == Version(1, 0, 1)
    for text in (
        "Return only a JSON object with exactly these six top-level keys: status, "
        "summary, relevant_files, findings, risks, unknowns.",
        "All six keys are required; none is optional.",
        "The risks key and the unknowns key are two separate keys: each MUST appear "
        "on its own, and they must never be merged into one key.",
        "risks is a required array of at most 8 nonblank strings of <=1024 bytes "
        "describing risks supported by the supplied evidence; it may be empty.",
        "unknowns is a required array of at most 8 nonblank strings of <=1024 bytes "
        "describing relevant unresolved or missing evidence; it may be empty.",
        SHAPE_LEAD + SHAPE,
        "For insufficient_evidence give at least one unknown and no findings.",
    ):
        assert text in definition.instructions
    assert "risks and unknowns (" not in definition.instructions
    assert "ForgeAI" not in definition.instructions
    assert len(definition.system_prompt.encode()) + 32768 <= 49152


def test_risks_and_unknowns_are_each_their_own_required_field() -> None:
    instructions = repository_analyst_definition().instructions
    start = instructions.index(SHAPE_LEAD) + len(SHAPE_LEAD)
    shape, _ = json.JSONDecoder().raw_decode(instructions, start)
    assert list(shape) == list(FIELDS)  # six distinct top-level keys, in order
    assert type(shape["risks"]) is list and type(shape["unknowns"]) is list
    assert shape["risks"] != shape["unknowns"]
    positions = [instructions.index(name) for name in FIELDS]
    assert positions == sorted(positions)
    for own, other in (("risks", "unknowns"), ("unknowns", "risks")):
        [definition] = [
            s for s in sentences(instructions) if s.startswith(own + " is ")
        ]
        assert "required array" in definition and other not in definition


def test_governed_request_and_user_payload(workspace: Path) -> None:
    analyst, request, model = create_demo(workspace, answer())
    result = asyncio.run(analyst.analyze(request))
    assert result.status is RepositoryAnalysisStatus.SUCCEEDED
    assert result.agent_result is not None
    assert result.agent_result.definition == repository_analyst_definition()
    assert result.agent_result.definition.behavior_version == Version(1, 0, 1)
    assert model.last_request is not None and model.calls == 1
    system, user = model.last_request.messages
    assert system.role is ChatRole.SYSTEM and user.role is ChatRole.USER
    assert system.content == repository_analyst_definition().system_prompt
    assert SHAPE in system.content
    expected = json.dumps(
        {
            "question": request.question,
            "files": [
                {"path": "a.py", "text": "def a(): return 1\n"},
                {"path": "b.py", "text": "from a import a\n"},
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    assert user.content.encode() == expected.encode()


FENCE = "```"
INVALID = {
    "missing_risks": answer(drop=("risks",)),
    "missing_unknowns": answer(drop=("unknowns",)),
    "missing_both": answer(drop=("risks", "unknowns")),
    "combined_field": answer(
        drop=("risks", "unknowns"), risks_and_unknowns=["Execution was not observed."]
    ),
    "unexpected_field": answer(extra="not permitted"),
    "risks_type": answer(risks="none"),
    "risks_null": answer(risks=None),
    "unknowns_type": answer(unknowns={"note": "x"}),
    "unknowns_blank": answer(unknowns=[" "]),
    "risks_oversized": answer(risks=["x" * 1025]),
    "unknowns_count": answer(unknowns=["u"] * 9),
    "findings_shape": answer(findings={"text": "x", "paths": ["a.py"]}),
    "finding_entry": answer(findings=[{"text": "x"}]),
    "relevant_files_shape": answer(relevant_files="a.py"),
    "relevant_files_duplicate": answer(relevant_files=["a.py", "a.py"]),
    "insufficient_without_unknowns": answer(
        status="insufficient_evidence", findings=[], unknowns=[]
    ),
    "insufficient_with_findings": answer(status="insufficient_evidence"),
    "membership_relevant": answer(relevant_files=["c.py"]),
    "membership_finding": answer(findings=[{"text": "x", "paths": ["c.py"]}]),
    "duplicate_key": '{"status":"succeeded",' + answer()[1:],
}
VALID = {
    "raw": answer(),
    "fenced": FENCE + "json\n" + answer() + "\n" + FENCE,
    "empty_narrative": answer(unknowns=[]),
    "insufficient": answer(status="insufficient_evidence", findings=[]),
}


@pytest.mark.parametrize("case", sorted(VALID))
def test_valid_replies_are_accepted_unchanged(workspace: Path, case: str) -> None:
    analyst, request, model = create_demo(workspace, VALID[case])
    result = asyncio.run(analyst.analyze(request))
    expected = (
        RepositoryAnalysisStatus.INSUFFICIENT_EVIDENCE
        if case == "insufficient"
        else RepositoryAnalysisStatus.SUCCEEDED
    )
    assert result.status is expected and result.analysis is not None
    assert model.calls == 1


@pytest.mark.parametrize("case", sorted(INVALID))
def test_contract_violations_are_rejected_without_repair(
    workspace: Path, case: str
) -> None:
    analyst, request, model = create_demo(workspace, INVALID[case])
    result = asyncio.run(analyst.analyze(request))
    assert result.status is RepositoryAnalysisStatus.OUTPUT_INVALID
    assert result.analysis is None
    assert model.calls == 1  # no retry
    assert result.agent_result is not None
    assert result.agent_result.model_execution is not None
    assert result.agent_result.model_execution.effect is EffectExtent.COMPLETED
