"""Gate-2 M5: deterministic reference realization of Plugin admission and
lifecycle transitions (ADR-006 SS8).

Every function here is a pure, side-effect-free transformation: no
filesystem/network/site-packages discovery, no dynamic import, no
`eval`/`exec`/`compile`, no activation callback, no Catalog write, no
Resource allocation, no Governance current-authority call. `inspect` reads
only an already-in-hand, already-constructed `PluginDeclaration` -- it never
imports or executes a candidate to learn its shape (ADR-006 SS5: "Descriptor
inspection uses already trusted readers and declarative metadata; it does
not run candidate activation, initialization, registration or validation
callbacks").

Trusted-host scope: this module assumes its caller already supplies a
sufficiently trusted `PluginDeclaration` under the existing Gate-1/Gate-2
trusted shared-process scope (ADR-005 SS4, ADR-006 SS2). It performs no
process isolation or sandboxing and does not admit a hostile or
insufficiently trusted candidate; ADR-012 (Proposed) would govern that
expanded threat scope, and this module does not depend on it.

Stage-collapse is structurally impossible: `validate` never calls `admit`,
`admit` never calls `initialize`, `initialize` never calls `activate`, and
none of them ever produces or references a Catalog entry -- each is an
independent function the caller invokes explicitly, one at a time, and each
new `PluginLifecycleRecord` is a fresh immutable value, never a mutation of
its predecessor.
"""

from dataclasses import replace
from datetime import datetime

from legoai.kernel.context import TenantContext
from legoai.plugins.ports import (
    DiscoveredPluginRef,
    LifecycleTransitionError,
    PluginAdmissionId,
    PluginLifecycleRecord,
    PluginLifecycleState,
    ValidationOutcome,
    ValidationResult,
)
from legoai.plugins.values import PluginDeclaration


def inspect(declaration: PluginDeclaration) -> DiscoveredPluginRef:
    """Read the identity/release an already-constructed declaration
    presents (ADR-006 SS8 `inspect_plugin`). No initialization effect.
    """
    if type(declaration) is not PluginDeclaration:
        raise TypeError("inspect requires PluginDeclaration")
    return DiscoveredPluginRef(declaration.plugin_id, declaration.release)


def validate(
    discovered: DiscoveredPluginRef,
    declaration: PluginDeclaration,
    *,
    evaluated_at: datetime,
) -> ValidationResult:
    """Confirm the inspected declaration matches what discovery claimed
    (ADR-006 SS8 `validate_plugin`: "return findings only"). This is the
    one substitution-prevention check this reference realization can make
    without fabricating unrepresented PLUGIN-SPEC fields (module docstring
    of `legoai.plugins.ports`).
    """
    if type(discovered) is not DiscoveredPluginRef:
        raise TypeError("validate requires DiscoveredPluginRef")
    if type(declaration) is not PluginDeclaration:
        raise TypeError("validate requires PluginDeclaration")
    matches = (
        declaration.plugin_id == discovered.plugin_id
        and declaration.release == discovered.release
    )
    outcome = (
        ValidationOutcome.COMPATIBLE if matches else ValidationOutcome.INCOMPATIBLE
    )
    return ValidationResult(discovered, outcome, evaluated_at)


def admit(
    validation: ValidationResult,
    tenant_context: TenantContext,
    admission_id: PluginAdmissionId,
    *,
    established_at: datetime,
) -> PluginLifecycleRecord:
    """Commit the `validated` state (ADR-006 SS4/SS8: "`admit_plugin` alone
    commits `validated`, not activation"). Refuses an incompatible finding;
    a validation report is never itself sufficient for admission.
    """
    if type(validation) is not ValidationResult:
        raise TypeError("admit requires ValidationResult")
    if type(tenant_context) is not TenantContext:
        raise TypeError("admit requires TenantContext")
    if type(admission_id) is not PluginAdmissionId:
        raise TypeError("admit requires PluginAdmissionId")
    if validation.outcome is not ValidationOutcome.COMPATIBLE:
        raise LifecycleTransitionError("cannot admit an incompatible declaration")
    return PluginLifecycleRecord(
        admission_id,
        validation.discovered.plugin_id,
        validation.discovered.release,
        tenant_context,
        PluginLifecycleState.VALIDATED,
        1,
        established_at,
    )


def _allowed_next_states(
    current: PluginLifecycleState,
) -> frozenset[PluginLifecycleState]:
    """ADR-006 SS8's exact canonical transition table, encoded as a local
    (not module-level) mapping so no ambient module state exists.
    """
    table: dict[PluginLifecycleState, frozenset[PluginLifecycleState]] = {
        PluginLifecycleState.DISCOVERED: frozenset(
            {PluginLifecycleState.VALIDATED, PluginLifecycleState.RETIRED}
        ),
        PluginLifecycleState.VALIDATED: frozenset(
            {
                PluginLifecycleState.INITIALIZED,
                PluginLifecycleState.FAILED,
                PluginLifecycleState.STOPPED,
                PluginLifecycleState.RETIRED,
            }
        ),
        PluginLifecycleState.INITIALIZED: frozenset(
            {
                PluginLifecycleState.ACTIVE,
                PluginLifecycleState.FAILED,
                PluginLifecycleState.STOPPED,
            }
        ),
        PluginLifecycleState.ACTIVE: frozenset(
            {
                PluginLifecycleState.DEGRADED,
                PluginLifecycleState.STOPPING,
                PluginLifecycleState.FAILED,
            }
        ),
        PluginLifecycleState.DEGRADED: frozenset(
            {
                PluginLifecycleState.ACTIVE,
                PluginLifecycleState.STOPPING,
                PluginLifecycleState.FAILED,
            }
        ),
        PluginLifecycleState.STOPPING: frozenset(
            {PluginLifecycleState.STOPPED, PluginLifecycleState.FAILED}
        ),
        PluginLifecycleState.FAILED: frozenset({PluginLifecycleState.STOPPING}),
        PluginLifecycleState.STOPPED: frozenset({PluginLifecycleState.RETIRED}),
        PluginLifecycleState.RETIRED: frozenset(),
    }
    return table[current]


def _transition(
    record: PluginLifecycleRecord,
    target: PluginLifecycleState,
    *,
    established_at: datetime,
) -> PluginLifecycleRecord:
    if type(record) is not PluginLifecycleRecord:
        raise TypeError("transition requires PluginLifecycleRecord")
    if target not in _allowed_next_states(record.state):
        raise LifecycleTransitionError(
            f"{record.state.value} cannot transition to {target.value}"
        )
    return replace(
        record,
        state=target,
        revision=record.revision + 1,
        established_at=established_at,
    )


def initialize(
    record: PluginLifecycleRecord, *, established_at: datetime
) -> PluginLifecycleRecord:
    """`initialize_plugin` (ADR-006 SS8): requires an already-`validated`
    record and already-admitted usable dependencies (not modeled in this
    batch); commits `initialized` or the caller instead calls `mark_failed`.
    """
    return _transition(
        record, PluginLifecycleState.INITIALIZED, established_at=established_at
    )


def activate(
    record: PluginLifecycleRecord, *, established_at: datetime
) -> PluginLifecycleRecord:
    """`activate_plugin` (ADR-006 SS8): permitted from `initialized` or a
    recovering `degraded` record. Never itself Catalog publication (ADR-006
    SS9: "Lifecycle owns activation ... Catalog owns registration").
    """
    return _transition(
        record, PluginLifecycleState.ACTIVE, established_at=established_at
    )


def degrade(
    record: PluginLifecycleRecord, *, established_at: datetime
) -> PluginLifecycleRecord:
    return _transition(
        record, PluginLifecycleState.DEGRADED, established_at=established_at
    )


def begin_stopping(
    record: PluginLifecycleRecord, *, established_at: datetime
) -> PluginLifecycleRecord:
    return _transition(
        record, PluginLifecycleState.STOPPING, established_at=established_at
    )


def stop(
    record: PluginLifecycleRecord, *, established_at: datetime
) -> PluginLifecycleRecord:
    return _transition(
        record, PluginLifecycleState.STOPPED, established_at=established_at
    )


def retire(
    record: PluginLifecycleRecord, *, established_at: datetime
) -> PluginLifecycleRecord:
    return _transition(
        record, PluginLifecycleState.RETIRED, established_at=established_at
    )


def mark_failed(
    record: PluginLifecycleRecord, *, established_at: datetime
) -> PluginLifecycleRecord:
    """Explicit failure transition, permitted from every non-terminal state
    the table allows (ADR-006 SS8). Failure never silently retains an
    active/initialized appearance (task SS27/SS43).
    """
    return _transition(
        record, PluginLifecycleState.FAILED, established_at=established_at
    )
