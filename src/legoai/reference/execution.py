"""Gate-2 M9: deterministic reference realization of `DispatchArbiterPort`
(ADR-007 SS6.2's exclusive ordered section).

`DeterministicDispatchArbiter.arbitrate` implements exactly the ordering
ADR-007 SS6.2 requires, all inside one `threading.Lock` (a **reference
lock scoped to one arbiter instance and one process only** -- it makes no
multi-process or distributed exclusivity claim; ADR-007 SS13's own initial
scope is "one trusted local arbitration process"):

    acquire exclusive gate
    -> re-evaluate current authorization (never a cached/historical decision)
    -> re-check current Catalog publication of the resolved candidate
    -> confirm required evidence is still present
    -> commit Approval-use consumption (if an Approval participates)
    -> issue an inert permit
    release gate

Preparation (resolving a `CapabilityResolution`, obtaining pre-effect
evidence custody, constructing the `SecurityContext`) happens entirely
*before* this call, per ADR-007 SS6.1 -- `arbitrate` re-validates, it does
not re-derive those facts from scratch, and it performs no external
effect, provider invocation, or Plugin activation of any kind.

No exactly-once claim: this reference realization proves only that its own
exclusive gate serializes concurrent `arbitrate` calls against the same
in-memory Ports it was constructed with. It says nothing about a
persisted, restart-surviving operation ledger (deferred; see
`legoai.execution.ports`'s module docstring).
"""

import threading
from datetime import datetime

from legoai.capabilities.ports import CatalogPort
from legoai.evidence.ports import EvidenceCustodyPort
from legoai.execution.ports import (
    DispatchDecision,
    DispatchOutcome,
    DispatchPermit,
    DispatchRequest,
)
from legoai.governance.ports import (
    ApprovalConsumptionPort,
    AuthorizationOutcome,
    AuthorizationPort,
)
from legoai.kernel.errors import ErrorCategory
from legoai.kernel.references import OperationRef


class DeterministicDispatchArbiter:
    """Reference `DispatchArbiterPort` realization composed from four
    already-established Ports. Deterministic given deterministic Port
    answers; the only genuine nondeterminism in a live process is thread
    interleaving, which the internal lock serializes.
    """

    def __init__(
        self,
        authorization: AuthorizationPort,
        catalog: CatalogPort,
        evidence: EvidenceCustodyPort,
        approval_consumption: ApprovalConsumptionPort,
    ) -> None:
        self._authorization = authorization
        self._catalog = catalog
        self._evidence = evidence
        self._approval_consumption = approval_consumption
        self._lock = threading.Lock()

    def arbitrate(
        self, request: DispatchRequest, *, evaluated_at: datetime
    ) -> DispatchDecision:
        if type(request) is not DispatchRequest:
            raise TypeError("arbitrate requires DispatchRequest")
        if type(evaluated_at) is not datetime:
            raise TypeError("arbitrate evaluated_at must be datetime")
        if evaluated_at.tzinfo is None:
            raise ValueError("arbitrate evaluated_at must be timezone-aware")

        operation = request.security_context.operation
        with self._lock:
            security_decision = self._authorization.evaluate(request.security_context)
            if security_decision.outcome is AuthorizationOutcome.DENIED:
                return self._denied(operation, evaluated_at, security_decision.category)
            if security_decision.outcome is AuthorizationOutcome.UNAVAILABLE:
                return self._unavailable(
                    operation, evaluated_at, security_decision.category
                )

            snapshot = self._catalog.snapshot(request.security_context.tenant_context)
            if request.resolved_entry not in snapshot.entries:
                # ADR-006 SS9: "publishing a row is not ... an irrevocable
                # eligibility guarantee" -- the entry a prior resolution
                # picked is no longer currently published; treat this as a
                # stale prepared resolution (ADR-008's CONFLICT category:
                # "stale revision/equivalence/use"), never a silent permit.
                return self._stale(operation, evaluated_at)

            for evidence_id in request.required_evidence_ids:
                record = self._evidence.read(
                    evidence_id, request.security_context.tenant_context
                )
                if record is None:
                    return self._unavailable(
                        operation, evaluated_at, ErrorCategory.DEPENDENCY_FAILURE
                    )

            # `security_decision.outcome is ALLOWED` already proves (via
            # `DeterministicAuthorizationEvaluator.evaluate`, called above
            # under this same gate) that the Approval -- if one participates
            # -- currently covers this operation and has not exhausted its
            # uses: `evaluate` and this arbiter share the same
            # `approval_use`/`approval_consumption` Port state, and nothing
            # can observe or mutate that state between the two calls while
            # the gate lock is held. Re-deriving that verdict here would be
            # unreachable dead code, not extra safety. Only the commit step
            # -- actually consuming the use -- is this arbiter's own job.
            approval = request.security_context.approval
            if approval is not None:
                self._approval_consumption.consume(approval)

            permit = DispatchPermit(
                operation,
                request.resolved_entry,
                snapshot.revision,
                security_decision,
                evaluated_at,
            )
            return DispatchDecision(
                DispatchOutcome.PERMITTED, operation, evaluated_at, None, permit
            )

    @staticmethod
    def _denied(
        operation: OperationRef,
        evaluated_at: datetime,
        category: ErrorCategory | None,
    ) -> DispatchDecision:
        return DispatchDecision(
            DispatchOutcome.DENIED, operation, evaluated_at, category, None
        )

    @staticmethod
    def _unavailable(
        operation: OperationRef,
        evaluated_at: datetime,
        category: ErrorCategory | None,
    ) -> DispatchDecision:
        return DispatchDecision(
            DispatchOutcome.UNAVAILABLE, operation, evaluated_at, category, None
        )

    @staticmethod
    def _stale(operation: OperationRef, evaluated_at: datetime) -> DispatchDecision:
        return DispatchDecision(
            DispatchOutcome.STALE,
            operation,
            evaluated_at,
            ErrorCategory.CONFLICT,
            None,
        )
