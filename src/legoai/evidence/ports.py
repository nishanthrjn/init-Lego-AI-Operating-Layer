"""Gate-2 M8: Evidence custody Port and its operation request/result values
(ADR-009; ADR-002's `legoai.evidence` "Audit custody, required evidence
availability and general provenance contracts" row).

Critical distinctions preserved throughout:

    Evidence != Observation != log != trace != model explanation
    != private chain-of-thought
    EvidenceRequirement (F4, `legoai.evidence.values`, unchanged by this
    batch) != EvidenceRecord (this module) -- a requirement's mere
    existence is never proof a record exists.
    Evidence != canonical Outcome -- a record may support a claim about an
    Outcome without being that Outcome.

F8a's `Observation` (`legoai.observability`) is best-effort, non-
authoritative, bounded diagnostic telemetry; it is never reused as Evidence
storage here, and this module does not import it. `EvidenceRecord` is the
opposite: an authoritative, retained, attributable fact that custody
explicitly commits through `EvidenceCustodyPort.record`. Construction of an
`EvidenceRecord` value never writes it -- custody occurs only through an
explicit Port call (task SS65).

`subject` is a deliberately narrow, explicit union of the two evidence
subject types this batch has a genuine consumer for -- not a placeholder
for "any future subject":

  - `ConfigurationRevisionRef` (Kernel) -- satisfies F4's existing
    `EvidenceRequirement.subject` shape.
  - `AuthorizationDecision` (M4, `legoai.governance.ports`) -- historical
    evidence that an authorization was evaluated. Recording this evidence
    **never** authorizes future work: ADR-007 SS12.1 still requires current
    revalidation regardless of any retained historical decision, and this
    module records that decision without re-deriving, mutating, or
    recomputing it.

No callable, open file, DB connection, logger, or Plugin/provider instance
is representable in any value here. No hidden reasoning, model chain-of-
thought, or private scratchpad field exists or is ever required -- if a
later AI-producing system must supply evidence, only its already-visible
output/reference is retained.

This module deliberately imports `legoai.governance.values` and
`legoai.governance.ports` (ADR-002 SS9.2's O-row allowed-foreign-target
list includes G; Gate-2 M6's `capabilities.ports -> plugins.ports` widening
is the direct precedent for a Port module embedding a foreign owner's
Port-level operation-result value). `legoai.evidence.values` itself is
untouched and remains Kernel-only.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from legoai.governance.ports import AuthorizationDecision
from legoai.governance.values import Principal
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import _validate
from legoai.kernel.references import ConfigurationRevisionRef


class EvidenceConflictError(ValueError):
    """The same `EvidenceId` was submitted with materially different
    content. Mirrors `LifecycleTransitionError`/`CatalogPublicationError`'s
    role: a caller precondition violation, never a silent overwrite
    (ADR-009's append-only custody discipline). An exact equivalent
    resubmission is not a conflict -- see the reference realization's
    idempotent-replay behavior.
    """


@dataclass(frozen=True, slots=True)
class EvidenceId:
    """Opaque Evidence custody identity; distinct from `OperationId`,
    `ExecutionId`, `DutyId` and `ArtifactId` -- none of those identify one
    committed evidence record. Construction commits nothing.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """Immutable, attributable evidence actually retained (contrast
    `EvidenceRequirement`, which only describes what must eventually
    exist). `content_reference` is a bounded inert reference/description --
    never a raw secret, credential, or unbounded payload -- mirroring
    `EvidenceRequirement.description`'s own shape exactly. `issuer`
    attributes who/what produced this evidence (CONTRACTS
    `record_audit_evidence`: "issuer/source").

    Construction cross-checks that `tenant_context` matches the tenant
    implied by `subject`, so a record can never be attributed to a tenant
    other than the one its own subject actually belongs to.
    """

    evidence_id: EvidenceId
    subject: ConfigurationRevisionRef | AuthorizationDecision
    issuer: Principal
    tenant_context: TenantContext
    content_reference: str = field(repr=False)
    recorded_at: datetime

    def __post_init__(self) -> None:
        if type(self.evidence_id) is not EvidenceId:
            raise TypeError("evidence record requires EvidenceId")
        if type(self.subject) is ConfigurationRevisionRef:
            subject_tenant = self.subject.configuration.application.scope.tenant_id
        elif type(self.subject) is AuthorizationDecision:
            subject_tenant = self.subject.operation.scope.tenant_id
        else:
            raise TypeError(
                "evidence record subject must be ConfigurationRevisionRef "
                "or AuthorizationDecision"
            )
        if type(self.issuer) is not Principal:
            raise TypeError("evidence record requires Principal issuer")
        if type(self.tenant_context) is not TenantContext:
            raise TypeError("evidence record requires TenantContext")
        if subject_tenant != self.tenant_context.tenant_id:
            raise ValueError("evidence record subject tenant mismatch")
        _validate(self.content_reference)
        if type(self.recorded_at) is not datetime:
            raise TypeError("evidence record recorded_at must be datetime")
        if self.recorded_at.tzinfo is None:
            raise ValueError("evidence record recorded_at must be timezone-aware")


class EvidenceCustodyPort(Protocol):
    """The Evidence owner's exact custody operations. Append-only: no
    `update`/`patch`/`replace`/`delete` exists, matching ADR-009's custody
    discipline. Exact-ID lookup only -- no "latest"/"nearest"/"similar"
    substitution.
    """

    def record(self, record: EvidenceRecord) -> EvidenceRecord: ...

    def read(
        self, evidence_id: EvidenceId, tenant_context: TenantContext
    ) -> EvidenceRecord | None: ...
