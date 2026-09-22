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

Gate-2 M10: `ExecutionCoordinator` (below) is ADR-015's "single structured
asyncio supervisor" (SS4, Option C), narrowed to exactly the minimum slice
this batch owns -- orchestrate one admitted Execution up to, but never
across, the ADR-007 dispatch boundary `DeterministicDispatchArbiter`
already gates. `coordinate()` drives `created -> admitted ->` either
`running` (a `DispatchPermit` was obtained; M10's job ends here, handed off
inert and unconsumed for a later M11 to actually invoke) or `rejected`
(M9 returned DENIED/UNAVAILABLE/STALE, the Coordinator's own deadline
already elapsed, or an unexpected internal fault occurred during
preparation) or `cancelled` (the caller's own task was cancelled before
either of those was reached). SPEC SS5.1's exact transition text is
`_allowed_next_states`' only source; `FAILED` and `CANCELLING` never appear
in output because SPEC SS5.1 defines no `admitted -> failed` edge and no
`admitted -> cancelled` intermediate -- both are reachable only from
running/waiting/suspended work, which this batch's Coordinator never
enters for its own preparation faults, since a permit obtained is the
exact instant it hands off and stops.

No capability/provider invocation, no Plugin call, no network/filesystem
effect and no retry/compensation exist anywhere below. `asyncio.TaskGroup`
owns the one child task per `coordinate()` call; nothing survives past
that call's own `async with` scope -- there is no detached task, no
module-level supervisor, and no second `threading` exception beyond M9's
already-narrow one (`ExecutionCoordinator`'s own internal record uses
`asyncio.Lock`, not `threading.Lock`, per ADR-015 SS15's async-local
synchronization guidance).
"""

import asyncio
import threading
from collections.abc import Callable
from datetime import UTC, datetime

from legoai.capabilities.ports import CatalogPort
from legoai.evidence.ports import EvidenceCustodyPort
from legoai.execution.ports import (
    CoordinationOutcome,
    CoordinationRequest,
    CoordinationResult,
    DispatchArbiterPort,
    DispatchDecision,
    DispatchOutcome,
    DispatchPermit,
    DispatchRequest,
    ExecutionTransitionError,
    SecurityContextResolutionPort,
)
from legoai.execution.values import ExecutionId, ExecutionState
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


def _allowed_next_states(current: ExecutionState) -> frozenset[ExecutionState]:
    """SPEC SS5.1's exact canonical Execution lifecycle text, encoded as a
    local (not module-level) mapping so no ambient module state exists --
    mirroring `legoai.reference.plugins._allowed_next_states`'s established
    pattern for ADR-006's Plugin lifecycle (Gate-2 M5).

    Quoting SPEC SS5.1 exactly: "created -> admitted -> running <-> waiting.
    Running or waiting MAY enter suspended; suspended -> admitted after
    revalidation. Created MAY be rejected or cancelled; ... admitted MAY be
    cancelled or fail admission revalidation into rejected. ... Running MAY
    succeed or fail. Running, waiting, or suspended MAY enter cancelling ->
    cancelled. Waiting/suspended MAY fail on deadline or unrecoverable
    conditions; cancelling MAY fail if cancellation cannot be completed...
    Terminal states are succeeded, failed, cancelled, rejected."

    No `admitted -> failed` edge exists in this text -- FAILED is reachable
    only from running/waiting/suspended/cancelling, never from
    created/admitted. `ExecutionCoordinator` (Gate-2 M10) never reaches
    running for its own internal faults, so it never produces FAILED; this
    table still carries the full graph (including edges M10 never takes)
    so a later batch that genuinely reaches running/waiting/suspended can
    reuse it unchanged.
    """
    table: dict[ExecutionState, frozenset[ExecutionState]] = {
        ExecutionState.CREATED: frozenset(
            {
                ExecutionState.ADMITTED,
                ExecutionState.REJECTED,
                ExecutionState.CANCELLED,
            }
        ),
        ExecutionState.ADMITTED: frozenset(
            {
                ExecutionState.RUNNING,
                ExecutionState.REJECTED,
                ExecutionState.CANCELLED,
            }
        ),
        ExecutionState.RUNNING: frozenset(
            {
                ExecutionState.WAITING,
                ExecutionState.SUSPENDED,
                ExecutionState.SUCCEEDED,
                ExecutionState.FAILED,
                ExecutionState.CANCELLING,
            }
        ),
        ExecutionState.WAITING: frozenset(
            {
                ExecutionState.RUNNING,
                ExecutionState.SUSPENDED,
                ExecutionState.CANCELLING,
                ExecutionState.FAILED,
            }
        ),
        ExecutionState.SUSPENDED: frozenset(
            {
                ExecutionState.ADMITTED,
                ExecutionState.CANCELLING,
                ExecutionState.FAILED,
            }
        ),
        ExecutionState.CANCELLING: frozenset(
            {ExecutionState.CANCELLED, ExecutionState.FAILED}
        ),
        ExecutionState.SUCCEEDED: frozenset(),
        ExecutionState.FAILED: frozenset(),
        ExecutionState.CANCELLED: frozenset(),
        ExecutionState.REJECTED: frozenset(),
    }
    return table[current]


class _PreparationFailed(Exception):
    """Internal-only signal that `ExecutionCoordinator._run_prepared`'s
    single supervised child raised an unexpected, unclassified exception
    (ADR-015 SS16: "An unclassified internal execution fault may use
    ExecutionFailure"). Never escapes `ExecutionCoordinator`; `coordinate`
    always converts it to a `CoordinationResult` before returning.
    Deliberately not a canonical error category itself -- Python exception
    classes never become one (ADR-015 SS7: "Python ExceptionGroup and
    CancelledError remain implementation mechanics, never canonical
    result/error classes").
    """


class ExecutionCoordinator:
    """Gate-2 M10: the minimum ADR-015 structured-supervision Coordinator --
    see this module's docstring for the exact scope boundary. Composed from
    two already-established Ports (`SecurityContextResolutionPort`,
    `DispatchArbiterPort` -- the latter, per this task's own instruction,
    not the concrete `DeterministicDispatchArbiter`, so an alternative
    conforming arbiter realization is equally usable).

    `clock` isolates current-time acquisition (task's own clock-seam
    requirement) behind one narrow injectable seam instead of scattering
    `datetime.now()` calls; it supplies the semantic wall-clock instant
    compared against `ExecutionContext.deadline`. It is never the same
    clock domain as `asyncio`'s own monotonic scheduling clock --
    `coordinate` converts the wall-clock deadline to a *relative* delay
    before ever handing it to `asyncio.timeout`, which owns monotonic
    scheduling internally.

    Constructing this class starts no task, thread or event loop (F8b/M9's
    established construction-inertness discipline extended to M10).
    """

    def __init__(
        self,
        resolver: SecurityContextResolutionPort,
        arbiter: DispatchArbiterPort,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._resolver = resolver
        self._arbiter = arbiter
        self._clock = clock
        self._states: dict[ExecutionId, ExecutionState] = {}
        self._lock = asyncio.Lock()

    async def current_state(self, execution_id: ExecutionId) -> ExecutionState | None:
        """Diagnostic-only snapshot of this Coordinator's own internal
        runtime record -- never M1's immutable `ExecutionContext`/
        `ExecutionResult`, and never authoritative durable state (ADR-015
        SS5: "The live registry is a bounded technical index, not
        authoritative state"). `None` means this Coordinator has not yet
        recorded any transition for this `ExecutionId`.
        """
        async with self._lock:
            return self._states.get(execution_id)

    async def _transition(
        self, execution_id: ExecutionId, target: ExecutionState
    ) -> None:
        async with self._lock:
            current = self._states.get(execution_id, ExecutionState.CREATED)
            if target not in _allowed_next_states(current):
                raise ExecutionTransitionError(
                    f"{current.value} cannot transition to {target.value}"
                )
            self._states[execution_id] = target

    async def coordinate(self, request: CoordinationRequest) -> CoordinationResult:
        """Admit, supervise and (if and only if M9 permits) hand off one
        Execution -- never invoking a capability itself. `coordinate`
        performs the `created -> admitted` transition internally as its
        first step: this reference slice has no separately observable
        created-only phase with genuinely distinct data before admission
        (ADR-015 SS6.1's durable-acceptance stage is deferred; see this
        module's docstring), so there is no narrower place to expose it.

        Raises `ExecutionTransitionError` if called more than once for the
        same `execution_id` after it has already reached a
        non-`created` state (a caller precondition violation, not a
        dispatch outcome). Raises `asyncio.CancelledError` if the caller's
        own task is cancelled before a permit was obtained or a rejection
        was recorded -- this Coordinator never swallows its own
        cancellation (ADR-015 SS7); it records `CANCELLED` in its internal
        record first, then re-raises.
        """
        if type(request) is not CoordinationRequest:
            raise TypeError("coordinate requires CoordinationRequest")
        context = request.context
        execution_id = context.execution_id
        await self._transition(execution_id, ExecutionState.ADMITTED)

        deadline = context.deadline
        now = self._clock()
        if deadline is not None and now >= deadline:
            # ADR-015 timeline 5: "Deadline expires while queued" -- do not
            # arbitrate/invoke unnecessarily; apply the canonical
            # never-started disposition directly.
            await self._transition(execution_id, ExecutionState.REJECTED)
            return self._rejected(execution_id, ErrorCategory.DEADLINE_EXCEEDED)

        try:
            if deadline is not None:
                delay = (deadline - now).total_seconds()
                async with asyncio.timeout(delay):
                    decision = await self._run_prepared(request)
            else:
                decision = await self._run_prepared(request)
        except TimeoutError:
            await self._transition(execution_id, ExecutionState.REJECTED)
            return self._rejected(execution_id, ErrorCategory.DEADLINE_EXCEEDED)
        except _PreparationFailed:
            await self._transition(execution_id, ExecutionState.REJECTED)
            return self._rejected(execution_id, ErrorCategory.EXECUTION_FAILURE)
        except asyncio.CancelledError:
            # Bounded owned bookkeeping only (ADR-015 SS8): record the
            # cancellation before propagating it. This performs no
            # protected effect and awaits no child/worker -- just one
            # already-uncontended `asyncio.Lock` acquisition -- so no
            # shielding is required to keep it within a narrow bound.
            await self._transition(execution_id, ExecutionState.CANCELLED)
            raise

        if decision is None:
            # The SecurityContextRef could not currently be resolved.
            await self._transition(execution_id, ExecutionState.REJECTED)
            return self._rejected(execution_id, ErrorCategory.DEPENDENCY_FAILURE)

        if decision.outcome is DispatchOutcome.PERMITTED:
            await self._transition(execution_id, ExecutionState.RUNNING)
            return CoordinationResult(
                execution_id,
                CoordinationOutcome.READY,
                ExecutionState.RUNNING,
                decision.permit,
                None,
            )

        # DENIED, UNAVAILABLE or STALE: never began, never reaches running.
        # `decision.category` is M9's own already-correct classification
        # (AuthorizationDenied/DependencyFailure/Conflict) -- reused
        # verbatim, never re-derived or re-mapped.
        await self._transition(execution_id, ExecutionState.REJECTED)
        return self._rejected(execution_id, decision.category)

    async def _run_prepared(
        self, request: CoordinationRequest
    ) -> DispatchDecision | None:
        """Owns exactly one supervised child task per call, inside its own
        `asyncio.TaskGroup` scope -- ADR-015 SS5/SS7's "every live task
        belongs to a named bounded root duty" and "no unmanaged
        fire-and-forget task". Nothing survives this method's return: the
        `async with` block joins the child before control returns to
        `coordinate`.
        """
        try:
            async with asyncio.TaskGroup() as group:
                task = group.create_task(self._resolve_and_arbitrate(request))
        except* Exception as failures:
            raise _PreparationFailed() from failures
        return task.result()

    async def _resolve_and_arbitrate(
        self, request: CoordinationRequest
    ) -> DispatchDecision | None:
        context = request.context
        security_context = await self._resolver.resolve(
            context.security_context_ref, context.tenant_context
        )
        if security_context is None:
            return None
        dispatch_request = DispatchRequest(
            security_context, request.resolved_entry, request.required_evidence_ids
        )
        return self._arbiter.arbitrate(dispatch_request, evaluated_at=self._clock())

    @staticmethod
    def _rejected(
        execution_id: ExecutionId, category: ErrorCategory | None
    ) -> CoordinationResult:
        return CoordinationResult(
            execution_id,
            CoordinationOutcome.REJECTED,
            ExecutionState.REJECTED,
            None,
            category,
        )
