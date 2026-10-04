"""DISCOVERY-1 deterministic/security contracts; no live model or Docker."""

from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from pathlib import Path

import pytest
from governed_demo import NOW, WORKSPACE, create_governed_demo
from legoai.governance.ports import (
    AuthorizationDecision,
    AuthorizationOutcome,
    SecurityContext,
)
from legoai.governance.values import Approval, ApprovalId
from legoai.kernel.errors import ErrorCategory
from legoai.kernel.identity import TenantId
from legoai.reference.governance import (
    DeterministicAuthorizationEvaluator,
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)

from legoai_engineering.analyst.authorized import REPOSITORY_READ_ACTION
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.structure import (
    RepositoryStructure,
    RepositoryStructurePolicy,
    StructureError,
    StructureFailure,
)
from legoai_engineering.repository.structure_authorized import (
    REPOSITORY_STRUCTURE_ACTION,
    AuthorizedRepositoryStructure,
)
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import (
    RepositoryPath,
    WorkspaceEntry,
    WorkspaceEntryKind,
    WorkspacePolicy,
)


def entry(path: str, directory: bool = False) -> WorkspaceEntry:
    return WorkspaceEntry(
        RepositoryPath(path),
        WorkspaceEntryKind.DIRECTORY if directory else WorkspaceEntryKind.FILE,
    )


class Workspace:
    def __init__(self, tree: dict[str, tuple[WorkspaceEntry, ...]]) -> None:
        self.tree = tree
        self.calls: list[str] = []
        self.second: dict[str, tuple[WorkspaceEntry, ...]] | None = None
        self.error: WorkspaceFailure | None = None

    def list_entries(
        self, directory: RepositoryPath | None
    ) -> tuple[WorkspaceEntry, ...]:
        assert directory is not None
        if self.error:
            raise WorkspaceError(self.error)
        repeated = directory.value in self.calls
        self.calls.append(directory.value)
        tree = self.second if repeated and self.second is not None else self.tree
        return tree[directory.value]

    def read_text(self, path: RepositoryPath) -> RepositoryText:
        raise AssertionError("structure must never read contents")


class Authority:
    def __init__(self, fail_at: int = 0, unavailable: bool = False) -> None:
        self.fail_at = fail_at
        self.unavailable = unavailable
        self.contexts: list[SecurityContext] = []

    def evaluate(self, context: SecurityContext) -> AuthorizationDecision:
        self.contexts.append(context)
        denied = self.fail_at == len(self.contexts)
        outcome = (
            (
                AuthorizationOutcome.UNAVAILABLE
                if self.unavailable
                else AuthorizationOutcome.DENIED
            )
            if denied
            else AuthorizationOutcome.ALLOWED
        )
        category = (
            (
                ErrorCategory.DEPENDENCY_FAILURE
                if self.unavailable
                else ErrorCategory.AUTHORIZATION_DENIED
            )
            if denied
            else None
        )
        return AuthorizationDecision(
            outcome,
            context.operation,
            context.established_at,
            category,
            None,
            None,
            context.policy_ref,
        )


def acquire_object(
    workspace: Workspace,
    policy: RepositoryStructurePolicy | None = None,
    authority: Authority | None = None,
) -> AuthorizedRepositoryStructure:
    demo = create_governed_demo("not called")
    reference = replace(demo.configuration, instance=WORKSPACE)
    # Test-only context adaptation: scripted authority exercises the facade.
    context = replace(
        demo.host.security_context(reference, REPOSITORY_READ_ACTION, WORKSPACE),
        action=REPOSITORY_STRUCTURE_ACTION,
    )
    ticks = iter(NOW + timedelta(seconds=i) for i in range(1000))
    return AuthorizedRepositoryStructure(
        reference,
        workspace,
        context,
        authority or Authority(),
        policy or RepositoryStructurePolicy((RepositoryPath("src"),)),
        lambda: next(ticks),
    )


def run(subject: AuthorizedRepositoryStructure) -> RepositoryStructure:
    return subject.acquire(subject.security_context.tenant_context)


def fails(subject: AuthorizedRepositoryStructure, reason: StructureFailure) -> None:
    with pytest.raises(StructureError) as caught:
        run(subject)
    assert caught.value.reason is reason
    assert "src/" not in str(caught.value)


def test_traversal_order_kinds_identity_privacy() -> None:
    workspace = Workspace(
        {
            "src": (entry("src/z.py"), entry("src/a", True)),
            "src/a": (entry("src/a/b.py"),),
            "tests": (),
        }
    )
    policy = RepositoryStructurePolicy((RepositoryPath("tests"), RepositoryPath("src")))
    subject = acquire_object(workspace, policy)
    result = run(subject)
    assert [e.path.value for e in result.entries] == [
        "src",
        "src/a",
        "src/a/b.py",
        "src/z.py",
        "tests",
    ]
    assert workspace.calls == ["src", "src/a", "tests"] * 2
    assert len(result.digest()) == 64
    assert (
        result.digest()
        == replace(
            result, policy=replace(policy, roots=tuple(reversed(policy.roots)))
        ).digest()
    )
    assert (
        result.digest()
        != replace(result, policy=replace(policy, max_list_calls=63)).digest()
    )
    assert (
        result.model_bytes()
        == replace(result, policy=replace(policy, max_list_calls=63)).model_bytes()
    )
    assert "src" not in repr(result) + repr(policy) + repr(subject)
    assert b"digest" not in result.model_bytes()
    with pytest.raises(FrozenInstanceError):
        result.entries = ()  # type: ignore[misc]  # Runtime immutability negative.


@pytest.mark.parametrize(
    "name",
    [
        ".git",
        ".env",
        ".ENV",
        ".env.local",
        ".hidden",
        ".venv",
        "secrets",
        "Secrets",
        "credentials",
        "PRIVATE",
        "node_modules",
        "build",
        "dist",
        "generated",
        "vendor",
        "__pycache__",
        "custom",
    ],
)
def test_exclusions(name: str) -> None:
    workspace = Workspace(
        {
            "src": (
                entry("src/" + name, True),
                entry("src/customer-acme-contract.py"),
                entry("src/omit", True),
            )
        }
    )
    policy = RepositoryStructurePolicy(
        (RepositoryPath("src"),), ("CUSTOM",), (RepositoryPath("src/omit"),)
    )
    result = run(acquire_object(workspace, policy))
    assert [e.path.value for e in result.entries] == [
        "src",
        "src/customer-acme-contract.py",
    ]
    assert workspace.calls == ["src", "src"]


@pytest.mark.parametrize(
    "roots",
    [
        (),
        ("src", "src"),
        ("src", "SRC"),
        ("src", "src/sub"),
        ("src/sub", "SRC"),
        (".git",),
        ("private/sub",),
        tuple(f"r{i}" for i in range(9)),
    ],
)
def test_policy_roots(roots: tuple[str, ...]) -> None:
    with pytest.raises(StructureError) as caught:
        RepositoryStructurePolicy(tuple(RepositoryPath(p) for p in roots))
    assert caught.value.reason is StructureFailure.CONFIGURATION_INVALID


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_depth", True),
        ("max_depth", 7),
        ("max_entries", 513),
        ("max_list_calls", 65),
        ("max_serialized_bytes", 16385),
        ("max_entries", 0),
        ("max_entries", "12"),
        ("excluded_names", ("x", "X")),
        ("excluded_names", tuple(f"x{i}" for i in range(33))),
        ("excluded_names", ("a/b",)),
        ("excluded_subtrees", (RepositoryPath("x"),) * 33),
    ],
)
def test_policy_invalid(field: str, value: object) -> None:
    policy = RepositoryStructurePolicy((RepositoryPath("src"),))
    with pytest.raises(StructureError):
        replace(policy, **{field: value})  # type: ignore[arg-type]  # Invalid inputs.


@pytest.mark.parametrize(
    "children",
    [
        (entry("src/a"), entry("src/a")),
        (entry("src/a"), entry("src/A")),
        (entry("src/a"), entry("src/a", True)),
        (entry("other/a"),),
        (entry("src/a/b"),),
    ],
)
def test_malformed_adapter(children: tuple[WorkspaceEntry, ...]) -> None:
    fails(
        acquire_object(Workspace({"src": children})),
        StructureFailure.BOUNDARY_VIOLATION,
    )


def test_depth_bounds() -> None:
    root = "a/b/c/d/e"
    policy = RepositoryStructurePolicy((RepositoryPath(root),))
    assert (
        len(
            run(
                acquire_object(Workspace({root: (entry(root + "/file"),)}), policy)
            ).entries
        )
        == 2
    )
    fails(
        acquire_object(Workspace({root: (entry(root + "/dir", True),)}), policy),
        StructureFailure.STRUCTURE_LIMIT_EXCEEDED,
    )


@pytest.mark.parametrize(
    "kind", ["entries", "calls", "bytes", "component", "adapter_count"]
)
def test_bounds(kind: str) -> None:
    tree = {"src": (entry("src/a", True),), "src/a": ()}
    policy = RepositoryStructurePolicy((RepositoryPath("src"),))
    if kind == "entries":
        policy = replace(policy, max_entries=1)
    elif kind == "calls":
        policy = replace(policy, max_list_calls=1)
    elif kind == "bytes":
        policy = replace(policy, max_serialized_bytes=1)
    elif kind == "component":
        tree = {"src": (entry("src/" + "x" * 129),)}
    else:
        tree = {"src": tuple(entry(f"src/a{i}") for i in range(513))}
    fails(
        acquire_object(Workspace(tree), policy),
        StructureFailure.STRUCTURE_LIMIT_EXCEEDED,
    )


def test_stability_no_retry() -> None:
    workspace = Workspace({"src": (entry("src/a"),)})
    workspace.second = {"src": (entry("src/b"),)}
    fails(acquire_object(workspace), StructureFailure.STRUCTURE_CHANGED)
    assert workspace.calls == ["src", "src"]


@pytest.mark.parametrize("at", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("unavailable", [False, True])
def test_authority_each_listing_and_release(at: int, unavailable: bool) -> None:
    workspace = Workspace({"src": (entry("src/dir", True),), "src/dir": ()})
    authority = Authority(at, unavailable)
    subject = acquire_object(workspace, authority=authority)
    fails(
        subject,
        StructureFailure.AUTHORITY_UNAVAILABLE
        if unavailable
        else StructureFailure.AUTHORIZATION_DENIED,
    )
    assert len(workspace.calls) == min(at - 1, 4)
    times = [c.established_at for c in authority.contexts]
    assert times == sorted(set(times))


def test_wrong_tenant_no_io() -> None:
    workspace = Workspace({"src": ()})
    subject = acquire_object(workspace)
    tenant = replace(
        subject.security_context.tenant_context, tenant_id=TenantId("other")
    )
    with pytest.raises(StructureError):
        subject.acquire(tenant)
    assert workspace.calls == []


@pytest.mark.parametrize(
    "field,value", [("action", REPOSITORY_READ_ACTION), ("resource_scope", "elsewhere")]
)
def test_scope_binding(field: str, value: str) -> None:
    subject = acquire_object(Workspace({"src": ()}))
    with pytest.raises(StructureError) as caught:
        replace(
            subject,
            security_context=replace(subject.security_context, **{field: value}),  # type: ignore[arg-type]
        )
    assert caught.value.reason is StructureFailure.CONFIGURATION_INVALID


def test_workspace_binding() -> None:
    subject = acquire_object(Workspace({"src": ()}))
    with pytest.raises(StructureError):
        replace(
            subject,
            workspace_reference=replace(subject.workspace_reference, instance="other"),
        )


@pytest.mark.parametrize(
    "failure,expected",
    [
        (WorkspaceFailure.CHANGED, StructureFailure.STRUCTURE_CHANGED),
        (WorkspaceFailure.IO, StructureFailure.WORKSPACE_UNAVAILABLE),
        (WorkspaceFailure.BOUNDARY, StructureFailure.BOUNDARY_VIOLATION),
        (WorkspaceFailure.NOT_DIRECTORY, StructureFailure.UNSUPPORTED_ENTRY),
        (WorkspaceFailure.LIMIT, StructureFailure.STRUCTURE_LIMIT_EXCEEDED),
    ],
)
def test_workspace_failures(
    failure: WorkspaceFailure, expected: StructureFailure
) -> None:
    workspace = Workspace({"src": ()})
    workspace.error = failure
    subject = acquire_object(workspace)
    with pytest.raises(StructureError) as caught:
        run(subject)
    assert caught.value.reason is expected
    assert isinstance(caught.value.__cause__, WorkspaceError)


def test_real_workspace(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "nested").mkdir()
    (tmp_path / "src" / "nested" / "code.py").write_bytes(b"secret file content")
    (tmp_path / "src" / ".env").write_bytes(b"credential")
    subject = acquire_object(Workspace({"src": ()}))
    workspace = LocalRepositoryWorkspace(
        LocalWorkspaceRoot(tmp_path), WorkspacePolicy(10, 10, 512, 6, ())
    )
    result = run(replace(subject, workspace=workspace))
    assert [e.path.value for e in result.entries] == [
        "src",
        "src/nested",
        "src/nested/code.py",
    ]
    assert b"secret file content" not in result.model_bytes()
    assert str(tmp_path) not in repr(result) + result.model_bytes().decode()


def test_approval_refused() -> None:
    subject = acquire_object(Workspace({"src": ()}))
    c = subject.security_context
    approval = Approval(
        ApprovalId("approval"),
        c.operation,
        c.tenant_context,
        c.principal,
        c.principal,
        1,
        NOW,
        NOW + timedelta(hours=1),
    )
    with pytest.raises(StructureError) as caught:
        replace(subject, security_context=replace(c, approval=approval))
    assert caught.value.reason is StructureFailure.CONFIGURATION_INVALID


@pytest.mark.parametrize("mode", ["expiry", "revocation"])
def test_live_authority_invalidation(mode: str) -> None:
    workspace = Workspace({"src": (entry("src/dir", True),), "src/dir": ()})
    subject = acquire_object(workspace)
    assert subject.security_context.grant is not None
    grant = replace(subject.security_context.grant, action=REPOSITORY_STRUCTURE_ACTION)
    context = replace(subject.security_context, grant=grant)
    grants = InMemoryGrantRegistry()
    evaluator = DeterministicAuthorizationEvaluator(
        grants, InMemoryApprovalRegistry(), InMemoryPolicyRegistry()
    )

    class ChangingAuthority:
        def evaluate(self, c: SecurityContext) -> AuthorizationDecision:
            if mode == "revocation" and workspace.calls:
                grants.revoke(grant.grant_id)
            return evaluator.evaluate(c)

    subject = replace(
        subject,
        security_context=context,
        authorization=ChangingAuthority(),
        clock=lambda: (
            NOW + timedelta(hours=2 if mode == "expiry" and workspace.calls else 0)
        ),
    )
    fails(subject, StructureFailure.AUTHORIZATION_DENIED)
    assert workspace.calls == ["src"]


def test_exact_serialized_and_path_bounds() -> None:
    base = run(acquire_object(Workspace({"src": (entry("src/a"),)})))
    size = len(base.model_bytes())
    policy = replace(base.policy, max_serialized_bytes=size)
    assert run(
        acquire_object(Workspace({"src": (entry("src/a"),)}), policy)
    ) == replace(base, policy=policy)
    fails(
        acquire_object(
            Workspace({"src": (entry("src/a"),)}),
            replace(policy, max_serialized_bytes=size - 1),
        ),
        StructureFailure.STRUCTURE_LIMIT_EXCEEDED,
    )
    with pytest.raises(WorkspaceError):
        RepositoryPath("x" * 241)
    path = "src/" + "\U0001f600" * 128
    assert len(run(acquire_object(Workspace({"src": (entry(path),)}))).entries) == 2


def test_real_workspace_hardlink_refusal(tmp_path: Path) -> None:
    import os

    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "a"
    target.write_bytes(b"content")
    os.link(target, tmp_path / "src" / "b")
    workspace = LocalRepositoryWorkspace(
        LocalWorkspaceRoot(tmp_path), WorkspacePolicy(10, 10, 512, 6, ())
    )
    fails(
        replace(acquire_object(Workspace({"src": ()})), workspace=workspace),
        StructureFailure.BOUNDARY_VIOLATION,
    )


def test_unsupported_unicode() -> None:
    for text in ("src/\ud800", "src/name\u202e.py"):
        fails(
            acquire_object(Workspace({"src": (entry(text),)})),
            StructureFailure.UNSUPPORTED_ENTRY,
        )


def test_entry_and_call_hard_ceilings() -> None:
    names = [
        a + b
        for a in "abcdefghijklmnopqrstuvwxyz"
        for b in "abcdefghijklmnopqrstuvwxyz"
    ]
    policy = RepositoryStructurePolicy((RepositoryPath("r"),))
    result = run(
        acquire_object(
            Workspace({"r": tuple(entry("r/" + n) for n in names[:511])}), policy
        )
    )
    assert len(result.entries) == 512
    fails(
        acquire_object(
            Workspace({"r": tuple(entry("r/" + n) for n in names[:512])}), policy
        ),
        StructureFailure.STRUCTURE_LIMIT_EXCEEDED,
    )
    tree = {"r": tuple(entry("r/" + n, True) for n in names[:63])}
    tree.update({"r/" + n: () for n in names[:63]})
    workspace = Workspace(tree)
    run(acquire_object(workspace, policy))
    assert len(workspace.calls) == 128
    tree["r"] += (entry("r/" + names[63], True),)
    tree["r/" + names[63]] = ()
    workspace = Workspace(tree)
    fails(acquire_object(workspace, policy), StructureFailure.STRUCTURE_LIMIT_EXCEEDED)
    assert len(workspace.calls) == 64


@pytest.mark.parametrize("bad", [[], (object(),)])
def test_invalid_adapter_shape(bad: object) -> None:
    class Malformed(Workspace):
        def list_entries(
            self, directory: RepositoryPath | None
        ) -> tuple[WorkspaceEntry, ...]:
            return bad  # type: ignore[return-value]  # Malformed dependency response.

    fails(acquire_object(Malformed({})), StructureFailure.UNSUPPORTED_ENTRY)


def test_invalid_component_configuration_safe_error() -> None:
    with pytest.raises(StructureError) as caught:
        RepositoryStructurePolicy((RepositoryPath("src"),), ("C:\\sensitive",))
    assert caught.value.reason is StructureFailure.CONFIGURATION_INVALID
    assert "sensitive" not in str(caught.value) + repr(caught.value)
