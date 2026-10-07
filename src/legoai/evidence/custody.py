"""Additive acknowledged source custody; legacy record/read stay unchanged.

Receipts describe a qualified intact-local-storage profile, not authority or a
power-loss/hostile-storage guarantee. Source acceptance remains Secret-owned.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol

from legoai.governance.secret import SecretUseFact, _time
from legoai.governance.values import Principal
from legoai.kernel.identity import RequestId, _validate
from legoai.kernel.references import ReferenceScope


class CustodyProfile(Enum):
    INTACT_LOCAL_V1 = "intact_local_crash_restart_v1"


@dataclass(frozen=True, slots=True)
class CustodyAccess:
    """Scoped input, not authentication. Trusted composition establishes access."""

    scope: ReferenceScope
    requester: Principal

    def __post_init__(self) -> None:
        if (
            type(self.scope) is not ReferenceScope
            or type(self.requester) is not Principal
        ):
            raise TypeError("explicit custody scope required")


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    fact: SecretUseFact
    issuer: Principal
    profile: CustodyProfile

    def __post_init__(self) -> None:
        if type(self.fact) is not SecretUseFact or type(self.issuer) is not Principal:
            raise TypeError("invalid source evidence")
        if type(self.profile) is not CustodyProfile:
            raise TypeError("explicit custody profile required")
        if self.issuer != self.fact.plan.actor:
            raise ValueError("source issuer mismatch")


@dataclass(frozen=True, slots=True)
class DurableCustodyReceipt:
    """Exact retained outcome; constructing a value does not establish custody."""

    identity: str = field(repr=False)
    custodian: str = field(repr=False)
    evidence: SourceEvidence
    committed_at: datetime

    def __post_init__(self) -> None:
        _validate(self.identity)
        _validate(self.custodian)
        if type(self.evidence) is not SourceEvidence:
            raise TypeError("receipt requires evidence")
        _time(self.committed_at)
        if (
            not self.evidence.fact.occurred_at
            <= self.committed_at
            < self.evidence.fact.plan.retain_until
        ):
            raise ValueError("receipt outside declared coverage")


class AcknowledgedEvidenceCustodyPort(Protocol):
    """Additional custody profile; no retroactive promise for legacy callers.

    INTACT_LOCAL_V1: schema/version and SQLite integrity checks, scope-controlled
    reads, exact source revision/event class, retention through retain_until,
    no automatic deletion, and no hostile-admin/rollback/power-loss guarantee.
    Current authenticated admission must be established by trusted composition.
    """

    def acknowledge(
        self, evidence: SourceEvidence, access: CustodyAccess, *, recorded_at: datetime
    ) -> DurableCustodyReceipt: ...

    def submission_status(
        self, submission: RequestId, access: CustodyAccess
    ) -> DurableCustodyReceipt | None: ...
