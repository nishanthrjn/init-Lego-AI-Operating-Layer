"""F2's closed normalization configuration fixture, not a configuration language.

Strings identifying sources use F1's 1-256 code-point bound. Input size is in
Unicode code points, bounded locally to 1-65536. Whitespace is an ordered tuple
of at most six distinct ASCII whitespace characters; empty means recognize no
whitespace. No Unicode normalization or non-ASCII transformation is implied.
"""

from dataclasses import dataclass, field
from enum import Enum

from legoai.evidence.values import EvidenceRequirement
from legoai.governance.values import Principal
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorDetail
from legoai.kernel.identity import _validate
from legoai.kernel.provenance import DutyId, DutyKind
from legoai.kernel.references import (
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    OwnerRevision,
)
from legoai.kernel.versions import Version


class SourceLayer(Enum):
    DEFAULTS = "defaults"
    BASE = "base"
    TENANT_OVERRIDE = "tenant override"


class NormalizationMode(Enum):
    """Future fixture behavior: trim edges or also collapse runs to ASCII space.

    F2 only represents these settings; it does not execute normalization.
    Non-ASCII characters are always preserved by this fixture contract.
    """

    TRIM = "trim"
    COLLAPSE = "collapse"


def _versions(contract: Version, interpretation: Version) -> None:
    if type(contract) is not Version or type(interpretation) is not Version:
        raise TypeError("configuration versions must be Version values")
    if contract != Version(0, 1, 0) or interpretation != Version(0, 1, 0):
        raise ValueError("unsupported normalization contract or interpretation version")


def _maximum(value: int) -> None:
    if type(value) is not int:
        raise TypeError("maximum input length must be an integer")
    if not 1 <= value <= 65536:
        raise ValueError("maximum input length must be within 1-65536 code points")


def _whitespace(value: tuple[str, ...]) -> None:
    if type(value) is not tuple:
        raise TypeError("whitespace must be an immutable tuple")
    if len(value) > 6:
        raise ValueError("whitespace collection exceeds six characters")
    for character in value:
        if type(character) is not str:
            raise TypeError("whitespace elements must be text")
        if len(character) != 1 or character not in " \t\n\r\v\f":
            raise ValueError("unsupported whitespace character")
    if len(set(value)) != len(value):
        raise ValueError("duplicate whitespace character")


@dataclass(frozen=True, slots=True)
class SourceProvenance:
    """Claimed source attribution, neither verified provenance nor custody."""

    owner: str = field(repr=False)
    source_id: str = field(repr=False)
    source_revision: str = field(repr=False)
    contract_version: Version
    interpretation_version: Version

    def __post_init__(self) -> None:
        _validate(self.owner)
        _validate(self.source_id)
        _validate(self.source_revision)
        _versions(self.contract_version, self.interpretation_version)


@dataclass(frozen=True, slots=True)
class NormalizationPatch:
    """Internal captured fields. None denotes missing, never explicit input null.

    The capture boundary rejects supplied null before constructing this record.
    A supplied empty tuple is distinct from a missing whitespace field.
    """

    max_input_length: int | None = None
    normalization_mode: NormalizationMode | None = None
    allowed_whitespace: tuple[str, ...] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.max_input_length is not None:
            _maximum(self.max_input_length)
        if (
            self.normalization_mode is not None
            and type(self.normalization_mode) is not NormalizationMode
        ):
            raise TypeError("normalization mode must be NormalizationMode")
        if self.allowed_whitespace is not None:
            _whitespace(self.allowed_whitespace)


@dataclass(frozen=True, slots=True)
class CapturedCandidate:
    target: ConfigurationRef
    provenance: SourceProvenance
    layer: SourceLayer
    values: NormalizationPatch

    def __post_init__(self) -> None:
        if type(self.target) is not ConfigurationRef:
            raise TypeError("candidate requires ConfigurationRef")
        if type(self.provenance) is not SourceProvenance:
            raise TypeError("candidate requires SourceProvenance")
        if type(self.layer) is not SourceLayer:
            raise TypeError("candidate requires SourceLayer")
        if type(self.values) is not NormalizationPatch:
            raise TypeError("candidate requires immutable NormalizationPatch")
        if (
            self.layer is SourceLayer.TENANT_OVERRIDE
            and self.values.max_input_length is not None
        ):
            raise ValueError(
                "tenant layer cannot replace protected maximum input length"
            )


@dataclass(frozen=True, slots=True)
class EffectiveConfiguration:
    """Fully materialized semantic value; source identities are a separate axis.

    Equality includes interpretation versions and ordered fixture field values,
    not source provenance, capture time, target scope or object identity.
    """

    contract_version: Version
    interpretation_version: Version
    max_input_length: int
    normalization_mode: NormalizationMode
    allowed_whitespace: tuple[str, ...] = field(repr=False)

    def __post_init__(self) -> None:
        _versions(self.contract_version, self.interpretation_version)
        _maximum(self.max_input_length)
        if type(self.normalization_mode) is not NormalizationMode:
            raise TypeError("effective normalization mode must be NormalizationMode")
        _whitespace(self.allowed_whitespace)


@dataclass(frozen=True, slots=True)
class ComposedConfiguration:
    """Unpublished candidate plus retained capture inputs in semantic layer order.

    This is not a publication receipt. Equality of this full record includes
    target/provenance; compare .effective for semantic configuration equality.
    """

    target: ConfigurationRef
    effective: EffectiveConfiguration
    sources: tuple[CapturedCandidate, ...]

    def __post_init__(self) -> None:
        if (
            type(self.target) is not ConfigurationRef
            or type(self.effective) is not EffectiveConfiguration
        ):
            raise TypeError(
                "composition requires typed target and effective configuration"
            )
        if type(self.sources) is not tuple:
            raise TypeError("composition sources must be an immutable captured tuple")
        if not 1 <= len(self.sources) <= 3:
            raise ValueError("composition requires one to three source records")
        if any(type(source) is not CapturedCandidate for source in self.sources):
            raise TypeError("composition sources must contain CapturedCandidate")
        layers = tuple(source.layer for source in self.sources)
        if layers not in (
            (SourceLayer.DEFAULTS,),
            (SourceLayer.DEFAULTS, SourceLayer.BASE),
            (SourceLayer.DEFAULTS, SourceLayer.TENANT_OVERRIDE),
            (SourceLayer.DEFAULTS, SourceLayer.BASE, SourceLayer.TENANT_OVERRIDE),
        ):
            raise ValueError("composition requires defaults and unique ordered layers")
        for source in self.sources:
            if source.target != self.target:
                raise ValueError("composition source scope mismatch")


class OperationStage(Enum):
    """ADR-004/008 retained outcome of one configuration-publication attempt.

    Exactly these two members: a stale/conflicting/invalid attempt is
    REJECTED with an attached ErrorDetail, never silently coerced into a
    partial commit. There is no third "replayed" stage -- resubmitting an
    already-committed operation returns its original COMMITTED result
    unchanged (SS "operation result recovery" below), it does not mint a new
    stage value.
    """

    COMMITTED = "committed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ConfigurationPublicationOperation:
    """Descriptor of one requested configuration-publish operation (ADR-003/004/008).

    expected_revision=None is an explicit claim that no prior revision is
    expected to exist yet (first publish for this target) -- it is not an
    omitted field and must not be confused with "don't care". requested_by
    identifies who is accountable for the resulting duty (SS "duty" below);
    it is representation only and confers no authority (Gate-1 SS5.3).
    """

    operation: OperationRef
    target: ConfigurationRef
    expected_revision: OwnerRevision | None
    candidate: ComposedConfiguration
    requested_by: Principal

    def __post_init__(self) -> None:
        if type(self.operation) is not OperationRef:
            raise TypeError("publication operation requires OperationRef")
        if type(self.target) is not ConfigurationRef:
            raise TypeError("publication operation requires ConfigurationRef target")
        if type(self.operation.subject) is not ConfigurationRef or (
            self.operation.subject != self.target
        ):
            raise ValueError("operation subject must match the publication target")
        if self.expected_revision is not None:
            if type(self.expected_revision) is not OwnerRevision:
                raise TypeError("expected revision must be OwnerRevision or explicit None")
            if self.expected_revision.subject != self.target:
                raise ValueError("expected revision subject mismatch")
        if type(self.candidate) is not ComposedConfiguration:
            raise TypeError("publication operation requires ComposedConfiguration candidate")
        if self.candidate.target != self.target:
            raise ValueError("candidate target mismatch")
        if type(self.requested_by) is not Principal:
            raise TypeError("publication operation requires a requesting Principal")


@dataclass(frozen=True, slots=True)
class ConfigurationPublicationResult:
    """Retained outcome of one configuration-publication operation (ADR-004 SS9, ADR-008).

    Recoverable by operation identity after a lost acknowledgment: the same
    operation, resubmitted, must yield this exact same result -- never a
    second commit, and never a failure solely because the head has since
    advanced. Committed and rejected results are mutually exclusive shapes:
    a committed result carries no error, and a rejected result carries no
    resulting revision, published reference, or duty.
    """

    operation: OperationRef
    stage: OperationStage
    resulting_revision: OwnerRevision | None
    published: ConfigurationRevisionRef | None
    effect: EffectExtent
    error: ErrorDetail | None
    duties: tuple[DutyId, ...]

    def __post_init__(self) -> None:
        if type(self.operation) is not OperationRef:
            raise TypeError("publication result requires OperationRef")
        if type(self.stage) is not OperationStage:
            raise TypeError("publication result requires OperationStage")
        if type(self.effect) is not EffectExtent:
            raise TypeError("publication result requires EffectExtent")
        if type(self.duties) is not tuple or any(
            type(duty) is not DutyId for duty in self.duties
        ):
            raise TypeError("duties must be an immutable tuple of DutyId")
        if self.stage is OperationStage.COMMITTED:
            if self.resulting_revision is None or self.published is None:
                raise ValueError(
                    "committed result requires a resulting revision and published reference"
                )
            if type(self.resulting_revision) is not OwnerRevision:
                raise TypeError("resulting revision must be OwnerRevision")
            if type(self.published) is not ConfigurationRevisionRef:
                raise TypeError("published reference must be ConfigurationRevisionRef")
            if self.published.configuration != self.resulting_revision.subject:
                raise ValueError("published reference and resulting revision subject mismatch")
            if self.error is not None:
                raise ValueError("committed result cannot carry an error")
        else:
            if self.resulting_revision is not None or self.published is not None:
                raise ValueError(
                    "rejected result cannot carry a resulting revision or published reference"
                )
            if self.error is None:
                raise ValueError("rejected result requires an ErrorDetail")
            if type(self.error) is not ErrorDetail:
                raise TypeError("result error must be ErrorDetail")
            if self.duties:
                raise ValueError("rejected result cannot carry duties")


@dataclass(frozen=True, slots=True)
class ConfigurationSourceSubmissionDuty:
    """One outstanding post-commit source-custody obligation for a published
    configuration revision (ADR-009, applied as narrowly as Gate-1 SS9.1
    describes). Recording this duty is not a custody receipt: it does not
    imply an Evidence owner accepted anything, and resolving it is explicitly
    deferred to later custody work (Gate-1 SS10.4) -- this value only makes
    the outstanding obligation discoverable and consistently described.
    """

    duty_id: DutyId
    kind: DutyKind
    operation: OperationRef
    published: ConfigurationRevisionRef
    responsible_principal: Principal
    tenant_context: TenantContext
    requirement: EvidenceRequirement

    def __post_init__(self) -> None:
        if type(self.duty_id) is not DutyId:
            raise TypeError("duty requires DutyId")
        if type(self.kind) is not DutyKind:
            raise TypeError("duty requires DutyKind")
        if type(self.operation) is not OperationRef:
            raise TypeError("duty requires OperationRef")
        if type(self.published) is not ConfigurationRevisionRef:
            raise TypeError("duty requires ConfigurationRevisionRef")
        if type(self.operation.subject) is not ConfigurationRef or (
            self.operation.subject != self.published.configuration
        ):
            raise ValueError("duty operation subject must match the published configuration")
        if type(self.responsible_principal) is not Principal:
            raise TypeError("duty requires a responsible Principal")
        if type(self.tenant_context) is not TenantContext:
            raise TypeError("duty requires TenantContext")
        if (
            self.tenant_context.tenant_id
            != self.published.configuration.application.scope.tenant_id
        ):
            raise ValueError("duty tenant context does not match published configuration scope")
        if type(self.requirement) is not EvidenceRequirement:
            raise TypeError("duty requires EvidenceRequirement")
        if self.requirement.subject != self.published:
            raise ValueError("duty requirement subject must match the published revision")
