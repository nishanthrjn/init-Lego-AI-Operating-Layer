"""Pinned requirement/guarantee inputs for source submission duties.

References identify externally defined meaning; possession proves neither its
authority nor satisfaction. No Evidence record, receipt or custody service.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from legoai.kernel.identity import _validate
from legoai.kernel.references import ReferenceScope
from legoai.kernel.versions import Version


def _utc(value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise TypeError("time must be an explicit UTC datetime")


@dataclass(frozen=True, slots=True)
class RequirementRef:
    scope: ReferenceScope
    identity: str = field(repr=False)
    version: Version

    def __post_init__(self) -> None:
        if type(self.scope) is not ReferenceScope or type(self.version) is not Version:
            raise TypeError("requirement requires scope and version")
        _validate(self.identity)


@dataclass(frozen=True, slots=True)
class GuaranteeRef:
    scope: ReferenceScope
    identity: str = field(repr=False)
    version: Version

    def __post_init__(self) -> None:
        if type(self.scope) is not ReferenceScope or type(self.version) is not Version:
            raise TypeError("guarantee requires scope and version")
        _validate(self.identity)


@dataclass(frozen=True, slots=True)
class SourceRequirement:
    """Post-commit requirement with explicit UTC due/retention bounds.

    Guarantee reference pins the required custody/recovery meaning. These
    supplied requirements are not endorsements and cannot replace pre-effect
    custody. No clock is read and no default retention policy is invented.
    """

    requirement: RequirementRef
    guarantee: GuaranteeRef
    due_at: datetime
    retain_until: datetime

    def __post_init__(self) -> None:
        if type(self.requirement) is not RequirementRef or type(self.guarantee) is not GuaranteeRef:
            raise TypeError("source requirement requires pinned references")
        if self.requirement.scope.tenant_id != self.guarantee.scope.tenant_id:
            raise ValueError("requirement and guarantee tenant mismatch")
        _utc(self.due_at)
        _utc(self.retain_until)
        if self.retain_until < self.due_at:
            raise ValueError("retention ends before duty deadline")
