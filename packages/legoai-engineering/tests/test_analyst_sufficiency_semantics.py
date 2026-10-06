"""ENG-ANALYST-SUFFICIENCY-SEMANTICS-1: strict evidence sufficiency, unchanged parser."""

import asyncio
import json
from pathlib import Path

import pytest
from legoai.intelligence.model.values import ChatRole
from legoai.kernel.versions import Version
from repository_analyst import create_demo

from legoai_engineering.analyst.api import repository_analyst_definition
from legoai_engineering.analyst.values import RepositoryAnalysisStatus

POLICY_LEAD = "Status decision policy: "
GOVERNING = (
    "governing evidence is the supplied implementation, authoritative data or "
    "configuration, or ownership or relationship evidence without which the "
    "requested conclusion would require guessing"
)
SUCCEEDED = (
    "Choose succeeded only when the supplied evidence contains the governing "
    "evidence for the requested conclusion, such as the current implementation, the "
    "authoritative source, the governing owner or the relationship the question "
    "asks about"
)
NOT_CERTAINTY = (
    "succeeded means a defensible answer, not certainty: record residual "
    "uncertainty that does not prevent the conclusion in risks and unknowns while "
    "status stays succeeded"
)
INSUFFICIENT_LEAD = (
    "Choose insufficient_evidence when governing evidence needed for the requested "
    "conclusion is absent or materially ambiguous: "
)
QUALIFYING = (
    "the governing implementation is not supplied",
    "the authoritative data or configuration is not supplied",
    "several supplied candidates plausibly match and the evidence cannot "
    "establish which one is meant or authoritative",
    "the requested relationship cannot be established from the supplied evidence",
)
REFERENCE = (
    "A reference to unsupplied code or data, such as an import, a call site, a "
    "docstring naming a source or a stated path, shows that the source exists or "
    "where it lives, not what it contains"
)
CONTEXT = (
    "Unseen context that the conclusion does not depend on does not make the "
    "evidence insufficient; missing governing evidence does"
)
FUTURE = (
    "A requested behavior that does not exist yet is not by itself missing "
    "evidence, but only when the current implementation the change depends on is "
    "supplied; if that implementation is absent, choose insufficient_evidence"
)
AMBIGUITY = (
    "When supplied candidates remain ambiguous, list them in relevant_files, state "
    "the unresolved choice in unknowns and do not select one"
)
RELEVANCE = (
    "relevant_files may name supplied context or candidates under insufficient_evidence"
)
STRUCTURE = (
    "With insufficient_evidence, findings MUST be an empty array and unknowns MUST "
    "contain at least one item"
)
FINDINGS_MEAN_SUCCEEDED = (
    "If you have evidence-supported findings that answer the question, choose "
    "succeeded and put the remaining uncertainty in risks and unknowns"
)
ORDER = [
    GOVERNING,
    SUCCEEDED,
    NOT_CERTAINTY,
    None,  # the insufficient_evidence rule, parsed below
    REFERENCE,
    CONTEXT,
    FUTURE,
    AMBIGUITY,
    RELEVANCE,
    STRUCTURE,
    FINDINGS_MEAN_SUCCEEDED,
]


def policy() -> list[str]:
    """The status-policy sentences, in order."""
    instructions = repository_analyst_definition().instructions
    start = instructions.index(POLICY_LEAD) + len(POLICY_LEAD)
    end = instructions.index("Narrative is a hypothesis")
    return [s.strip() for s in instructions[start:end].split(". ") if s.strip()]


def qualifying() -> list[str]:
    """The insufficient_evidence clauses, one per qualifying situation."""
    rule = policy()[3]
    assert rule.startswith(INSUFFICIENT_LEAD)
    clauses = rule.removeprefix(INSUFFICIENT_LEAD).split("; ")
    return [c.removeprefix("or ") for c in clauses]


# Version, budget, sentence structure -----------------------------------------


def test_version_and_budget() -> None:
    definition = repository_analyst_definition()
    assert definition.agent_id.value == "repository-analyst"
    assert definition.behavior_version == Version(1, 0, 3)
    assert len(definition.system_prompt.encode()) + 32768 <= 49152
    assert len(definition.system_prompt.encode()) <= 4096  # compact, not a tutorial


def test_policy_sentences_are_exact_and_ordered() -> None:
    sentences = policy()
    assert len(sentences) == len(ORDER)
    for sentence, wanted in zip(sentences, ORDER, strict=True):
        if wanted is not None:
            assert sentence == wanted


# Semantic rules ----------------------------------------------------------------


def test_governing_evidence_is_defined() -> None:
    definition = policy()[0]
    assert definition.startswith("governing evidence is ")
    for kind in (
        "supplied implementation",
        "authoritative data or configuration",
        "ownership or relationship evidence",
    ):
        assert kind in definition
    assert definition.endswith("would require guessing")


def test_succeeded_requires_governing_evidence_not_certainty() -> None:
    sentences = policy()
    assert sentences[1].startswith("Choose succeeded only when")
    assert (
        "contains the governing evidence for the requested conclusion" in sentences[1]
    )
    assert "not certainty" in sentences[2]
    assert "risks and unknowns while status stays succeeded" in sentences[2]
    assert "does not prevent the conclusion" in sentences[2]


def test_insufficient_rule_lists_exactly_the_four_situations() -> None:
    clauses = qualifying()
    assert clauses == list(QUALIFYING)
    rule = policy()[3]
    assert "uncertain" not in rule  # uncertainty alone never qualifies
    assert not any(ch.isdigit() for ch in " ".join(policy()))  # never path-count based


@pytest.mark.parametrize(
    ("index", "subject"),
    [
        (0, "implementation"),
        (1, "authoritative data or configuration"),
        (2, "which one is meant or authoritative"),
        (3, "relationship"),
    ],
    ids=["implementation", "authoritative_source", "ambiguity", "relationship"],
)
def test_each_qualifying_situation(index: int, subject: str) -> None:
    assert subject in qualifying()[index]


def test_reference_is_not_content() -> None:
    rule = policy()[4]
    for reference in (
        "an import",
        "a call site",
        "a docstring naming a source",
        "a stated path",
    ):
        assert reference in rule
    assert rule.endswith("not what it contains")


def test_unseen_context_vs_missing_governing_evidence() -> None:
    rule = policy()[5]
    left, right = rule.split("; ")
    assert (
        "does not depend on" in left
        and "does not make the evidence insufficient" in left
    )
    assert right == "missing governing evidence does"
    assert "related files may exist elsewhere" not in " ".join(policy())


def test_future_behavior_rule_and_its_limit() -> None:
    rule = policy()[6]
    principle, limit = rule.split("; ")
    assert "does not exist yet is not by itself missing evidence" in principle
    assert (
        "only when the current implementation the change depends on is supplied"
        in principle
    )
    assert limit == "if that implementation is absent, choose insufficient_evidence"


def test_ambiguity_rule() -> None:
    rule = policy()[7]
    assert "list them in relevant_files" in rule
    assert "state the unresolved choice in unknowns" in rule
    assert rule.endswith("do not select one")


def test_relevance_and_structural_invariants() -> None:
    sentences = policy()
    assert sentences[8] == RELEVANCE
    assert sentences[9] == STRUCTURE
    assert sentences.index(RELEVANCE) < sentences.index(STRUCTURE)


def test_policy_is_generic_and_grants_nothing() -> None:
    text = " ".join(policy()).casefold()
    for word in (
        "forgeai", "fixture", "held-out", "heldout", "oracle", "evaluation",
        "probe", "q19", "q20", "q21", "q22", "c15", "loyalty", "catalog",
        "timeout", "schedule", ".py", "target", "authoriz", "permission",
        "request more", "read more", "fetch", "execute", "edit", "write",
    ):  # fmt: skip
        assert word not in text, word


# Governed requests -----------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_bytes(b"def a(): return 1\n")
    (tmp_path / "b.py").write_bytes(b"from a import a\n")
    return tmp_path


def answer(*, drop: tuple[str, ...] = (), **changes: object) -> str:
    result: dict[str, object] = {
        "status": "succeeded",
        "summary": "A defines the behavior.",
        "relevant_files": ["a.py"],
        "findings": [{"text": "Definition supplied.", "paths": ["a.py"]}],
        "risks": [],
        "unknowns": [],
    }
    result.update(changes)
    for name in drop:
        del result[name]
    return json.dumps(result)


def test_governed_system_and_user_requests(workspace: Path) -> None:
    analyst, request, model = create_demo(workspace, answer())
    result = asyncio.run(analyst.analyze(request))
    assert result.status is RepositoryAnalysisStatus.SUCCEEDED
    assert model.last_request is not None and model.calls == 1
    system, user = model.last_request.messages
    assert system.role is ChatRole.SYSTEM and user.role is ChatRole.USER
    assert system.content == repository_analyst_definition().system_prompt
    for sentence in (GOVERNING, SUCCEEDED, REFERENCE, FUTURE, AMBIGUITY, RELEVANCE):
        assert sentence in system.content
    for leaked in ("1.0.", "governing", "insufficient", "oracle"):
        assert leaked not in user.content
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


# Parser regressions (unchanged acceptance) -------------------------------------------

INSUFFICIENT = {"status": "insufficient_evidence", "findings": [], "unknowns": ["u"]}
FENCE = "```"
ACCEPTED = {
    "raw": answer(),
    "fenced": FENCE + "json\n" + answer() + "\n" + FENCE,
    "succeeded_risks_unknowns": answer(risks=["r"], unknowns=["u"]),
    "insufficient_with_relevant_files": json.dumps(
        {
            "summary": "Candidates supplied; the governing source is not.",
            "relevant_files": ["a.py", "b.py"],
            "risks": [],
            **INSUFFICIENT,
        }
    ),
    "insufficient_without_relevant_files": json.dumps(
        {
            "summary": "Nothing governing supplied.",
            "relevant_files": [],
            "risks": [],
            **INSUFFICIENT,
        }  # fmt: skip
    ),
}
REJECTED = {
    "insufficient_findings": answer(status="insufficient_evidence", unknowns=["u"]),
    "insufficient_empty_unknowns": answer(status="insufficient_evidence", findings=[]),
    "missing_field": answer(drop=("unknowns",)),
    "unexpected_field": answer(governing_files=["a.py"]),
    "wrong_type": answer(relevant_files="a.py"),
    "unknown_path": answer(relevant_files=["c.py"]),
    "bounds": answer(summary="x" * 2049),
    "duplicate_key": '{"status":"succeeded",' + answer()[1:],
}


@pytest.mark.parametrize("case", sorted(ACCEPTED))
def test_accepted_replies(workspace: Path, case: str) -> None:
    analyst, request, model = create_demo(workspace, ACCEPTED[case])
    result = asyncio.run(analyst.analyze(request))
    assert result.analysis is not None and model.calls == 1
    expected = (
        RepositoryAnalysisStatus.INSUFFICIENT_EVIDENCE
        if case.startswith("insufficient")
        else RepositoryAnalysisStatus.SUCCEEDED
    )
    assert result.status is expected
    if case == "insufficient_with_relevant_files":
        assert [p.value for p in result.analysis.relevant_files] == ["a.py", "b.py"]
        assert result.analysis.findings == ()


@pytest.mark.parametrize("case", sorted(REJECTED))
def test_rejected_replies_without_repair(workspace: Path, case: str) -> None:
    analyst, request, model = create_demo(workspace, REJECTED[case])
    result = asyncio.run(analyst.analyze(request))
    assert result.status is RepositoryAnalysisStatus.OUTPUT_INVALID
    assert result.analysis is None
    assert model.calls == 1  # no retry, repair or default
