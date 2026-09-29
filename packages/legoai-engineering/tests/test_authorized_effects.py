"""CR-3 authorized mutation and check wrappers: current authority before effect.

Authority comes from the public local host (operator grants) unless a test
needs a live revocation or policy change, which the reference evaluator
supplies. Spies record one shared event log so ordering is asserted directly.
"""

import asyncio
import json
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from governed_demo import NOW, WORKSPACE, create_governed_demo
from governed_engineering import create_engineering_demo
from legoai.governance.ports import (
    AuthorizationDecision,
    AuthorizationOutcome,
    AuthorizationPort,
    SecurityContext,
)
from legoai.governance.values import Approval, ApprovalId
from legoai.kernel.context import TenantContext
from legoai.kernel.errors import ErrorCategory
from legoai.kernel.identity import TenantId
from legoai.kernel.references import ConfigurationRef
from legoai.reference.governance import (
    DeterministicAuthorizationEvaluator,
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)
from legoai.runtime.api import GovernedHost

from legoai_engineering import _authority
from legoai_engineering.analyst.authorized import REPOSITORY_READ_ACTION
from legoai_engineering.authorization import (
    EffectAuthorizationError,
    EffectAuthorizationFailure,
)
from legoai_engineering.checks.authorized import (
    ENGINEERING_CHECK_ACTION,
    AuthorizedEngineeringChecks,
)
from legoai_engineering.checks.errors import CheckError, CheckFailure
from legoai_engineering.checks.local import LocalCheckTools, LocalEngineeringChecks
from legoai_engineering.checks.ports import EngineeringCheckPort
from legoai_engineering.checks.sandboxed import (
    CheckInputPolicy,
    SandboxedEngineeringChecks,
)
from legoai_engineering.checks.values import (
    CheckKind,
    CheckOutcome,
    CheckPolicy,
    CheckRequest,
    CheckResult,
)
from legoai_engineering.coding.values import CodingTarget
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.mutation import (
    FileChange,
    FileChangeKind,
    RepositoryChangeSet,
    RepositoryMutationResult,
    digest_text,
)
from legoai_engineering.repository.mutation_authorized import (
    REPOSITORY_MUTATION_ACTION,
    AuthorizedRepositoryMutation,
)
from legoai_engineering.repository.mutation_errors import (
    MutationConflict,
    MutationConflictReason,
)
from legoai_engineering.repository.mutation_local import LocalRepositoryMutation
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import (
    RepositoryPath,
    WorkspaceEntry,
    WorkspacePolicy,
)
from legoai_engineering.sandbox.ports import CancellationSignal
from legoai_engineering.sandbox.values import SandboxRequest, SandboxResult

POLICY = WorkspacePolicy(8192, 8192, 16, 8, (".git", ".venv"))
CHECK = CheckRequest(CheckKind.RUFF_CHECK, (RepositoryPath("greeting.py"),))


class Clock:
    def __init__(self, now: datetime = NOW) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class SpyAuthorization:
    def __init__(self, inner: AuthorizationPort, log: list[str]) -> None:
        self.inner = inner
        self.log = log
        self.contexts: list[SecurityContext] = []

    def evaluate(self, context: SecurityContext) -> AuthorizationDecision:
        self.log.append("evaluate")
        self.contexts.append(context)
        return self.inner.evaluate(context)


class ScriptedAuthorization:
    """Current policy answers change between calls; nothing is cached."""

    def __init__(self, *outcomes: AuthorizationOutcome) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def evaluate(self, context: SecurityContext) -> AuthorizationDecision:
        self.calls += 1
        outcome = self.outcomes.pop(0)
        category = (
            None
            if outcome is AuthorizationOutcome.ALLOWED
            else ErrorCategory.DEPENDENCY_FAILURE
            if outcome is AuthorizationOutcome.UNAVAILABLE
            else ErrorCategory.AUTHORIZATION_DENIED
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


class SpyMutation:
    def __init__(
        self, log: list[str], inner: LocalRepositoryMutation | None = None
    ) -> None:
        self.log = log
        self.inner = inner
        self.error: Exception | None = None
        self.changesets: list[RepositoryChangeSet] = []

    def apply(self, changeset: RepositoryChangeSet) -> RepositoryMutationResult:
        self.log.append("apply")
        self.changesets.append(changeset)
        if self.error is not None:
            raise self.error
        assert self.inner is not None
        return self.inner.apply(changeset)


class SpyChecks:
    def __init__(self, log: list[str], inner: EngineeringCheckPort | None = None):
        self.log = log
        self.inner = inner
        self.error: Exception | None = None
        self.requests: list[CheckRequest] = []

    def check(self, request: CheckRequest) -> CheckResult:
        self.log.append("check")
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        if self.inner is not None:
            return self.inner.check(request)
        return CheckResult(request.kind, 1, b"finding", b"")


class CountingWorkspace:
    def __init__(self, root: Path) -> None:
        self.inner = LocalRepositoryWorkspace(LocalWorkspaceRoot(root), POLICY)
        self.calls = 0

    def list_entries(
        self, directory: RepositoryPath | None
    ) -> tuple[WorkspaceEntry, ...]:
        self.calls += 1
        return self.inner.list_entries(directory)

    def read_text(self, path: RepositoryPath) -> RepositoryText:
        self.calls += 1
        return self.inner.read_text(path)


class CountingSandbox:
    """Answers with the CR-2b runner envelope for a clean completed run."""

    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult:
        self.calls += 1
        body = {"status": "completed", "exit": 0, "stdout": "", "stderr": ""}
        return SandboxResult(0, json.dumps(body).encode(), b"")


@dataclass
class Governed:
    host: GovernedHost
    reference: ConfigurationRef
    log: list[str]
    authorization: SpyAuthorization
    clock: Clock

    def context(self, action: str) -> SecurityContext:
        return self.host.security_context(self.reference, action, WORKSPACE)

    def mutation(
        self, inner: object, **changes: object
    ) -> AuthorizedRepositoryMutation:
        wrapper = AuthorizedRepositoryMutation(
            self.reference,
            inner,  # type: ignore[arg-type]
            self.context(REPOSITORY_MUTATION_ACTION),
            self.authorization,
            self.clock,
        )
        return replace(wrapper, **changes)  # type: ignore[arg-type]

    def checks(self, inner: object, **changes: object) -> AuthorizedEngineeringChecks:
        wrapper = AuthorizedEngineeringChecks(
            self.reference,
            inner,  # type: ignore[arg-type]
            self.context(ENGINEERING_CHECK_ACTION),
            self.authorization,
            self.clock,
        )
        return replace(wrapper, **changes)  # type: ignore[arg-type]


def governed(**grants: bool) -> Governed:
    demo = create_governed_demo("{}", **grants)
    log: list[str] = []
    return Governed(
        demo.host,
        replace(demo.configuration, instance=WORKSPACE),
        log,
        SpyAuthorization(demo.host.authorization, log),
        Clock(),
    )


def update(
    root: Path, text: str = "GREETING = 'hello LegoAI'\n"
) -> RepositoryChangeSet:
    current = (root / "greeting.py").read_text(encoding="utf-8")
    return RepositoryChangeSet(
        (
            FileChange(
                RepositoryPath("greeting.py"),
                FileChangeKind.UPDATE,
                digest_text(current),
                text,
            ),
        )
    )


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "greeting.py").write_bytes(b"GREETING = 'hello'\n")
    return tmp_path


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in root.iterdir()}


# --- A/B. Authorized mutation ------------------------------------------------


def test_mutation_allowed_authorizes_then_applies_exactly_once(root: Path) -> None:
    g = governed()
    inner = SpyMutation(
        g.log, LocalRepositoryMutation(LocalWorkspaceRoot(root), POLICY)
    )
    changeset = update(root)
    result = g.mutation(inner).apply(changeset)
    assert g.log == ["evaluate", "apply"]
    assert inner.changesets == [changeset] and inner.changesets[0] is changeset
    assert result.applied[0].after == digest_text("GREETING = 'hello LegoAI'\n")
    assert (root / "greeting.py").read_bytes() == b"GREETING = 'hello LegoAI'\n"
    evaluated = g.authorization.contexts[0]
    assert evaluated.action == REPOSITORY_MUTATION_ACTION
    assert evaluated.resource_scope == WORKSPACE
    assert evaluated.established_at == NOW


def test_mutation_denied_never_calls_inner_and_writes_nothing(root: Path) -> None:
    g = governed(write_allowed=False)
    inner = SpyMutation(
        g.log, LocalRepositoryMutation(LocalWorkspaceRoot(root), POLICY)
    )
    before = snapshot(root)
    with pytest.raises(EffectAuthorizationError) as caught:
        g.mutation(inner).apply(update(root))
    assert caught.value.reason is EffectAuthorizationFailure.DENIED
    assert g.log == ["evaluate"] and inner.changesets == []
    assert snapshot(root) == before


def test_mutation_requires_changeset_before_authorization(root: Path) -> None:
    g = governed()
    inner = SpyMutation(g.log)
    with pytest.raises(TypeError):
        g.mutation(inner).apply(object())  # type: ignore[arg-type]
    assert g.log == []


# --- C/D. Authorized checks --------------------------------------------------


def test_check_allowed_authorizes_then_checks_exactly_once() -> None:
    g = governed()
    inner = SpyChecks(g.log)
    result = g.checks(inner).check(CHECK)
    assert g.log == ["evaluate", "check"]
    assert inner.requests == [CHECK] and inner.requests[0] is CHECK
    assert result.outcome is CheckOutcome.FAILED and result.stdout == b"finding"
    assert g.authorization.contexts[0].action == ENGINEERING_CHECK_ACTION


def test_check_denied_never_reaches_workspace_or_sandbox(root: Path) -> None:
    g = governed(check_allowed=False)
    workspace = CountingWorkspace(root)
    sandbox = CountingSandbox()
    inner = SandboxedEngineeringChecks(
        workspace, sandbox, CheckInputPolicy((RepositoryPath("pkg"),)), CheckPolicy()
    )
    with pytest.raises(EffectAuthorizationError) as caught:
        g.checks(inner).check(CHECK)
    assert caught.value.reason is EffectAuthorizationFailure.DENIED
    assert g.log == ["evaluate"]
    assert workspace.calls == 0 and sandbox.calls == 0


def test_check_requires_request_before_authorization() -> None:
    g = governed()
    with pytest.raises(TypeError):
        g.checks(SpyChecks(g.log)).check(object())  # type: ignore[arg-type]
    assert g.log == []


# --- E. Authorization is current per effect ---------------------------------


def test_grant_valid_at_construction_but_expired_before_effect(root: Path) -> None:
    g = governed()
    mutation_inner = SpyMutation(
        g.log, LocalRepositoryMutation(LocalWorkspaceRoot(root), POLICY)
    )
    checks_inner = SpyChecks(g.log)
    mutation = g.mutation(mutation_inner)
    checks = g.checks(checks_inner)
    checks.check(CHECK)
    g.clock.now = NOW + timedelta(hours=2)
    before = snapshot(root)
    for effect in (lambda: mutation.apply(update(root)), lambda: checks.check(CHECK)):
        with pytest.raises(EffectAuthorizationError) as caught:
            effect()
        assert caught.value.reason is EffectAuthorizationFailure.DENIED
    assert g.log == ["evaluate", "check", "evaluate", "evaluate"]
    assert snapshot(root) == before
    assert [c.established_at for c in g.authorization.contexts] == [
        NOW,
        NOW + timedelta(hours=2),
        NOW + timedelta(hours=2),
    ]


def test_allow_is_never_cached() -> None:
    g = governed()
    inner = SpyChecks(g.log)
    scripted = ScriptedAuthorization(
        AuthorizationOutcome.ALLOWED, AuthorizationOutcome.DENIED
    )
    checks = g.checks(inner, authorization=scripted)
    checks.check(CHECK)
    with pytest.raises(EffectAuthorizationError):
        checks.check(CHECK)
    assert scripted.calls == 2 and len(inner.requests) == 1


def test_revocation_and_policy_supersession_deny_the_next_effect(root: Path) -> None:
    for change in ("revoke", "supersede"):
        g = governed()
        grants, policies = InMemoryGrantRegistry(), InMemoryPolicyRegistry()
        evaluator = DeterministicAuthorizationEvaluator(
            grants, InMemoryApprovalRegistry(), policies
        )
        inner = SpyMutation(
            g.log, LocalRepositoryMutation(LocalWorkspaceRoot(root), POLICY)
        )
        mutation = g.mutation(inner, authorization=evaluator)
        (root / "greeting.py").write_bytes(b"GREETING = 'hello'\n")
        mutation.apply(update(root))
        context = mutation.security_context
        assert context.grant is not None
        if change == "revoke":
            grants.revoke(context.grant.grant_id)
        else:
            policies.supersede(context.policy_ref)
        before = snapshot(root)
        with pytest.raises(EffectAuthorizationError) as caught:
            mutation.apply(update(root, "GREETING = 'again'\n"))
        assert caught.value.reason is EffectAuthorizationFailure.DENIED, change
        assert len(inner.changesets) == 1 and snapshot(root) == before


def test_unavailable_authority_is_distinct_and_fails_closed() -> None:
    g = governed()
    inner = SpyChecks(g.log)
    checks = g.checks(
        inner, authorization=ScriptedAuthorization(AuthorizationOutcome.UNAVAILABLE)
    )
    with pytest.raises(EffectAuthorizationError) as caught:
        checks.check(CHECK)
    assert caught.value.reason is EffectAuthorizationFailure.UNAVAILABLE
    assert inner.requests == []


def test_unrelated_or_stale_decision_is_denied() -> None:
    g = governed()

    class Unrelated:
        def evaluate(self, context: SecurityContext) -> AuthorizationDecision:
            return AuthorizationDecision(
                AuthorizationOutcome.ALLOWED,
                context.operation,
                context.established_at - timedelta(seconds=1),
                None,
                None,
                None,
                context.policy_ref,
            )

    inner = SpyChecks(g.log)
    with pytest.raises(EffectAuthorizationError) as caught:
        g.checks(inner, authorization=Unrelated()).check(CHECK)
    assert caught.value.reason is EffectAuthorizationFailure.DENIED
    assert inner.requests == []


def test_non_decision_is_a_contract_error_not_an_allow() -> None:
    g = governed()

    class Broken:
        def evaluate(self, context: SecurityContext) -> object:
            return True

    inner = SpyChecks(g.log)
    with pytest.raises(TypeError):
        g.checks(inner, authorization=Broken()).check(CHECK)
    assert inner.requests == []


# --- F. Tenant and workspace scope -------------------------------------------


def test_wrong_tenant_grant_is_denied_before_effect(root: Path) -> None:
    g = governed()
    context = g.context(REPOSITORY_MUTATION_ACTION)
    assert context.grant is not None
    foreign = replace(
        context,
        grant=replace(
            context.grant, tenant_context=TenantContext(TenantId("other-tenant"))
        ),
    )
    inner = SpyMutation(
        g.log, LocalRepositoryMutation(LocalWorkspaceRoot(root), POLICY)
    )
    before = snapshot(root)
    with pytest.raises(EffectAuthorizationError) as caught:
        g.mutation(inner, security_context=foreign).apply(update(root))
    assert caught.value.reason is EffectAuthorizationFailure.DENIED
    assert g.log == ["evaluate"] and snapshot(root) == before


def test_wrong_workspace_or_action_scope_is_refused_at_composition() -> None:
    g = governed()
    other = replace(g.reference, instance="other-workspace")
    inner = SpyChecks(g.log)
    for reference, context in (
        (other, g.context(ENGINEERING_CHECK_ACTION)),
        (g.reference, g.context(REPOSITORY_READ_ACTION)),
        (g.reference, g.context(REPOSITORY_MUTATION_ACTION)),
        (
            g.reference,
            replace(g.context(ENGINEERING_CHECK_ACTION), resource_scope="other"),
        ),
    ):
        with pytest.raises(ValueError):
            AuthorizedEngineeringChecks(
                reference, inner, context, g.authorization, g.clock
            )
    with pytest.raises(ValueError):
        AuthorizedRepositoryMutation(
            g.reference,
            SpyMutation(g.log),
            g.context(ENGINEERING_CHECK_ACTION),
            g.authorization,
            g.clock,
        )
    assert g.log == []


def test_constructor_rejects_wrong_types() -> None:
    g = governed()
    context = g.context(ENGINEERING_CHECK_ACTION)
    valid: dict[str, object] = {
        "workspace_reference": g.reference,
        "checks": SpyChecks(g.log),
        "security_context": context,
        "authorization": g.authorization,
        "clock": g.clock,
    }
    for field, value in (
        ("workspace_reference", "workspace"),
        ("checks", object()),
        ("security_context", object()),
        ("authorization", object()),
        ("clock", "now"),
    ):
        with pytest.raises(TypeError):
            AuthorizedEngineeringChecks(**{**valid, field: value})  # type: ignore[arg-type]


# --- G. Approvals fail closed ------------------------------------------------


def approval_context(g: Governed, action: str) -> SecurityContext:
    context = g.context(action)
    return replace(
        context,
        approval=Approval(
            ApprovalId("approval"),
            context.operation,
            context.tenant_context,
            context.principal,
            context.principal,
            1,
            NOW,
            NOW + timedelta(hours=1),
        ),
    )


def test_approval_bearing_context_is_refused_before_any_effect() -> None:
    g = governed()
    for action, build in (
        (
            REPOSITORY_MUTATION_ACTION,
            lambda c: AuthorizedRepositoryMutation(
                g.reference, SpyMutation(g.log), c, g.authorization, g.clock
            ),
        ),
        (
            ENGINEERING_CHECK_ACTION,
            lambda c: AuthorizedEngineeringChecks(
                g.reference, SpyChecks(g.log), c, g.authorization, g.clock
            ),
        ),
    ):
        with pytest.raises(ValueError):
            build(approval_context(g, action))
    assert g.log == []


def test_helper_denies_approvals_without_evaluating() -> None:
    g = governed()
    outcome = _authority._evaluate(
        approval_context(g, ENGINEERING_CHECK_ACTION), g.authorization, g.clock
    )
    assert outcome is AuthorizationOutcome.DENIED and g.log == []
    assert (
        _authority._evaluate(
            g.context(ENGINEERING_CHECK_ACTION), g.authorization, g.clock
        )
        is AuthorizationOutcome.ALLOWED
    )
    assert g.log == ["evaluate"]


# --- H. Allowed failures propagate unchanged; no retry -----------------------


def test_allowed_mutation_error_propagates_once() -> None:
    g = governed()
    inner = SpyMutation(g.log)
    error = MutationConflict(
        MutationConflictReason.STALE, RepositoryPath("greeting.py")
    )
    inner.error = error
    changeset = RepositoryChangeSet(
        (
            FileChange(
                RepositoryPath("greeting.py"),
                FileChangeKind.UPDATE,
                digest_text("x"),
                "y",
            ),
        )
    )
    with pytest.raises(MutationConflict) as caught:
        g.mutation(inner).apply(changeset)
    assert caught.value is error and g.log == ["evaluate", "apply"]


@pytest.mark.parametrize(
    "error",
    [CheckError(CheckFailure.TIMEOUT), WorkspaceError(WorkspaceFailure.MISSING)],
    ids=["check-error", "workspace-error"],
)
def test_allowed_check_error_propagates_once(error: Exception) -> None:
    g = governed()
    inner = SpyChecks(g.log)
    inner.error = error
    with pytest.raises(type(error)) as caught:
        g.checks(inner).check(CHECK)
    assert caught.value is error and g.log == ["evaluate", "check"]


# --- I. Substitutability ------------------------------------------------------


def outcomes(port: EngineeringCheckPort, requests: list[CheckRequest]) -> list[str]:
    """Application code: depends on EngineeringCheckPort only."""
    return [port.check(item).outcome.value for item in requests]


def test_same_consumer_over_local_and_sandboxed_inner_adapters(root: Path) -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    requests = [CheckRequest(CheckKind.RUFF_CHECK, (RepositoryPath("pkg"),))]
    base = Path(sys.executable).parent
    suffix = ".exe" if sys.platform == "win32" else ""
    local = LocalEngineeringChecks(
        LocalWorkspaceRoot(root),
        LocalCheckTools(
            *(base / (name + suffix) for name in ("pytest", "ruff", "mypy"))
        ),
        CheckPolicy(timeout_seconds=60),
    )
    sandbox = CountingSandbox()
    sandboxed = SandboxedEngineeringChecks(
        CountingWorkspace(root),
        sandbox,
        CheckInputPolicy((RepositoryPath("pkg"),)),
        CheckPolicy(),
    )
    for inner in (local, sandboxed):
        g = governed()
        assert outcomes(g.checks(inner), requests) == ["passed"]
        assert g.log == ["evaluate"]
    assert sandbox.calls == 1


# --- J. M4 invariants behind the wrapper -------------------------------------


@pytest.mark.parametrize("kind", [FileChangeKind.CREATE, FileChangeKind.UPDATE])
def test_m4_preconditions_still_apply_behind_authorization(
    tmp_path: Path, kind: FileChangeKind
) -> None:
    file = tmp_path / "greeting.py"
    if kind is FileChangeKind.UPDATE:
        file.write_bytes(b"GREETING = 'hello'\n")
    output = json.dumps(
        {
            "summary": "Propose.",
            "changes": [
                {
                    "path": "greeting.py",
                    "operation": kind.value,
                    "content": "GREETING = 'new'\n",
                    "reason": "Requested.",
                }
            ],
            "risks": [],
            "unknowns": [],
        }
    )
    demo = create_engineering_demo(
        tmp_path, output, (CodingTarget(RepositoryPath("greeting.py"), kind),)
    )
    result = asyncio.run(demo.agent.propose(demo.request))
    assert result.proposal is not None
    file.write_bytes(b"later edit")
    with pytest.raises(MutationConflict) as caught:
        demo.mutation.apply(result.proposal.changeset)
    assert caught.value.reason is (
        MutationConflictReason.EXISTS
        if kind is FileChangeKind.CREATE
        else MutationConflictReason.STALE
    )
    assert file.read_bytes() == b"later edit"


def test_denied_write_leaves_proposal_unapplied(tmp_path: Path) -> None:
    (tmp_path / "greeting.py").write_bytes(b"GREETING = 'hello'\n")
    output = json.dumps(
        {
            "summary": "Propose.",
            "changes": [
                {
                    "path": "greeting.py",
                    "operation": "update",
                    "content": "GREETING = 'new'\n",
                    "reason": "Requested.",
                }
            ],
            "risks": [],
            "unknowns": [],
        }
    )
    demo = create_engineering_demo(
        tmp_path,
        output,
        (CodingTarget(RepositoryPath("greeting.py"), FileChangeKind.UPDATE),),
        write_allowed=False,
    )
    result = asyncio.run(demo.agent.propose(demo.request))
    assert result.proposal is not None
    with pytest.raises(EffectAuthorizationError):
        demo.mutation.apply(result.proposal.changeset)
    assert (tmp_path / "greeting.py").read_bytes() == b"GREETING = 'hello'\n"


def test_read_write_and_check_grants_are_independent(tmp_path: Path) -> None:
    (tmp_path / "greeting.py").write_bytes(b"GREETING = 'hello'\n")
    demo = create_engineering_demo(
        tmp_path,
        "{}",
        (CodingTarget(RepositoryPath("greeting.py"), FileChangeKind.UPDATE),),
        check_allowed=False,
    )
    with pytest.raises(EffectAuthorizationError):
        demo.checks.check(CHECK)
    applied = demo.mutation.apply(update(tmp_path))
    assert applied.applied[0].path.value == "greeting.py"
