"""Exact, offline trusted Stage-A composition fixture."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.governance.ports import SecretAccessRequest, SecurityContext
from legoai.governance.secret import SecretRef
from legoai.governance.values import Approval, Grant
from legoai.kernel.context import TenantContext
from legoai.kernel.references import OperationRef
from legoai.plugins.ports import (
    PluginAdmissionId,
    PluginLifecycleRecord,
    PluginLifecycleState,
)
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.reference._durable_evidence import _EvidenceStore
from legoai.reference._secret_domain import _OrderingDomain
from legoai.reference._secret_ledger import _SecretLedger
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.governance import (
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)
from legoai.reference.secret import _SecretClock
from legoai.runtime._composition.secret import _SyntheticSecretAccess
from tests.support.custody_scenario import NOW, access, plan


@contextmanager
def scenario(
    directory: Path, *, reopen: bool = False, with_approval: bool = True
) -> Iterator[_SyntheticSecretAccess]:
    p = plan()
    if not with_approval:
        p = replace(p, approval_id=None)
    domain = _OrderingDomain()
    tenant = TenantContext(p.secret.scope.tenant_id)
    operation = OperationRef(p.configuration.configuration, p.operation_id, p.purpose)
    grant = Grant(
        p.grant_id,
        p.actor,
        p.requester,
        tenant,
        "secret-use",
        p.secret.identity,
        False,
        NOW,
        p.expires_at,
    )
    approval = (
        None
        if p.approval_id is None
        else Approval(
            p.approval_id, operation, tenant, p.requester, p.actor, 1, NOW, p.expires_at
        )
    )
    context = SecurityContext(
        p.requester,
        tenant,
        operation,
        "secret-use",
        p.secret.identity,
        grant,
        approval,
        p.policy,
        NOW,
    )
    request = SecretAccessRequest(
        SecretRef(p.secret, "synthetic", p.purpose), p, context
    )
    grants, policies, approvals = (
        InMemoryGrantRegistry(_domain=domain),
        InMemoryPolicyRegistry(_domain=domain),
        InMemoryApprovalRegistry(_domain=domain),
    )
    catalog = InMemoryCatalog(_domain=domain)
    offer = CapabilityOffer(CapabilityId(p.consumer), p.consumer_version)
    plugin = PluginId("legoai", "synthetic")
    declaration = PluginDeclaration(plugin, p.consumer_version, (offer,), ())
    lifecycle = PluginLifecycleRecord(
        PluginAdmissionId("admission"),
        plugin,
        p.consumer_version,
        tenant,
        PluginLifecycleState.ACTIVE,
        1,
        NOW,
    )
    entry = catalog.publish(lifecycle, declaration, offer, established_at=NOW)
    source_path, custody_path = directory / "source.db", directory / "evidence.db"
    if not reopen:
        _SecretLedger.provision(source_path)
        _EvidenceStore.provision(custody_path)
    source = _SecretLedger(source_path, access(), domain)
    custody = _EvidenceStore(custody_path, access(), domain)
    try:
        yield _SyntheticSecretAccess(
            request,
            entry,
            domain,
            grants,
            policies,
            approvals,
            catalog,
            source,
            custody,
            _SecretClock(domain, NOW),
        )
    finally:
        custody.close()
        source.close()
