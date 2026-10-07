"""Scripted contract tests; no model, request dispatch or evidence acquisition."""

import ast
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
from legoai_engineering.analyst import sufficiency
from legoai_engineering.analyst.sufficiency import (
    EvidenceClarification,
    EvidenceManifest,
    EvidenceRequest,
    EvidenceRequestKind,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyError,
    EvidenceSufficiencyResult,
    GoverningSourceExpectation,
    SufficiencyDisposition,
    SufficiencyFailure,
)
from legoai_engineering.analyst.values import RepositoryEvidence
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath


def evidence(**files: str) -> RepositoryEvidence:
    return RepositoryEvidence(
        tuple(RepositoryText(p, t) for p, t in sorted(files.items()))
    )


def manifest() -> EvidenceManifest:
    return EvidenceManifest(
        "Explain current behavior", evidence(**{"a.py": "x = 1"}), "workspace-r1"
    )


def sufficient(m: EvidenceManifest) -> EvidenceSufficiencyAssessment:
    return EvidenceSufficiencyAssessment(
        m,
        SufficiencyDisposition.SUFFICIENT,
        "Scripted reviewable claim",
        (RepositoryPath(m.evidence.files[0].path),),
    )


def named(path: str) -> EvidenceRequest:
    return EvidenceRequest(
        EvidenceRequestKind.NAMED_EVIDENCE,
        "Current implementation",
        RepositoryPath(path),
    )


def role() -> EvidenceRequest:
    return EvidenceRequest(
        EvidenceRequestKind.SOURCE_ROLE,
        "Translation catalog containing decline messages",
    )


def clarification() -> EvidenceClarification:
    return EvidenceClarification(
        "timeout",
        EvidenceRequest(
            EvidenceRequestKind.OPERATOR_CLARIFICATION,
            "Which timeout?",
            choices=("connect", "read", "pool", "job"),
        ),
    )


def test_public_values_and_dispositions() -> None:
    assert {v.value for v in SufficiencyDisposition} == {
        "sufficient",
        "missing_governing_evidence",
        "unresolved_ambiguity",
    }
    for name in sufficiency.__all__:
        assert getattr(sufficiency, name).__module__ == sufficiency.__name__
    assert not any(name.startswith("_") for name in sufficiency.__all__)
    assert EvidenceSufficiencyResult(assessment=sufficient(manifest())).failure is None


def test_q21_missing_catalog_and_source_role() -> None:
    request = role()
    m = EvidenceManifest(
        "Update the decline message",
        evidence(
            **{
                "payments/errors.py": '"""Messages are in the translation catalog."""',
            }
        ),
        "payments-r1",
        (GoverningSourceExpectation("catalog", request),),
    )
    assert m.missing_expectations() == ("catalog",)
    with pytest.raises(EvidenceSufficiencyError) as caught:
        sufficient(m)
    assert caught.value.reason is SufficiencyFailure.PREREQUISITES_UNMET
    a = EvidenceSufficiencyAssessment(
        m,
        SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE,
        "Catalog content is absent",
        requests=(request,),
    )
    assert a.requests[0].path is None
    a.validate_for(m)


def test_declared_role_binding_checks_membership_not_truth() -> None:
    m = manifest()
    expectation = GoverningSourceExpectation(
        "catalog", role(), (RepositoryPath("a.py"),)
    )
    # The contract cannot establish that a.py really is a catalog.
    declared = replace(m, expectations=(expectation,))
    sufficient(declared).validate_for(declared)
    with pytest.raises(ValueError, match="not supplied"):
        replace(
            m,
            expectations=(
                replace(expectation, supplied_paths=(RepositoryPath("missing.py"),)),
            ),
        )


def test_q22_clarification_and_unrelated_evidence() -> None:
    c = clarification()
    m = EvidenceManifest(
        "Make the timeout longer",
        evidence(
            **{
                "net.py": "CONNECT=5\nREAD=30",
                "pool.py": "TIMEOUT=10",
            }
        ),
        "timeouts-r1",
        clarifications=(c,),
    )
    a = EvidenceSufficiencyAssessment(
        m,
        SufficiencyDisposition.UNRESOLVED_AMBIGUITY,
        "Intent does not distinguish candidates",
        requests=(c.request,),
    )
    a.validate_for(m)
    with pytest.raises(EvidenceSufficiencyError):
        sufficient(m)
    more = replace(
        m,
        evidence=evidence(
            **{
                "net.py": "CONNECT=5\nREAD=30",
                "pool.py": "TIMEOUT=10",
                "other.py": "OTHER=1",
            }
        ),
    )
    with pytest.raises(EvidenceSufficiencyError):
        sufficient(more)
    resolved = replace(m, clarifications=(replace(c, answer="read"),))
    sufficient(resolved).validate_for(resolved)
    with pytest.raises(EvidenceSufficiencyError, match="stale_assessment"):
        a.validate_for(resolved)
    with pytest.raises(ValueError, match="declared choice"):
        replace(c, answer="invented")


def test_q19_named_missing_implementation() -> None:
    request = named("cart/loyalty.py")
    m = EvidenceManifest(
        "Change loyalty percentage",
        evidence(
            **{
                "cart/checkout.py": "from cart.loyalty import apply_loyalty_discount",
            }
        ),
        "cart-r1",
        (GoverningSourceExpectation("implementation", request),),
    )
    a = EvidenceSufficiencyAssessment(
        m,
        SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE,
        "Caller is not implementation",
        requests=(request,),
    )
    assert m.missing_expectations() == ("implementation",)
    assert a.requests == (request,)  # data only: nothing was read
    with pytest.raises(EvidenceSufficiencyError):
        sufficient(m)
    added = replace(
        m,
        evidence=evidence(
            **{
                "cart/checkout.py": "from cart.loyalty import apply_loyalty_discount",
                "cart/loyalty.py": "def apply_loyalty_discount(x): return x * .95",
            }
        ),
    )
    assert added.missing_expectations() == ()
    sufficient(added).validate_for(added)


@pytest.mark.parametrize(
    "question,text",
    [
        ("Add currency to invoices", "class Invoice: total = 0"),
        ("Warn on failed login", "def login(): return False"),
        ("Create enrollment support", "def start(): return 'no enrollment support'"),
    ],
    ids=["q11", "q12", "c15"],
)
def test_future_behavior_controls(question: str, text: str) -> None:
    m = EvidenceManifest(
        question,
        evidence(**{"a.py": text}),
        "current-code",
        (GoverningSourceExpectation("base", named("a.py")),),
    )
    sufficient(m).validate_for(m)


@pytest.mark.parametrize(
    "change",
    [
        "question",
        "content",
        "path",
        "provenance",
        "expectation",
        "clarification",
        "unknown",
    ],
)
def test_exact_attribution_and_stale_rejection(change: str) -> None:
    m = manifest()
    a = sufficient(m)
    changed = {
        "question": replace(m, question="Different question"),
        "content": replace(m, evidence=evidence(**{"a.py": "x = 2"})),
        "path": replace(m, evidence=evidence(**{"b.py": "x = 1"})),
        "provenance": replace(m, provenance="workspace-r2"),
        "expectation": replace(
            m, expectations=(GoverningSourceExpectation("base", named("a.py")),)
        ),
        "clarification": replace(m, clarifications=(clarification(),)),
        "unknown": replace(m, unknowns=("Governing ownership unresolved",)),
    }[change]
    with pytest.raises(EvidenceSufficiencyError) as caught:
        a.validate_for(changed)
    assert caught.value.reason is SufficiencyFailure.STALE_ASSESSMENT
    assert m.identity() != changed.identity()


def test_identity_equality_hash_and_safe_repr() -> None:
    m = manifest()
    copy = replace(m, evidence=evidence(**{"a.py": "x = 1"}))
    assert m is not copy and m == copy and hash(m) == hash(copy)
    assert m.identity() == copy.identity()
    assert len(m.identity()) == len(m.evidence_identity) == 64
    sufficient(m).validate_for(copy)
    for value in (
        m,
        sufficient(m),
        role(),
        clarification(),
        GoverningSourceExpectation("private", role()),
    ):
        displayed = repr(value)
        assert not any(
            s in displayed
            for s in (
                "x = 1",
                "Explain current",
                "workspace-r1",
                "Translation",
                "Which timeout",
                "private",
            )
        )
    with pytest.raises(FrozenInstanceError):
        m.question = "tamper"  # type: ignore[misc]
    # Unordered declarations use canonical key ordering, never container identity.
    x = GoverningSourceExpectation("x", named("a.py"))
    y = GoverningSourceExpectation("y", role())
    assert (
        replace(m, expectations=(x, y)).identity()
        == replace(m, expectations=(y, x)).identity()
    )


def test_duplicate_expectations() -> None:
    m = manifest()
    x = GoverningSourceExpectation("x", named("a.py"))
    for declarations in (
        (x, x),
        (x, replace(x, key="other")),
        (x, GoverningSourceExpectation("x", role())),
    ):
        with pytest.raises(ValueError):
            replace(m, expectations=declarations)


def test_request_kinds_are_not_authority() -> None:
    assert len(EvidenceRequestKind) == 3
    for request in (named("not-authorized.py"), role(), clarification().request):
        assert not any(
            hasattr(request, attr)
            for attr in ("acquire", "authorize", "execute", "read_text", "targets")
        )
    for kind in (
        EvidenceRequestKind.SOURCE_ROLE,
        EvidenceRequestKind.OPERATOR_CLARIFICATION,
    ):
        with pytest.raises(ValueError, match="only named"):
            EvidenceRequest(kind, "Description", RepositoryPath("invented.py"))
    with pytest.raises(TypeError):
        EvidenceRequest("named_evidence", "text")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        GoverningSourceExpectation("wrong", clarification().request)
    with pytest.raises(ValueError):
        EvidenceClarification("wrong", named("a.py"))
    with pytest.raises(ValueError):
        EvidenceRequest(EvidenceRequestKind.NAMED_EVIDENCE, "missing path")
    with pytest.raises(ValueError):
        EvidenceRequest(EvidenceRequestKind.SOURCE_ROLE, "role", choices=("a", "b"))
    # Text resembling a path stays inert text, not a path or permission.
    assert (
        EvidenceRequest(EvidenceRequestKind.SOURCE_ROLE, "possibly catalog.json").path
        is None
    )


def test_operational_failures_are_separate() -> None:
    a = sufficient(manifest())
    for failure in SufficiencyFailure:
        assert EvidenceSufficiencyResult(failure=failure).assessment is None
        with pytest.raises(ValueError):
            EvidenceSufficiencyResult(a, failure)
    with pytest.raises(ValueError):
        EvidenceSufficiencyResult()
    with pytest.raises(TypeError):
        EvidenceSufficiencyResult(failure="model_failure")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(a, disposition="model_failure")  # type: ignore[arg-type]


def test_semantic_shape_and_declared_unknowns() -> None:
    m = manifest()
    with pytest.raises(EvidenceSufficiencyError):
        sufficient(replace(m, unknowns=("Unknown governing owner",)))
    for disposition in (
        SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE,
        SufficiencyDisposition.UNRESOLVED_AMBIGUITY,
    ):
        with pytest.raises(ValueError):
            EvidenceSufficiencyAssessment(m, disposition, "Missing request")
    with pytest.raises(ValueError):
        replace(sufficient(m), requests=(role(),))
    with pytest.raises(ValueError, match="not supplied"):
        replace(sufficient(m), governing_sources=(RepositoryPath("unsupplied.py"),))
    with pytest.raises(ValueError):
        replace(sufficient(m), governing_sources=())


@pytest.mark.parametrize("bad", ["", " ", "x" * 1025, "é" * 513, "\ud800"])
def test_request_text_bounds(bad: str) -> None:
    with pytest.raises(ValueError):
        EvidenceRequest(EvidenceRequestKind.SOURCE_ROLE, bad)


def test_bounds_and_invalid_values() -> None:
    m = manifest()
    for question in ("", "x" * 2049, "é" * 1025):
        with pytest.raises(ValueError):
            replace(m, question=question)
    assert len(replace(m, question="x" * 2048).question) == 2048
    with pytest.raises(ValueError):
        replace(m, provenance="x" * 257)
    with pytest.raises(ValueError):
        replace(sufficient(m), explanation="x" * 2049)
    for choices in (
        ("only",),
        ("same", "same"),
        ("x" * 257, "b"),
        tuple(str(i) for i in range(9)),
    ):
        with pytest.raises(ValueError):
            EvidenceRequest(
                EvidenceRequestKind.OPERATOR_CLARIFICATION, "Choose", choices=choices
            )
    with pytest.raises(ValueError):
        replace(clarification(), answer="x" * 1025)
    with pytest.raises(ValueError):
        replace(
            m,
            expectations=tuple(
                GoverningSourceExpectation(str(i), named(f"{i}.py")) for i in range(9)
            ),
        )
    with pytest.raises(ValueError):
        replace(
            m,
            clarifications=tuple(
                replace(clarification(), key=str(i)) for i in range(9)
            ),
        )
    with pytest.raises(ValueError):
        replace(m, unknowns=tuple(str(i) for i in range(9)))
    with pytest.raises(ValueError):
        replace(m, unknowns=("x" * 1025,))
    with pytest.raises(ValueError):
        EvidenceSufficiencyAssessment(
            m,
            SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE,
            "Need files",
            requests=tuple(named(f"{i}.py") for i in range(9)),
        )
    with pytest.raises(ValueError):
        GoverningSourceExpectation("not an identifier", role())
    with pytest.raises(ValueError):
        replace(m, expectations=[])  # type: ignore[arg-type]
    for files in (
        {},
        {f"{i}.py": "x" for i in range(9)},
        {"a.py": "x" * 8193},
        {f"{i}.py": "x" * 8192 for i in range(4)},
    ):
        with pytest.raises(ValueError):
            evidence(**files)


def test_architecture_no_io_or_new_runtime() -> None:
    tree = ast.parse(Path(sufficiency.__file__).read_text(encoding="utf-8"))
    imports: set[str | None] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module)
    assert imports == {
        "hashlib",
        "json",
        "dataclasses",
        "enum",
        "legoai_engineering.analyst.values",
        "legoai_engineering.repository.workspace",
    }
    assert not any(
        isinstance(n, (ast.AsyncFunctionDef, ast.Await)) for n in ast.walk(tree)
    )
    assert not any(
        isinstance(n, ast.Name) and n.id in {"open", "exec", "eval", "__import__"}
        for n in ast.walk(tree)
    )
