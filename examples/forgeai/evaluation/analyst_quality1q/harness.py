"""One independent, governed RepositoryAnalyst call per (case, repetition).

Each call gets a fresh public local host whose only grants are named-file read
for model analysis and governed Chat, a fresh evidence reader bound to exactly
the confirmed files, and the unchanged Analyst. The Analyst's own result is
authoritative; the reply text is classified in memory, cross-checked and then
dropped. Nothing is retried, repaired or written, and no output becomes authority.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from content_discovery1.stages import Workspace
from legoai_engineering.analyst.api import RepositoryAnalyst
from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.analyst.values import (
    RepositoryAnalysisRequest,
    RepositoryAnalysisResult,
    RepositoryAnalysisStatus,
)
from legoai_engineering.repository.workspace import RepositoryPath

from analyst_quality1q.classify import ANSWERS, Category, classify
from analyst_quality1q.data import Case
from legoai.execution.agent.values import AgentExecutionStatus
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
    GovernedHost,
    LocalHostConfig,
    ModelBindingConfig,
    ModelPurpose,
    OperatorGrant,
)
from legoai.runtime.local import open_local_host

BindingFactory = Callable[[Case, int], ModelBindingConfig]
GRANTED_ACTIONS = frozenset(
    {REPOSITORY_READ_ACTION, "invoke-capability"}
)  # never write or check


def host(
    binding: ModelBindingConfig, now: datetime
) -> tuple[GovernedHost, ConfigurationRef]:
    reference = ConfigurationRef(
        ApplicationRef(
            ReferenceScope("operator", TenantId("analyst-quality")),
            ApplicationId("analyst-quality"),
        ),
        "workspace",
    )
    grants = (
        OperatorGrant(
            GrantId("read"),
            REPOSITORY_READ_ACTION,
            "workspace",
            now - timedelta(hours=1),
            now + timedelta(hours=2),
        ),
        OperatorGrant(
            GrantId("chat"),
            "invoke-capability",
            ModelPurpose.CHAT.capability_id.value,
            now - timedelta(hours=1),
            now + timedelta(hours=2),
        ),
    )
    config = LocalHostConfig(
        ConfigurationRevisionRef(reference, "r1", Version(1, 0, 0)),
        PrincipalRef("operator", PrincipalId("analyst-quality")),
        PolicyRef("operator", "analyst-quality", Version(1, 0, 0)),
        grants,
        (binding,),
        max_executions=4,
    )
    opened = open_local_host(
        config,
        {"revision": "r1", "binding": binding.binding_id},
        clock=lambda: now,
    )
    return opened, reference


@dataclass(frozen=True)
class CallResult:
    """Content-free view of one call; no reply, prompt or file text."""

    status: str  # runtime status value
    category: Category
    relevant: tuple[str, ...] | None  # accepted structured relevant_files
    accepted_paths: tuple[str, ...]  # every accepted structured path
    reads: tuple[str, ...]
    seconds: float


async def _analyze(
    case: Case, binding: ModelBindingConfig
) -> tuple[RepositoryAnalysisResult, Workspace]:
    now = datetime.now(UTC)
    governed, reference = host(binding, now)
    workspace = Workspace(case.files)
    paths = tuple(RepositoryPath(f.path) for f in case.files)
    reader = AuthorizedRepositoryEvidence(
        reference,
        workspace,
        governed.security_context(
            reference, REPOSITORY_READ_ACTION, reference.instance
        ),
        governed.authorization,
        paths,
        lambda: now,
    )
    result = await RepositoryAnalyst(reader, governed.agent_runtime()).analyze(
        RepositoryAnalysisRequest(
            case.question, paths, governed.model_execution(ModelPurpose.CHAT)
        )
    )
    return result, workspace


def reconcile(result: RepositoryAnalysisResult, case: Case) -> CallResult:
    """Classify in memory and cross-check with the Analyst's own verdict."""
    agent = result.agent_result
    accepted: tuple[str, ...] = ()
    relevant: tuple[str, ...] | None = None
    if result.analysis is not None:
        relevant = tuple(sorted(p.value for p in result.analysis.relevant_files))
        accepted = tuple(
            sorted(
                {
                    *relevant,
                    *(p.value for f in result.analysis.findings for p in f.paths),
                }
            )
        )
    if result.status is RepositoryAnalysisStatus.MODEL_FAILURE:
        category = Category.MODEL_FAILURE
    elif agent is not None and agent.status is AgentExecutionStatus.OUTPUT_INVALID:
        category = Category.OUTPUT_CONTRACT_INVALID
    elif agent is None or agent.output is None:
        category = Category.CLASSIFIER_DISAGREEMENT
    else:
        category, status, classified = classify(agent.output, case.supplied)
        runtime_valid = result.status in ANSWERS
        if (category is Category.VALID) != runtime_valid or (
            runtime_valid and (status != result.status.value or classified != relevant)
        ):
            category = Category.CLASSIFIER_DISAGREEMENT
    return CallResult(result.status.value, category, relevant, accepted, (), 0.0)


def run_call(case: Case, binding: ModelBindingConfig) -> CallResult:
    started = time.perf_counter()
    result, workspace = asyncio.run(_analyze(case, binding))
    seconds = time.perf_counter() - started
    view = reconcile(result, case)
    return CallResult(
        view.status,
        view.category,
        view.relevant,
        view.accepted_paths,
        tuple(workspace.reads),
        round(seconds, 3),
    )
