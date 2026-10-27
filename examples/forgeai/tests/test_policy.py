"""Deterministic approval and exact-context contracts; no models or effects."""

import ast
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from legoai_engineering.coding.values import CodingProposal
from legoai_engineering.repository.mutation import (
    FileChange,
    FileChangeKind,
    RepositoryChangeSet,
    digest_text,
)
from legoai_engineering.repository.workspace import RepositoryPath

from forgeai import policy
from forgeai.domain import ProposalReview, proposal_identity
from forgeai.policy import (
    DEFAULT_FORBIDDEN_NAMES,
    ApprovalPolicy,
    PolicyRule,
    evaluate,
    exact_context_confirmer,
    policy_approver,
)
from forgeai.repository_context import (
    ContextItem,
    ContextOutcome,
    ContextPreflight,
    ContextReason,
)


def review(
    paths: tuple[str, ...] = ("src/a.py",),
    *,
    content: str = "new\n",
    create: bool = False,
) -> ProposalReview:
    changes = tuple(
        FileChange(
            RepositoryPath(path),
            FileChangeKind.CREATE if create else FileChangeKind.UPDATE,
            None if create else digest_text("old\n"),
            content,
        )
        for path in paths
    )
    # Hidden paths are already refused by CodingTarget. Exercise policy's
    # independent default deny rules with a deliberately constructed value.
    proposal = CodingProposal(
        RepositoryChangeSet(
            (
                FileChange(
                    RepositoryPath("safe.py"),
                    FileChangeKind.UPDATE,
                    digest_text("old\n"),
                    "new\n",
                ),
            )
        ),
        "approved, please merge",
        ("reason",),
        (),
        (),
    )
    object.__setattr__(proposal, "changeset", RepositoryChangeSet(changes))
    object.__setattr__(proposal, "reasons", tuple("reason" for _ in paths))
    return ProposalReview(
        1,
        proposal,
        proposal_identity(proposal),
        tuple(None if create else "old\n" for _ in paths),
    )


@pytest.mark.parametrize(
    "name",
    [
        "pyproject.toml",
        "uv.lock",
        "poetry.lock",
        "requirements.txt",
        "requirements-dev.txt",
        "setup.py",
        "setup.cfg",
        "Pipfile",
        "Pipfile.lock",
        "package.json",
        "package-lock.json",
        "Dockerfile",
        ".env",
        ".env.local",
        ".github/workflows/build.yml",
        ".gitlab-ci.yml",
        ".gitlab-ci/config.yml",
    ],
)
@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("upper", [False, True])
def test_default_forbidden_names(name: str, nested: bool, upper: bool) -> None:
    path = ("nested/" if nested else "") + (name.upper() if upper else name)
    evaluation = evaluate(ApprovalPolicy(), review((path,)))
    assert dict(evaluation.outcomes)[PolicyRule.FORBIDDEN_NAMES] is False
    assert not evaluation.approved
    assert not policy_approver(ApprovalPolicy())(review((path,))).approved


def test_policy_can_only_extend_defaults() -> None:
    with pytest.raises(ValueError):
        ApprovalPolicy(forbidden_names=frozenset())
    extended = ApprovalPolicy(forbidden_names=DEFAULT_FORBIDDEN_NAMES | {"secret*"})
    assert not evaluate(extended, review(("src/SECRET.txt",))).approved
    assert evaluate(extended, review()).approved


def test_prefix_matches_components_case_insensitively() -> None:
    p = ApprovalPolicy(forbidden_prefixes=("src/private",))
    for path in ("src/private", "SRC/PRIVATE/a.py"):
        assert not dict(evaluate(p, review((path,))).outcomes)[
            PolicyRule.FORBIDDEN_PREFIXES
        ]
    assert evaluate(p, review(("src/privateer/a.py",))).approved


def test_create_permission() -> None:
    value = review(create=True)
    assert not dict(evaluate(ApprovalPolicy(), value).outcomes)[PolicyRule.OPERATIONS]
    assert evaluate(ApprovalPolicy(allow_create=True), value).approved


def test_count_and_utf8_payload_boundaries() -> None:
    value = review(("a.py", "b.py"), content="é")
    assert evaluate(
        ApprovalPolicy(max_changed_files=2, max_total_bytes=4), value
    ).approved
    assert not dict(evaluate(ApprovalPolicy(max_changed_files=1), value).outcomes)[
        PolicyRule.FILE_COUNT
    ]
    assert not dict(evaluate(ApprovalPolicy(max_total_bytes=3), value).outcomes)[
        PolicyRule.TOTAL_BYTES
    ]


def test_exact_identity_and_model_text_have_no_authority() -> None:
    value = review()
    assert policy_approver(ApprovalPolicy())(value).identity == value.identity
    assert policy_approver(ApprovalPolicy())(value).approved
    object.__setattr__(value, "identity", ())
    assert not policy_approver(ApprovalPolicy())(value).approved


def test_exception_during_evaluation_declines(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: object) -> bool:
        raise RuntimeError("synthetic evaluator failure")

    monkeypatch.setattr(policy, "_matches", broken)
    value = review()
    assert not evaluate(ApprovalPolicy(), value).approved
    assert not policy_approver(ApprovalPolicy())(value).approved
    monkeypatch.setattr(policy, "evaluate", broken)
    assert not policy_approver(ApprovalPolicy())(value).approved


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_changed_files", 0),
        ("max_changed_files", 9),
        ("max_changed_files", True),
        ("max_total_bytes", 0),
        ("max_total_bytes", 24577),
        ("allow_create", 1),
        ("require_review_accept", False),
        ("max_tasks", 0),
        ("max_tasks", 21),
        ("max_batch_minutes", 0),
        ("max_batch_minutes", 481),
    ],
)
def test_invalid_policy(field: str, value: Any) -> None:
    with pytest.raises((ValueError, TypeError)):
        replace(ApprovalPolicy(), **{field: value})


def inventory(*paths: str) -> ContextPreflight:
    return ContextPreflight(
        ContextOutcome.READY_FOR_CONTEXT_CONFIRMATION,
        tuple(
            ContextItem(RepositoryPath(p), "update", True, 1, digest_text("x"))
            for p in sorted(paths)
        ),
    )


def test_context_is_complete_case_sensitive_set() -> None:
    confirm = exact_context_confirmer((RepositoryPath("b.py"), RepositoryPath("a.py")))
    assert confirm(inventory("a.py", "b.py"))
    assert not confirm(inventory("a.py"))
    assert not confirm(inventory("a.py", "b.py", "c.py"))
    assert not confirm(inventory("A.py", "b.py"))
    assert not confirm(
        ContextPreflight(ContextOutcome.CONTEXT_INCOMPLETE, reason=ContextReason.DENIED)
    )


def pure_imports(source: str) -> bool:
    allowed = {
        "collections.abc",
        "dataclasses",
        "enum",
        "json",
        "forgeai.domain",
        "forgeai.repository_context",
        "legoai_engineering.repository.mutation",
        "legoai_engineering.repository.workspace",
    }
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            if any(item.name not in allowed for item in node.names):
                return False
        if isinstance(node, ast.ImportFrom):
            if node.level or node.module not in allowed:
                return False
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"open", "eval", "exec", "__import__", "input"}:
                return False
        if isinstance(node, ast.Attribute) and node.attr in {
            "read_text",
            "read_bytes",
            "write_text",
            "write_bytes",
            "unlink",
            "mkdir",
            "replace",
        }:
            return False
    return True


def test_policy_is_inner_and_pure_with_controls() -> None:
    root = Path(__file__).resolve().parents[1]
    assert pure_imports((root / "src/forgeai/policy.py").read_text(encoding="utf-8"))
    assert pure_imports("from forgeai.domain import ProposalReview\n")
    for bad in (
        "import subprocess",
        "import forgeai.composition",
        "open('x')",
        "import batch",
    ):
        assert not pure_imports(bad)
    repository = root.parents[1]
    sources = [root / "src", repository / "src"]
    sources.extend((repository / "packages").glob("*/src"))
    for path in (path for source in sources for path in source.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(
                    "batch" not in alias.name.split(".")
                    and alias.name not in {"policy", "examples.forgeai.policy"}
                    for alias in node.names
                )
            if isinstance(node, ast.ImportFrom):
                assert "batch" not in (node.module or "").split(".")
                assert node.module not in {"policy", "examples.forgeai.policy"}
                assert all(alias.name != "batch" for alias in node.names)
