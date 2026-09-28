"""Explicit single-operator reference host; no implicit authority from env data."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from legoai.capabilities.values import (
    CapabilityOffer,
    CapabilityRequirement,
    CapabilityVersionRange,
)
from legoai.execution.ports import CoordinationRequest, CoordinationResult
from legoai.execution.values import ExecutionContext, ExecutionId, SecurityContextRef
from legoai.governance.ports import SecurityContext
from legoai.governance.values import Grant, GrantId, PolicyRef, Principal
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
from legoai.plugins.values import PluginDeclaration, PluginId
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
from legoai.reference.plugins import activate, admit, initialize, inspect, validate

from .comfyui import HARD_MAX_WAIT_SECONDS
from .composition import OFFER, TRY_ON_OFFER, Contribution, select
from .ports import TextToImagePort, VirtualTryOnPort
from .values import ApprovedWorkflowRef


@dataclass(frozen=True)
class LocalSession:
    coordinator: ExecutionCoordinator
    ready: CoordinationResult
    context: ExecutionContext
    contribution: Contribution
    catalog: InMemoryCatalog
    requirement: CapabilityRequirement


_NAMES = {
    OFFER: ("text-to-image", "generate-image"),
    TRY_ON_OFFER: ("virtual-try-on", "try-on"),
}


async def prepare_local(
    adapter: TextToImagePort | VirtualTryOnPort,
    revision_digest: str,
    *,
    approved: ApprovedWorkflowRef,
    timeout: float = 300,
    binding: str = "comfyui-local",
    offer: CapabilityOffer = OFFER,
) -> LocalSession:
    """Call only from an explicit operator-authorized local invocation.

    Admission/grant are host acts, never consequences of untrusted input. This
    uses existing in-memory reference authority, not multi-tenant production IAM.
    The operator owns the exact configuration digest passed here. timeout is
    the Execution deadline; pass the adapter's CompletionPolicy.max_wait_seconds.
    """
    if (
        type(timeout) not in (float, int)
        or not math.isfinite(timeout)
        or not 0 < timeout <= HARD_MAX_WAIT_SECONDS
    ):
        raise ValueError("invalid execution timeout")
    if offer not in _NAMES:
        raise ValueError("unsupported capability offer")
    application, action = _NAMES[offer]
    now = datetime.now(UTC)
    tenant = TenantContext(TenantId("local-operator"))
    target = ConfigurationRef(
        ApplicationRef(
            ReferenceScope("local-host", tenant.tenant_id),
            ApplicationId(application),
        ),
        "generation",
    )
    revision = ConfigurationRevisionRef(target, revision_digest, Version(1, 0, 0))
    operation = OperationRef(target, OperationId(uuid4().hex), action)
    principal = Principal(PrincipalRef("local-host", PrincipalId("operator")))
    grant = Grant(
        GrantId(uuid4().hex),
        principal,
        principal,
        tenant,
        "invoke-capability",
        offer.capability.value,
        False,
        now,
        now + timedelta(seconds=timeout + 30),
    )
    policy = PolicyRef("local-host", "operator-generation", Version(1, 0, 0))
    security = SecurityContext(
        principal,
        tenant,
        operation,
        grant.action,
        grant.resource_scope,
        grant,
        None,
        policy,
        now,
    )
    approvals = InMemoryApprovalRegistry()
    evaluator = DeterministicAuthorizationEvaluator(
        InMemoryGrantRegistry(), approvals, InMemoryPolicyRegistry()
    )
    catalog = InMemoryCatalog()
    declaration = PluginDeclaration(
        PluginId("legoai", "local-comfyui"), Version(1, 0, 0), (offer,)
    )
    validated = validate(inspect(declaration), declaration, evaluated_at=now)
    record = admit(
        validated, tenant, PluginAdmissionId(uuid4().hex), established_at=now
    )
    active = activate(initialize(record, established_at=now), established_at=now)
    entry = catalog.publish(active, declaration, offer, established_at=now)
    contribution = Contribution(binding, revision, entry, active, approved, adapter)
    requirement = CapabilityRequirement(
        offer.capability, CapabilityVersionRange(offer.version)
    )
    chosen = select(
        requirement,
        contribution.binding,
        revision,
        (contribution,),
        catalog,
        now,
        offer=offer,
    )
    security_ref = SecurityContextRef("local-host", uuid4().hex)
    registry = StaticSecurityContextRegistry()
    registry.register(security_ref, security)
    coordinator = ExecutionCoordinator(
        registry,
        DeterministicDispatchArbiter(
            evaluator, catalog, InMemoryEvidenceCustody(), approvals
        ),
    )
    context = ExecutionContext(
        ExecutionId(uuid4().hex),
        operation,
        tenant,
        security_ref,
        CorrelationId(uuid4().hex),
        None,
        now + timedelta(seconds=timeout),
        None,
    )
    ready = await coordinator.coordinate(CoordinationRequest(context, chosen.entry))
    return LocalSession(coordinator, ready, context, chosen, catalog, requirement)
