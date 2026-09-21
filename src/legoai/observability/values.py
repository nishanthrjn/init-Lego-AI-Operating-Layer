"""F8a: bounded, allowlisted diagnostic observation value (CONTRACTS SS25;
Gate-1 plan SS6, SS11).

Observation is diagnostic only. It is never Evidence, never Provenance,
never an audit record, never an authorization fact, and never Conformance
proof (SS3 of the F8a task). Losing or never emitting an Observation must
never change semantic correctness: nothing in F0-F6b reads this value, or
its absence, to decide whether an operation committed, whether
authorization existed, whether an effect completed, whether Evidence
exists, or whether F6b's ``qualify_store`` result should be trusted. This
module has no consumer relationship with ``legoai.reference.application``
at all -- it does not import it, and nothing there imports this.

Field set is exactly the Gate-1 plan's own enumerated allowlist (SS11):
"record schema version, safe event code, owner/module, trace/correlation/
causation, operation/request refs, approved tenant-safe identity token,
configuration revision, ... stage/transition observation, canonical error
category and safe cause ref, latency and bounded size/usage observations."
There is no open attributes bag and no arbitrary payload field: the plan's
list is closed and enumerated, not "attributes plus whatever." Adding a
free-form ``dict[str, Any]`` here would be exactly the "general-purpose
arbitrary logging payload" the task instructs against. Plugin/Provider/
Adapter version and Execution/authorization-decision fields are omitted
entirely -- those types do not exist yet (F7/Gate-2), and the plan's own
rule is to include such fields "when real, not fake placeholders for the
inert harness." "Stage/transition observation" is expressed through
``event_code`` rather than a duplicate field, since no accepted document
defines a separate closed stage vocabulary.

No field accepts Secrets, credentials, raw payload/document/prompt content,
or personal data. Only opaque safe references (existing Kernel identity/
reference types) and small bounded diagnostic scalars are representable at
all -- there is no field wide enough to hold such content by construction,
not merely by caller discipline.
"""

from dataclasses import dataclass, field
from math import isfinite

from legoai.kernel.errors import ErrorCategory
from legoai.kernel.identity import CorrelationId, TenantId, TraceId, _validate
from legoai.kernel.references import ConfigurationRevisionRef, OperationRef


@dataclass(frozen=True, slots=True)
class ObservationEventCode:
    """Open, owner-declared diagnostic event code.

    Deliberately not a closed enum: no accepted document enumerates a fixed
    diagnostic-event vocabulary, mirroring ``DutyKind``'s own rationale
    (``legoai.kernel.provenance``) -- future owners must be able to declare
    new diagnostic events without a Kernel or Observability code change.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class Observation:
    """One bounded diagnostic fact. Never authoritative state (see module
    docstring). A ``None`` field is a real "not applicable to this
    observation" fact, never an omitted-by-mistake placeholder the caller
    should have filled with invented content.
    """

    schema_version: int
    event_code: ObservationEventCode
    owner: str = field(repr=False)
    correlation_id: CorrelationId | None = None
    trace_id: TraceId | None = None
    causation: OperationRef | None = None
    operation: OperationRef | None = None
    tenant_id: TenantId | None = None
    configuration_revision: ConfigurationRevisionRef | None = None
    error_category: ErrorCategory | None = None
    safe_cause_reference: str | None = field(default=None, repr=False)
    latency_ms: float | None = None
    size_bytes: int | None = None

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int:
            raise TypeError("observation requires an integer schema_version")
        if self.schema_version != 1:
            raise ValueError("unsupported observation schema_version")
        if type(self.event_code) is not ObservationEventCode:
            raise TypeError("observation requires ObservationEventCode")
        _validate(self.owner)
        if (
            self.correlation_id is not None
            and type(self.correlation_id) is not CorrelationId
        ):
            raise TypeError("correlation_id must be CorrelationId or None")
        if self.trace_id is not None and type(self.trace_id) is not TraceId:
            raise TypeError("trace_id must be TraceId or None")
        if self.causation is not None and type(self.causation) is not OperationRef:
            raise TypeError("causation must be OperationRef or None")
        if self.operation is not None and type(self.operation) is not OperationRef:
            raise TypeError("operation must be OperationRef or None")
        if self.tenant_id is not None and type(self.tenant_id) is not TenantId:
            raise TypeError("tenant_id must be TenantId or None")
        if (
            self.configuration_revision is not None
            and type(self.configuration_revision) is not ConfigurationRevisionRef
        ):
            raise TypeError(
                "configuration_revision must be ConfigurationRevisionRef or None"
            )
        if (
            self.error_category is not None
            and type(self.error_category) is not ErrorCategory
        ):
            raise TypeError("error_category must be ErrorCategory or None")
        if self.safe_cause_reference is not None:
            _validate(self.safe_cause_reference)
            if self.error_category is None:
                raise ValueError("safe_cause_reference requires an error_category")
        if self.latency_ms is not None:
            if type(self.latency_ms) is not float:
                raise TypeError("latency_ms must be a float or None")
            if not isfinite(self.latency_ms):
                raise ValueError("latency_ms must be finite")
            if self.latency_ms < 0:
                raise ValueError("latency_ms must be non-negative")
        if self.size_bytes is not None:
            if type(self.size_bytes) is not int:
                raise TypeError("size_bytes must be an integer or None")
            if self.size_bytes < 0:
                raise ValueError("size_bytes must be non-negative")
