"""Pinned source-duty requirements; claimed inputs, not authority or custody."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from legoai.kernel.identity import _validate
from legoai.kernel.references import ReferenceScope
from legoai.kernel.versions import Version


def _utc(value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is not UTC:
        raise TypeError("time requires an explicit UTC datetime")


@dataclass(frozen=True, slots=True)
class RequirementRef:
    scope: ReferenceScope
    identity: str = field(repr=False)
    version: Version

    def __post_init__(self) -> None:
        if type(self.scope) is not ReferenceScope or type(self.version) is not Version:
            raise TypeError("requirement requires scope and Version")
        _validate(self.identity)


@dataclass(frozen=True, slots=True)
class GuaranteeRef:
    scope: ReferenceScope
    identity: str = field(repr=False)
    version: Version

    def __post_init__(self) -> None:
        if type(self.scope) is not ReferenceScope or type(self.version) is not Version:
            raise TypeError("guarantee requires scope and Version")
        _validate(self.identity)


@dataclass(frozen=True, slots=True)
class SourceRequirement:
    """Post-commit requirement, pinned guarantee and explicit UTC time bounds.

    Guarantee interpretation is supplied by the entitled requirement owner;
    no default TTL, custody strength or pre-effect exemption is invented here.
    """

    requirement: RequirementRef
    guarantee: GuaranteeRef
    due_at: datetime
    retain_until: datetime

    def __post_init__(self) -> None:
        if (
            type(self.requirement) is not RequirementRef
            or type(self.guarantee) is not GuaranteeRef
        ):
            raise TypeError("source requirement requires pinned references")
        if self.requirement.scope.tenant_id != self.guarantee.scope.tenant_id:
            raise ValueError("requirement/guarantee tenant mismatch")
        _utc(self.due_at)
        _utc(self.retain_until)
        if self.retain_until < self.due_at:
            raise ValueError("retention cannot end before deadline")
