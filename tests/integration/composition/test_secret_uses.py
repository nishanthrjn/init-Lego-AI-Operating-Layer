"""OPENAI-COMPATIBLE-REMOTE-1: per-invocation exact Secret uses of one revision.

One S1 revision serves many uses; each use has its own plan, use id, state,
currentness, Approval consumption, durable attribution and at most one
acceptance. The ledger incarnation's single Stage-A binding is taken once by
the factory and can never be reset. Offline, synthetic canary material only.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from legoai.capabilities.ports import CatalogEntry
from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.governance.ports import SecretAccessRequest, SecurityContext
from legoai.governance.secret import (
    SecretRef,
    SecretUseId,
    SecretUsePlan,
    UseRecoveryCategory,
)
from legoai.governance.values import Approval, ApprovalId, Grant
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import RequestId
from legoai.kernel.references import OperationRef
from legoai.plugins.ports import (
    PluginAdmissionId,
    PluginLifecycleRecord,
    PluginLifecycleState,
)
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.reference._custody_sqlite import _ScopeDenied
from legoai.reference._durable_evidence import _EvidenceStore
from legoai.reference._secret_domain import _OrderingDomain
from legoai.reference._secret_ledger import _SecretLedger
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.governance import (
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)
from legoai.reference.secret import _ProvisionedSecretSource, _SecretClock
from legoai.runtime._composition.secret import _SecretUses, _SyntheticSecretAccess
from tests.support.custody_scenario import NOW, access, plan

CANARY = "uses-CANARY-DO-NOT-LEAK-40917"

type Participants = tuple[
    CatalogEntry,
    _OrderingDomain,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
    InMemoryApprovalRegistry,
    InMemoryCatalog,
    _SecretLedger,
    _EvidenceStore,
    _SecretClock,
]


@dataclass
class Setup:
    uses: _SecretUses
    source: _ProvisionedSecretSource
    reference: SecretRef
    participants: Participants
    grants: InMemoryGrantRegistry


@contextmanager
def factory(directory: Path) -> Iterator[Setup]:
    p = plan()
    domain = _OrderingDomain()
    source = _ProvisionedSecretSource(domain, p.secret.scope)
    reference = source.provision(p.secret.identity, p.purpose, p.consumer, CANARY)
    tenant = TenantContext(p.secret.scope.tenant_id)
    grants = InMemoryGrantRegistry(_domain=domain)
    policies = InMemoryPolicyRegistry(_domain=domain)
    approvals = InMemoryApprovalRegistry(_domain=domain)
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
    _SecretLedger.provision(source_path)
    _EvidenceStore.provision(custody_path)
    ledger = _SecretLedger(source_path, access(), domain)
    custody = _EvidenceStore(custody_path, access(), domain)
    participants: Participants = (
        entry,
        domain,
        grants,
        policies,
        approvals,
        catalog,
        ledger,
        custody,
        _SecretClock(domain, NOW),
    )
    try:
        uses = _SecretUses(*participants, source)
        yield Setup(uses, source, reference, participants, grants)
    finally:
        custody.close()
        ledger.close()


def request(x: Setup, key: str, *, approval: str | None = None) -> SecretAccessRequest:
    base = plan()
    p: SecretUsePlan = replace(
        base,
        use_id=SecretUseId(key),
        secret=x.reference.exact,
        approval_id=None if approval is None else ApprovalId(approval),
        duty_id=f"duty-{key}",
        pre_submission=RequestId(f"pre-{key}"),
        post_submission=RequestId(f"post-{key}"),
    )
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
    granted = (
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
        granted,
        p.policy,
        NOW,
    )
    return SecretAccessRequest(x.reference, p, context)


def test_one_revision_serves_independent_exact_uses(tmp_path: Path) -> None:
    with factory(tmp_path) as x:
        facts = []
        for key in ("use-1", "use-2", "use-3"):
            r = request(x, key)
            use = x.uses.admit(r)
            facts.append(use._accept(r))
            status = use.record_secret_use(r)
            assert status.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTED
        assert [f.plan.use_id.value for f in facts] == ["use-1", "use-2", "use-3"]
        assert {f.plan.secret for f in facts} == {x.reference.exact}


def test_a_use_is_admitted_and_accepted_at_most_once(tmp_path: Path) -> None:
    with factory(tmp_path) as x:
        r = request(x, "use-1")
        use = x.uses.admit(r)
        use._accept(r)
        with pytest.raises(PermissionError):
            use._accept(r)  # one exact acceptance per use
        with pytest.raises(PermissionError):
            x.uses.admit(r)  # the same use id is never admitted again


def test_the_factory_holds_the_single_stage_a_binding(tmp_path: Path) -> None:
    with factory(tmp_path) as x:
        r = request(x, "use-1")
        with pytest.raises(_ScopeDenied):
            _SyntheticSecretAccess(r, *x.participants, x.source)
        with pytest.raises(_ScopeDenied):
            _SecretUses(*x.participants, x.source)


def test_retirement_refuses_new_uses_without_rewriting_old(tmp_path: Path) -> None:
    with factory(tmp_path) as x:
        first = request(x, "use-1")
        x.uses.admit(first)._accept(first)
        x.source.retire(x.reference.exact)
        second = request(x, "use-2")
        use = x.uses.admit(second)
        with pytest.raises(PermissionError):
            use.authorize_secret_use(second)
        with pytest.raises(PermissionError):
            use._accept(second)
        ledger = x.participants[6]
        assert isinstance(ledger, _SecretLedger)
        status = ledger.status(first.plan.use_id, access())
        assert status is not None and status.accepted_fact is not None


def test_grant_revocation_is_current_for_every_new_use(tmp_path: Path) -> None:
    with factory(tmp_path) as x:
        first = request(x, "use-1")
        x.uses.admit(first)._accept(first)
        x.grants.revoke(first.plan.grant_id)
        second = request(x, "use-2")
        with pytest.raises(PermissionError):
            x.uses.admit(second)._accept(second)


def test_each_use_consumes_its_own_approval(tmp_path: Path) -> None:
    with factory(tmp_path) as x:
        for key, approval in (("use-1", "approval-1"), ("use-2", "approval-2")):
            r = request(x, key, approval=approval)
            x.uses.admit(r)._accept(r)
        reused = request(x, "use-3", approval="approval-1")
        with pytest.raises(PermissionError):
            x.uses.admit(reused)._accept(reused)


def test_cancelling_one_use_does_not_touch_another(tmp_path: Path) -> None:
    with factory(tmp_path) as x:
        first, second = request(x, "use-1"), request(x, "use-2")
        a, b = x.uses.admit(first), x.uses.admit(second)
        a._state.cancel()
        with pytest.raises(PermissionError):
            a._accept(first)
        assert b._accept(second).plan.use_id.value == "use-2"


def test_factory_requires_s1_and_its_own_identity(tmp_path: Path) -> None:
    with factory(tmp_path) as x:
        r = request(x, "use-1")
        with pytest.raises(TypeError):
            _SecretUses(*x.participants, None)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            _SyntheticSecretAccess(
                r,
                *x.participants,
                x.source,
                uses=object(),  # type: ignore[arg-type]
            )


def test_admission_is_bounded(tmp_path: Path) -> None:
    with factory(tmp_path) as x:
        x.uses._admitted = {f"use-{i}" for i in range(4096)}
        with pytest.raises(PermissionError):
            x.uses.admit(request(x, "one-more"))


def test_no_material_in_factory_or_use_representations(tmp_path: Path) -> None:
    with factory(tmp_path) as x:
        r = request(x, "use-1")
        use = x.uses.admit(r)
        use._accept(r)
        for value in (x.uses, use, x.source, r):
            assert CANARY not in repr(value) + str(value)
    for file in tmp_path.rglob("*"):
        if file.is_file():
            assert CANARY.encode() not in file.read_bytes()
