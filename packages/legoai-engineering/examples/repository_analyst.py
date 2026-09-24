"""Offline Repository Analyst technical composition, with explicit read grants."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from legoai.execution.values import ExecutionContext, ExecutionId, SecurityContextRef
from legoai.governance.ports import SecurityContext
from legoai.governance.values import Grant, GrantId, PolicyRef, Principal
from legoai.intelligence.model.routing import ModelBinding, ModelRequirement
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ProviderId,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import (
    ApplicationId,
    CorrelationId,
    OperationId,
    PrincipalId,
    TenantId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginAdmissionId
from legoai.plugins.values import PluginId
from legoai.reference.agent import OneStepAgentRuntime
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.evidence import InMemoryEvidenceCustody
from legoai.reference.execution import (
    DeterministicDispatchArbiter,
    ExecutionCoordinator,
    StaticSecurityContextRegistry,
)
from legoai.reference.governance import (
    DeterministicAuthorizationEvaluator,
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)
from legoai.reference.model import ollama_chat_capability_id, ollama_declaration
from legoai.reference.model_routing import DeterministicModelRouter
from legoai.reference.plugins import activate, admit, initialize, inspect, validate
from legoai.runtime._composition.agent import GovernedAgentChat
from legoai.runtime._composition.model_governed import ConfiguredModelBinding
from legoai_engineering.analyst._composition import AuthorizedRepositoryEvidence
from legoai_engineering.analyst.api import RepositoryAnalyst
from legoai_engineering.analyst.values import RepositoryAnalysisRequest
from legoai_engineering.repository.local import LocalRepositoryWorkspace, LocalWorkspaceRoot
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy


class StaticModel:
    """Demonstration-only ModelPort; performs no network or tool operation."""

    def __init__(self, output: str) -> None:
        self.output = output
        self.calls = 0
        self.last_request: ChatRequest | None = None
        self.error: Exception | None = None

    async def chat(self, request: ChatRequest) -> ChatResult:
        self.calls += 1
        self.last_request = request
        if self.error is not None:
            raise self.error
        return ChatResult(self.output, ModelId("static"), ProviderId("demo"), None)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        raise NotImplementedError("Chat-only demo")


def create_demo(
    root: Path,
    output: str,
    *,
    route_count: int = 1,
    read_allowed: bool = True,
    targets: tuple[RepositoryPath, ...] = (RepositoryPath("a.py"), RepositoryPath("b.py")),
) -> tuple[RepositoryAnalyst, RepositoryAnalysisRequest, StaticModel]:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    version = Version(1, 0, 0)
    tenant = TenantContext(TenantId("demo"))
    target = ConfigurationRef(
        ApplicationRef(
            ReferenceScope("operator", tenant.tenant_id), ApplicationId("demo")
        ),
        "models",
    )
    operation = OperationRef(target, OperationId("analyze"), "configuration")
    revision = ConfigurationRevisionRef(target, "r1", version)
    requirement = ModelRequirement("engineering-reasoning")
    binding = ModelBinding("static", requirement, ModelId("static"), ProviderId("demo"))
    # Reuse the existing v1 Chat capability, supplied by an explicit fake Plugin.
    # The historical declaration helper constructs data, never an Ollama client.
    declaration = replace(
        ollama_declaration(), plugin_id=PluginId("legoai.demo", "static")
    )
    catalog = InMemoryCatalog()
    record = admit(
        validate(inspect(declaration), declaration, evaluated_at=now),
        tenant,
        PluginAdmissionId("demo"),
        established_at=now,
    )
    record = activate(initialize(record, established_at=now), established_at=now)
    entry = catalog.publish(
        record, declaration, declaration.offers[0], established_at=now
    )
    principal = Principal(PrincipalRef("operator", PrincipalId("service")))
    grant = Grant(
        GrantId("demo"),
        principal,
        principal,
        tenant,
        "invoke-capability",
        ollama_chat_capability_id().value,
        False,
        now,
        now + timedelta(hours=1),
    )
    security = SecurityContext(
        principal,
        tenant,
        operation,
        "invoke-capability",
        ollama_chat_capability_id().value,
        grant,
        None,
        PolicyRef("operator", "demo", version),
        now,
    )
    security_ref = SecurityContextRef("operator", "demo")
    resolver = StaticSecurityContextRegistry()
    resolver.register(security_ref, security)
    approvals = InMemoryApprovalRegistry()
    authorization = DeterministicAuthorizationEvaluator(
        InMemoryGrantRegistry(), approvals, InMemoryPolicyRegistry()
    )
    arbiter = DeterministicDispatchArbiter(
        authorization,
        catalog,
        InMemoryEvidenceCustody(),
        approvals,
    )
    model = StaticModel(output)
    bindings = tuple(
        replace(binding, binding_id=f"static-{i}") for i in range(route_count)
    )
    selected = bindings[0] if bindings else binding
    runtime = OneStepAgentRuntime(
        DeterministicModelRouter(revision, bindings),
        GovernedAgentChat(
            ExecutionCoordinator(resolver, arbiter, clock=lambda: now),
            ConfiguredModelBinding(revision, selected, entry, model),
        ),
    )
    workspace_reference = replace(target, instance="workspace")
    read_security = replace(
        security,
        operation=OperationRef(workspace_reference, OperationId("read"), "configuration"),
        action="read-for-model-analysis",
        resource_scope="workspace",
        grant=replace(
            grant,
            grant_id=GrantId("read"),
            action="read-for-model-analysis",
            resource_scope="workspace",
        )
        if read_allowed
        else None,
    )
    reader = AuthorizedRepositoryEvidence(
        workspace_reference,
        LocalRepositoryWorkspace(
            LocalWorkspaceRoot(root), WorkspacePolicy(8192, 8192, 16, 8, (".git", ".venv"))
        ),
        read_security,
        authorization,
        targets,
        lambda: now,
    )
    request = RepositoryAnalysisRequest(
        "Which files implement the supplied behavior?",
        targets,
        ExecutionContext(
            ExecutionId("demo"),
            operation,
            tenant,
            security_ref,
            CorrelationId("demo"),
            None,
            None,
            None,
        ),
    )
    return RepositoryAnalyst(reader, runtime), request, model


async def main() -> None:
    with TemporaryDirectory(prefix="legoai-analyst-") as temporary:
        root = Path(temporary)
        (root / "a.py").write_text("def greet(): return 'hello'\n", encoding="utf-8")
        (root / "b.py").write_text("from a import greet\n", encoding="utf-8")
        output = json.dumps(
            {
                "status": "succeeded",
                "summary": "The supplied files define and import greet.",
                "relevant_files": ["a.py", "b.py"],
                "findings": [{"text": "greet is defined here.", "paths": ["a.py"]}],
                "risks": [],
                "unknowns": ["Runtime behavior was not executed."],
            }
        )
        analyst, request, model = create_demo(root, output)
        result = await analyst.analyze(request)
        assert result.analysis is not None and model.calls == 1
        print(result.status.value)
        print(", ".join(p.value for p in result.analysis.relevant_files))
        print(result.analysis.summary)


if __name__ == "__main__":
    asyncio.run(main())
