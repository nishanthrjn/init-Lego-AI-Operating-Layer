"""Gate-2 M5: Plugin lifecycle/admission operation request/result values
(ADR-002 SS9's `ports.py` category: "operation request/result definitions").

No `PluginLifecyclePort`/`PluginAdmissionPort` Protocol is defined here: every
operation this batch implements (`legoai.reference.plugins`) is a pure,
side-effect-free transformation with no external dependency to seam behind a
Protocol -- unlike ADR-005's Governance current-authority facts (M4), a
lifecycle transition here needs no live external state, so a Port would be
an unused abstraction, not a real seam (mirroring F7's own pure
`reference.resolution`, which likewise has no accompanying Port).

Canonical distinctions preserved throughout (ADR-006 SS2, SS8):

    discovered != inspected != validated != admitted != configured
    != initialized != activated != catalog-published

`PluginDeclaration` (F7, `legoai.plugins.values`, untouched by this batch)
remains inert descriptive data. `PluginLifecycleRecord` is a *separate*
runtime/admission representation, never merged into or mutating the
declaration: ADR-006 SS4 states "`validate_plugin` returns findings while
`admit_plugin` alone commits `validated`, not activation" -- a validation
finding is not an admission, and an admission record is not a Catalog entry
or an executable binding. No callable, provider instance, adapter, or
runtime client field exists on any value in this module.

Trusted-host scope (ADR-012 remains Proposed): this batch assumes the
already-accepted Gate-1/Gate-2 trusted shared-process scope (ADR-005 SS4,
ADR-006 SS2) -- admission here is bookkeeping over an already-trusted
declaration, never process isolation or sandboxing, and never admits a
hostile or insufficiently trusted candidate. A batch that needs to admit an
untrusted contribution must stop and report ADR-012 as a blocker rather
than deciding isolation implicitly.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from legoai.kernel.context import TenantContext
from legoai.kernel.identity import _validate
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginId


class LifecycleTransitionError(ValueError):
    """An attempted transition is not permitted from the record's current
    state (ADR-006 SS8's exact canonical transition table). Not a Plugin
    failure category itself -- a caller precondition violation, mirroring
    `application.ports.UnknownRevisionError`'s role for F4.
    """


class PluginLifecycleState(Enum):
    """The exact canonical Plugin lifecycle states (ADR-006 SS8). No other
    state exists here, and no technical observation (queue entry, health
    ping, restart attempt) is ever added as a new canonical state.
    """

    DISCOVERED = "discovered"
    VALIDATED = "validated"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    FAILED = "failed"
    STOPPED = "stopped"
    RETIRED = "retired"


class ValidationOutcome(Enum):
    """`validate_plugin` "returns findings" (ADR-006 SS8) -- never itself an
    admission. This reference batch's only currently representable finding
    is exact discovery-to-declaration provenance binding (ADR-006 SS5:
    "verify the intended artifact/source association ... prevent
    substitution between inspected artifact and loaded code"); PLUGIN-SPEC's
    fuller compatibility/namespace/trust findings have no accepted typed
    representation yet and are not fabricated here.
    """

    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True, slots=True)
class PluginAdmissionId:
    """Opaque Plugin lifecycle-record identity; distinct from `PluginId`
    (identifies the Plugin release, not this admission attempt), `ExecutionId`
    and `OperationId` (a lifecycle record is neither an Execution attempt
    nor a logical operation). Construction admits nothing.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class DiscoveredPluginRef:
    """The unverified identity/release a discovery step claims for a
    candidate (ADR-006 SS8: `discover_plugin` "no code execution, trust,
    installation or eligibility implied"). This is a claim to verify during
    `validate`, not yet a trusted fact.
    """

    plugin_id: PluginId
    release: Version

    def __post_init__(self) -> None:
        if type(self.plugin_id) is not PluginId:
            raise TypeError("discovered plugin reference requires PluginId")
        if type(self.release) is not Version:
            raise TypeError("discovered plugin reference requires a release Version")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Immutable `validate_plugin` finding (ADR-006 SS8): "findings only",
    never itself validated/admitted state. See `ValidationOutcome`.
    """

    discovered: DiscoveredPluginRef
    outcome: ValidationOutcome
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if type(self.discovered) is not DiscoveredPluginRef:
            raise TypeError("validation result requires DiscoveredPluginRef")
        if type(self.outcome) is not ValidationOutcome:
            raise TypeError("validation result requires ValidationOutcome")
        if type(self.evaluated_at) is not datetime:
            raise TypeError("validation result evaluated_at must be datetime")
        if self.evaluated_at.tzinfo is None:
            raise ValueError("validation result evaluated_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class PluginLifecycleRecord:
    """Immutable Plugin lifecycle/admission record -- a runtime/admission
    representation *separate* from `PluginDeclaration` (ADR-002 SS9.2's
    reference-realization split; task SS4). References the Plugin by
    `plugin_id`/`release` rather than embedding the full declaration, the
    same "reference, not a copy" discipline already used by
    `AuthorizationDecision.considered_grant` (M4).

    `revision` is a per-transition attribution counter, not an ADR-004
    expected-revision concurrency guard: this reference realization is a
    pure in-memory transformation with no concurrent writers to guard
    against; a persisted Lifecycle store (a later batch) would add that
    guard against its own storage, not against this value's shape.

    Presence of this record with `state=ACTIVE` is never itself Catalog
    visibility (ADR-006 SS9: "Lifecycle owns activation ... Catalog owns
    registration, visibility") and never itself dispatch authority.
    """

    admission_id: PluginAdmissionId
    plugin_id: PluginId
    release: Version
    tenant_context: TenantContext
    state: PluginLifecycleState
    revision: int
    established_at: datetime

    def __post_init__(self) -> None:
        if type(self.admission_id) is not PluginAdmissionId:
            raise TypeError("lifecycle record requires PluginAdmissionId")
        if type(self.plugin_id) is not PluginId:
            raise TypeError("lifecycle record requires PluginId")
        if type(self.release) is not Version:
            raise TypeError("lifecycle record requires a release Version")
        if type(self.tenant_context) is not TenantContext:
            raise TypeError("lifecycle record requires TenantContext")
        if type(self.state) is not PluginLifecycleState:
            raise TypeError("lifecycle record requires PluginLifecycleState")
        if type(self.revision) is not int or isinstance(self.revision, bool):
            raise TypeError("lifecycle record revision must be an int")
        if self.revision < 1:
            raise ValueError("lifecycle record revision must be positive")
        if type(self.established_at) is not datetime:
            raise TypeError("lifecycle record established_at must be datetime")
        if self.established_at.tzinfo is None:
            raise ValueError("lifecycle record established_at must be timezone-aware")
