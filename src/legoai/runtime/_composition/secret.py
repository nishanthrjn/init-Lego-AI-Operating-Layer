"""Trusted Stage-A wiring, not a runtime/provider enablement.

SECRET-SOURCE-S1 reuses this exact-use composition with an operator-provisioned
material source; it adds no transport, provider or public material API.

Owners retain state. Only this composition imports their concrete realizations.
SQLite operations stay on the constructing owner thread. Foreign-thread use
fails closed; invalidating mutations use the shared domain from any thread.
No Coordinator/dispatch lock is acquired here. No worker is created or queued.
"""

import getpass
import sys
from collections.abc import Callable
from dataclasses import replace

from legoai.capabilities.ports import CatalogEntry
from legoai.evidence.custody import CustodyAccess, CustodyProfile, SourceEvidence
from legoai.governance.ports import (
    AuthorizationDecision,
    AuthorizationOutcome,
    SecretAccessRequest,
)
from legoai.governance.secret import (
    ApprovalObservation,
    SecretRef,
    SecretUseFact,
    SecretUseStatus,
    SourceEvent,
)
from legoai.reference._durable_evidence import _EvidenceStore
from legoai.reference._secret_domain import _OrderingDomain
from legoai.reference._secret_ledger import _SecretLedger
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.governance import (
    DeterministicAuthorizationEvaluator,
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)
from legoai.reference.secret import (
    _provisioned_class,
    _ProvisionedSecretSource,
    _SecretClock,
    _SecretState,
)


def _provision_interactively(
    source: _ProvisionedSecretSource,
    identity: str,
    purpose: str,
    consumer: str,
    *,
    read: Callable[[str], str] = getpass.getpass,
    interactive: Callable[[], bool] | None = None,
) -> SecretRef:
    """Bootstrap S1 from hidden interactive input (ADR-023 §8, option 1).

    The operator types the credential without echo; it never enters argv,
    environment, configuration or files, and goes straight into the protected
    source. Refused without an interactive terminal, so piped or redirected
    input (which `getpass` may echo) is never accepted. `read`/`interactive`
    exist so trusted tests can supply synthetic material; there is no other
    source and no fallback.
    """
    if type(source) is not _ProvisionedSecretSource:
        raise TypeError("trusted source composition required")
    if interactive is None:
        stdin = sys.stdin
        terminal = stdin is not None and stdin.isatty()
    else:
        terminal = interactive()
    if not terminal:
        raise PermissionError("hidden interactive input required")
    material = read("Credential (input hidden): ")
    try:
        return source.provision(identity, purpose, consumer, material)
    finally:
        del material


class _SyntheticSecretAccess:
    """One exact admitted synthetic use. Constructor inputs are trusted facts.

    Publicly constructed Grants/contexts are not authenticated by equality.
    Composition must establish them before calling this private constructor.
    Reopening stores never admits new work or restores this authority binding.
    """

    def __init__(
        self,
        request: SecretAccessRequest,
        entry: CatalogEntry,
        domain: _OrderingDomain,
        grants: InMemoryGrantRegistry,
        policies: InMemoryPolicyRegistry,
        approvals: InMemoryApprovalRegistry,
        catalog: InMemoryCatalog,
        source: _SecretLedger,
        custody: _EvidenceStore,
        clock: _SecretClock,
        material_source: _ProvisionedSecretSource | None = None,
    ) -> None:
        """`material_source` selects SECRET-SOURCE-S1: the exact-use flow is
        unchanged, but the material is the operator-provisioned revision the
        reference names instead of fresh synthetic bytes."""
        if material_source is not None and (
            type(material_source) is not _ProvisionedSecretSource
            or material_source._domain is not domain
        ):
            raise ValueError("shared ordering domain required")
        for value, kind in (
            (domain, _OrderingDomain),
            (grants, InMemoryGrantRegistry),
            (policies, InMemoryPolicyRegistry),
            (approvals, InMemoryApprovalRegistry),
            (catalog, InMemoryCatalog),
            (source, _SecretLedger),
            (custody, _EvidenceStore),
            (clock, _SecretClock),
            (request, SecretAccessRequest),
            (entry, CatalogEntry),
        ):
            if type(value) is not kind:
                raise TypeError("qualified Stage-A participants required")
        if any(
            owner._domain is not domain
            for owner in (grants, policies, approvals, catalog, source, custody, clock)
        ):
            raise ValueError("shared ordering domain required")
        p, c = request.plan, request.context
        access = CustodyAccess(p.secret.scope, p.requester)
        expected_class = (
            "synthetic" if material_source is None else _provisioned_class()
        )
        if (
            request.reference.secret_class != expected_class
            or request.reference.use_requirement != p.purpose
            or p.actor != p.requester
            or c.principal != p.requester
            or c.operation.operation_id != p.operation_id
            or c.operation.subject != p.configuration.configuration
            or c.operation.contract_identity != p.purpose
            or c.action != "secret-use"
            or c.resource_scope != p.secret.identity
            or c.tenant_context.tenant_id != p.secret.scope.tenant_id
            or c.grant is None
            or c.grant.grant_id != p.grant_id
            or c.policy_ref != p.policy
            or (c.approval.approval_id if c.approval else None) != p.approval_id
            or entry.tenant_context != c.tenant_context
            or entry.offer.capability.value != p.consumer
            or entry.offer.version != p.consumer_version
            or source._access != access
            or custody._access != access
        ):
            raise ValueError("exact Stage-A admission required")
        self._request, self._entry, self._domain = request, entry, domain
        self._approvals, self._catalog = approvals, catalog
        self._source, self._custody, self._clock = source, custody, clock
        self._access = access
        self._authorization = DeterministicAuthorizationEvaluator(
            grants, approvals, policies
        )
        source._claim_stage_a()
        self._state = _SecretState(request, domain, material_source)
        self._thread = domain.thread_identity()

    def _outside(self, request: SecretAccessRequest) -> None:
        self._domain.outside()
        if (
            type(request) is not SecretAccessRequest
            or self._domain.thread_identity() != self._thread
            or request != self._request
        ):
            raise PermissionError("Secret use unavailable")

    def _current(self, request: SecretAccessRequest) -> AuthorizationDecision:
        self._domain.held()
        if not self._source._new_work:
            raise PermissionError("Secret use unavailable")
        now = self._clock.now()
        self._state.current(request, now)
        decision = self._authorization.evaluate(
            replace(request.context, established_at=now)
        )
        if (
            decision.outcome is not AuthorizationOutcome.ALLOWED
            or self._entry
            not in self._catalog.snapshot(request.context.tenant_context).entries
        ):
            raise PermissionError("Secret use unavailable")
        return decision

    def authorize_secret_use(
        self, request: SecretAccessRequest
    ) -> AuthorizationDecision:
        self._outside(request)
        with self._domain.enter():
            return self._current(request)

    def resolve_secret_reference(self, request: SecretAccessRequest) -> SecretRef:
        self.authorize_secret_use(request)
        return request.reference

    def validate_secret_revision(self, request: SecretAccessRequest) -> SecretRef:
        return self.resolve_secret_reference(request)

    def _accept(self, request: SecretAccessRequest) -> SecretUseFact:
        self._outside(request)
        try:
            self.authorize_secret_use(request)
            p = request.plan
            # Inspection is always separate from acceptance; never call accept
            # to discover a lost acknowledgment or an earlier incarnation.
            status = self._source.prepare(p, self._access)
            if status.accepted_fact is not None or not self._source._new_work:
                raise PermissionError("Secret use unavailable")
            prepared = SecretUseFact(p, SourceEvent.PREPARED, p.prepared_at)
            self._custody.acknowledge(
                SourceEvidence(prepared, p.actor, CustodyProfile.INTACT_LOCAL_V1),
                self._access,
                recorded_at=self._clock.now(),
            )
            witness = self._custody.witness(p.pre_submission, self._access)
            self._state.acquire()
            with self._domain.enter():
                decision = self._current(request)
                self._source._ready(p, witness, decision.evaluated_at)
                material = self._state.take()
                try:
                    observation = ApprovalObservation.NOT_APPLICABLE
                    if request.context.approval is not None:
                        self._approvals._consume(request.context.approval)
                        observation = ApprovalObservation.CONSUMED
                    # Only the source's local durable transition is the effect.
                    # Evidence already acknowledged; no Evidence I/O in gate.
                    return self._source.accept(
                        p,
                        witness,
                        self._access,
                        material=material,
                        expected_material=material,
                        now=decision.evaluated_at,
                        approval=observation,
                    )
                finally:
                    del material
        finally:
            self._state.discard()
            with self._domain.enter():
                self._source._discard(request.plan.use_id)

    def _inspect(self, request: SecretAccessRequest) -> SecretUseStatus | None:
        """Retained exact outcome under the trusted custody access binding.

        Historical attribution access does not grant a new material use. A
        restart inspection/repair host must establish this binding afresh.
        """
        self._outside(request)
        return self._source.status(request.plan.use_id, self._access)

    def record_secret_use(self, request: SecretAccessRequest) -> SecretUseStatus:
        self._outside(request)
        status = self._inspect(request)
        if status is None or status.accepted_fact is None:
            raise PermissionError("accepted Secret use unavailable")
        self._custody.acknowledge(
            SourceEvidence(
                status.accepted_fact, request.plan.actor, CustodyProfile.INTACT_LOCAL_V1
            ),
            self._access,
            recorded_at=self._clock.now(),
        )
        witness = self._custody.witness(request.plan.post_submission, self._access)
        return self._source.finish(
            request.plan.use_id,
            witness,
            self._access,
            expected_revision=status.revision,
        )
