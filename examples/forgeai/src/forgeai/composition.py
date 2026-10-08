"""ForgeAI composition root: operator configuration to one run's adapters.

The only ForgeAI module that names concrete LegoAI adapters or opens the
public governed host. Each run opens its own host, binds exactly one
workspace and gets a fresh ExecutionContext. Checks always run in the
sandbox on the qualified checks image; there is no host check adapter here.
"""

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from legoai.execution.values import ExecutionContext
from legoai.governance.values import GrantId, PolicyRef
from legoai.kernel.identity import ApplicationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.runtime.api import (
    LocalHostConfig,
    ModelBindingConfig,
    ModelPurpose,
    OperatorGrant,
)
from legoai.runtime.local import open_local_host
from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.checks.authorized import (
    ENGINEERING_CHECK_ACTION,
    AuthorizedEngineeringChecks,
)
from legoai_engineering.checks.sandboxed import (
    CheckInputPolicy,
    SandboxedEngineeringChecks,
)
from legoai_engineering.checks.values import CheckKind, CheckPolicy, CheckRequest
from legoai_engineering.coding.api import CodingAgent
from legoai_engineering.coding.authorized import AuthorizedCodingEvidence
from legoai_engineering.git.local import (
    GitReadPolicy,
    LocalGitExecutable,
    LocalGitRepository,
)
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.mutation_authorized import (
    REPOSITORY_MUTATION_ACTION,
    AuthorizedRepositoryMutation,
)
from legoai_engineering.repository.mutation_local import LocalRepositoryMutation
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy
from legoai_engineering.reviewer.api import IndependentReviewer
from legoai_engineering.sandbox.docker import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxImage,
)
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
from legoai_engineering.sandbox.ports import SandboxExecutionPort
from legoai_engineering.sandbox.values import SandboxPolicy

from forgeai.domain import (
    OperatorDecision,
    ProposalReview,
    RunStage,
    TaskRequest,
    TaskResult,
)
from forgeai.guard import WorkspaceGuard
from forgeai.worker import RepositoryTaskWorker


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ForgeAIConfig:
    """Trusted operator configuration; never derived from task text.

    The host configuration carries principal, tenant, policy, grants and model
    bindings; the selection names one binding. Grants must cover the read,
    mutation and check actions on `workspace_scope`, plus Chat invocation.
    """

    repository: Path
    workspace_policy: WorkspacePolicy
    editable_paths: tuple[RepositoryPath, ...]
    git_executable: Path
    git_policy: GitReadPolicy
    docker_executable: Path
    sandbox_policy: SandboxPolicy
    check_inputs: CheckInputPolicy
    check_policy: CheckPolicy
    check_plan: tuple[CheckRequest, ...]
    host: LocalHostConfig = field(repr=False)
    model_selection: Mapping[str, object] = field(repr=False)
    review_criteria: tuple[str, ...] = field(repr=False)
    workspace_scope: str = "workspace"
    sandbox_image: SandboxImage = SandboxImage.PYTHON_CHECKS
    # Read-only disclosure to the Coding Agent; never editable, never reviewed.
    context_paths: tuple[RepositoryPath, ...] = ()

    def __post_init__(self) -> None:
        for value, expected in (
            (self.workspace_policy, WorkspacePolicy),
            (self.git_policy, GitReadPolicy),
            (self.sandbox_policy, SandboxPolicy),
            (self.check_inputs, CheckInputPolicy),
            (self.check_policy, CheckPolicy),
            (self.host, LocalHostConfig),
            (self.sandbox_image, SandboxImage),
        ):
            if type(value) is not expected:
                raise TypeError(f"ForgeAI configuration requires {expected.__name__}")
        for path in (self.repository, self.git_executable, self.docker_executable):
            if not isinstance(path, Path) or not path.is_absolute():
                raise ValueError("ForgeAI configuration paths must be absolute")
        if (
            type(self.check_plan) is not tuple
            or not 1 <= len(self.check_plan) <= 8
            or any(type(item) is not CheckRequest for item in self.check_plan)
        ):
            raise ValueError("configure one to eight CheckRequest values")
        if not isinstance(self.model_selection, Mapping):
            raise TypeError("model selection must be a mapping")
        if (
            type(self.review_criteria) is not tuple
            or not 1 <= len(self.review_criteria) <= 8
            or any(type(item) is not str for item in self.review_criteria)
        ):
            raise ValueError("configure one to eight review criteria")
        if (
            type(self.context_paths) is not tuple
            or len(self.context_paths) > 8
            or any(type(path) is not RepositoryPath for path in self.context_paths)
        ):
            raise ValueError("configure at most eight read-only context paths")
        editable = {path.value.casefold() for path in self.editable_paths}
        if any(path.value.casefold() in editable for path in self.context_paths):
            raise ValueError("read-only context paths must not be editable paths")


@dataclass(frozen=True, slots=True)
class PreparedRun:
    worker: RepositoryTaskWorker
    context: ExecutionContext


def prepare_run(
    config: ForgeAIConfig,
    guard: WorkspaceGuard,
    *,
    approve: Callable[[ProposalReview], OperatorDecision],
    progress: Callable[[RunStage, int], None] = lambda stage, attempt: None,
    clock: Callable[[], datetime] = utc_now,
    sandbox: SandboxExecutionPort | None = None,
) -> PreparedRun:
    """Open a host and wire one workspace. `sandbox` replaces Docker only with
    another SandboxExecutionPort backend; there is never a host fallback.

    `approve` is the operator's decision on each validated proposal before any
    mutation. It is required; there is no automatic approval."""
    if type(config) is not ForgeAIConfig:
        raise TypeError("prepare_run requires ForgeAIConfig")
    host = open_local_host(config.host, config.model_selection, clock=clock)
    reference = replace(
        config.host.configuration.configuration, instance=config.workspace_scope
    )
    scope = config.workspace_scope
    root = LocalWorkspaceRoot(config.repository)
    workspace = LocalRepositoryWorkspace(root, config.workspace_policy)
    read_context = host.security_context(reference, REPOSITORY_READ_ACTION, scope)
    # Editable targets only: the Coding Agent's targets and the reviewer's reads.
    reads = AuthorizedRepositoryEvidence(
        reference,
        workspace,
        read_context,
        host.authorization,
        config.editable_paths,
        clock,
    )
    # A separate association for read-only context: disclosure, never targets.
    context_reads = (
        AuthorizedRepositoryEvidence(
            reference,
            workspace,
            read_context,
            host.authorization,
            config.context_paths,
            clock,
        )
        if config.context_paths
        else None
    )
    mutation = AuthorizedRepositoryMutation(
        reference,
        LocalRepositoryMutation(root, config.workspace_policy),
        host.security_context(reference, REPOSITORY_MUTATION_ACTION, scope),
        host.authorization,
        clock,
    )
    checks = AuthorizedEngineeringChecks(
        reference,
        SandboxedEngineeringChecks(
            workspace,
            sandbox
            if sandbox is not None
            else DockerSandbox(
                DockerSandboxConfig(config.docker_executable, config.sandbox_image),
                config.sandbox_policy,
            ),
            config.check_inputs,
            config.check_policy,
        ),
        host.security_context(reference, ENGINEERING_CHECK_ACTION, scope),
        host.authorization,
        clock,
    )
    runtime = host.agent_runtime()

    def fresh_context(coding: ExecutionContext) -> ExecutionContext:
        # A fresh Chat execution per later model call, correlated with the run.
        return host.model_execution(
            ModelPurpose.CHAT,
            correlation=coding.correlation_id,
            causation=coding.operation,
        )

    worker = RepositoryTaskWorker(
        os.path.normcase(str(config.repository.resolve())),
        guard,
        LocalGitRepository(
            root, LocalGitExecutable(config.git_executable), config.git_policy
        ),
        CodingAgent(AuthorizedCodingEvidence(reads, context_reads), runtime),
        mutation,
        checks,
        config.check_plan,
        IndependentReviewer(runtime),
        reads,
        config.review_criteria,
        fresh_context,
        approve,
        progress,
    )
    return PreparedRun(worker, host.model_execution(ModelPurpose.CHAT))


def sandbox_readiness(config: ForgeAIConfig) -> SandboxFailure | None:
    """Startup probe of the configured Docker checks sandbox, or why not ready.

    Metadata only through the Engineering adapter (no workload, pull, build or
    Docker start). Ready is a point-in-time observation, not a check result.
    """
    if type(config) is not ForgeAIConfig:
        raise TypeError("sandbox readiness requires ForgeAIConfig")
    try:
        sandbox = DockerSandbox(
            DockerSandboxConfig(config.docker_executable, config.sandbox_image),
            config.sandbox_policy,
        )
    except TypeError, ValueError:
        return SandboxFailure.RUNTIME_UNAVAILABLE  # not a usable docker.exe path
    try:
        sandbox.verify_ready()
    except SandboxError as error:
        return error.reason
    return None


async def run_task(
    config: ForgeAIConfig,
    task: TaskRequest,
    guard: WorkspaceGuard,
    *,
    approve: Callable[[ProposalReview], OperatorDecision],
    progress: Callable[[RunStage, int], None] = lambda stage, attempt: None,
    clock: Callable[[], datetime] = utc_now,
    sandbox: SandboxExecutionPort | None = None,
) -> TaskResult:
    prepared = prepare_run(
        config,
        guard,
        approve=approve,
        progress=progress,
        clock=clock,
        sandbox=sandbox,
    )
    return await prepared.worker.run(task, prepared.context)


REVISION = "forgeai-1"
REVIEW_CRITERIA = (
    "correctness: the change implements the objective without defects",
    "requested behavior: every requirement stated in the objective is met",
    "test adequacy: tests cover the new behavior, including rejected inputs",
    "maintainability: the change is clear and consistent with the code",
    "unintended changes: nothing beyond the objective was changed",
)


def local_profile(
    repository: Path,
    editable_paths: tuple[RepositoryPath, ...],
    *,
    bindings: tuple[ModelBindingConfig, ...],
    binding: str,
    git_executable: Path,
    docker_executable: Path,
    now: datetime,
    grant_hours: int = 1,
    denied_actions: frozenset[str] = frozenset(),
    context_paths: tuple[RepositoryPath, ...] = (),
) -> ForgeAIConfig:
    """The ForgeAI-1 local operator profile for a src/tests Python repository.

    Fixed check plan (Ruff, mypy, pytest) in the sandbox, fixed review
    criteria, one workspace, one principal and grants for exactly the four
    actions a run needs (the reviewer reuses the read and Chat grants). Grants in
    `denied_actions` are configured already expired (operator denial).
    """
    tenant = TenantId("local")
    configuration = ConfigurationRef(
        ApplicationRef(ReferenceScope("operator", tenant), ApplicationId("forgeai")),
        "forgeai",
    )
    scope = "workspace"
    active = (now - timedelta(minutes=1), now + timedelta(hours=grant_hours))
    expired = (now - timedelta(hours=2), now - timedelta(hours=1))
    actions = (
        ("invoke-capability", ModelPurpose.CHAT.capability_id.value),
        (REPOSITORY_READ_ACTION, scope),
        (REPOSITORY_MUTATION_ACTION, scope),
        (ENGINEERING_CHECK_ACTION, scope),
    )
    grants = tuple(
        OperatorGrant(
            GrantId(f"forgeai-{index}"),
            action,
            resource,
            *(expired if action in denied_actions else active),
        )
        for index, (action, resource) in enumerate(actions)
    )
    return ForgeAIConfig(
        repository=repository,
        workspace_policy=WorkspacePolicy(
            262_144, 65_536, 4096, 32, (".git", ".venv", "__pycache__")
        ),
        editable_paths=editable_paths,
        git_executable=git_executable,
        git_policy=GitReadPolicy(20, 262_144, 256, 4096),
        docker_executable=docker_executable,
        sandbox_policy=SandboxPolicy(timeout_seconds=180, max_output_bytes=1_048_576),
        check_inputs=CheckInputPolicy(
            (RepositoryPath("src"), RepositoryPath("tests")),
            (RepositoryPath("pyproject.toml"),),
        ),
        check_policy=CheckPolicy(timeout_seconds=120),
        check_plan=(
            CheckRequest(
                CheckKind.RUFF_CHECK, (RepositoryPath("src"), RepositoryPath("tests"))
            ),
            CheckRequest(CheckKind.MYPY, (RepositoryPath("src"),)),
            CheckRequest(CheckKind.PYTEST, (RepositoryPath("tests"),)),
        ),
        host=LocalHostConfig(
            ConfigurationRevisionRef(configuration, REVISION, Version(1, 0, 0)),
            PrincipalRef("operator", PrincipalId("forgeai")),
            PolicyRef("operator", "forgeai", Version(1, 0, 0)),
            grants,
            bindings,
            max_executions=16,
        ),
        model_selection={"revision": REVISION, "binding": binding},
        review_criteria=REVIEW_CRITERIA,
        workspace_scope=scope,
        context_paths=context_paths,
    )
