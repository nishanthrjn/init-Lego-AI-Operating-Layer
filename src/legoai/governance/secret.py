"""Safe Secret source attribution values; construction grants no authority.

Exact Stage-A references and durable attribution; no material or provider API.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from legoai.governance.values import ApprovalId, GrantId, PolicyRef, Principal
from legoai.kernel.identity import OperationId, RequestId, _validate
from legoai.kernel.references import ConfigurationRevisionRef, ReferenceScope
from legoai.kernel.versions import Version


def _time(value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("aware datetime required")


@dataclass(frozen=True, slots=True)
class SecretUseId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class SecretRevisionRef:
    scope: ReferenceScope
    identity: str = field(repr=False)
    revision: str = field(repr=False)
    mapping_revision: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.scope) is not ReferenceScope:
            raise TypeError("Secret scope required")
        for value in (self.identity, self.revision, self.mapping_revision):
            _validate(value)


@dataclass(frozen=True, slots=True)
class SecretRef:
    """Exact selection only. Opaque mapping identity is not a source locator.

    Class and use requirements are declarations, never permission. No alias,
    current selector, environment name or credential transport is interpreted.
    """

    exact: SecretRevisionRef
    secret_class: str = field(repr=False)
    use_requirement: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.exact) is not SecretRevisionRef:
            raise TypeError("exact Secret revision required")
        _validate(self.secret_class)
        _validate(self.use_requirement)


@dataclass(frozen=True, slots=True)
class SecretUsePlan:
    """Exact prepared meaning. Authority references are historical, never grants.

    This local profile retains no delegated, remote or provider effect semantics.
    Time bounds are required and never defaulted; local commit has no realtime SLA.
    """

    use_id: SecretUseId
    operation_id: OperationId
    secret: SecretRevisionRef
    requester: Principal
    actor: Principal
    configuration: ConfigurationRevisionRef
    purpose: str = field(repr=False)
    consumer: str = field(repr=False)
    consumer_version: Version
    target_mapping: str = field(repr=False)
    grant_id: GrantId
    policy: PolicyRef
    approval_id: ApprovalId | None
    duty_id: str = field(repr=False)
    pre_submission: RequestId
    post_submission: RequestId
    prepared_at: datetime
    expires_at: datetime
    retain_until: datetime

    def __post_init__(self) -> None:
        for value, kind in (
            (self.use_id, SecretUseId),
            (self.operation_id, OperationId),
            (self.secret, SecretRevisionRef),
            (self.requester, Principal),
            (self.actor, Principal),
            (self.configuration, ConfigurationRevisionRef),
            (self.consumer_version, Version),
            (self.grant_id, GrantId),
            (self.policy, PolicyRef),
            (self.pre_submission, RequestId),
            (self.post_submission, RequestId),
        ):
            if type(value) is not kind:
                raise TypeError("invalid Secret use field type")
        if self.approval_id is not None and type(self.approval_id) is not ApprovalId:
            raise TypeError("invalid Approval reference")
        for text in (self.purpose, self.consumer, self.target_mapping, self.duty_id):
            _validate(text)
        for instant in (self.prepared_at, self.expires_at, self.retain_until):
            _time(instant)
        if not self.prepared_at < self.expires_at < self.retain_until:
            raise ValueError("invalid use/retention interval")
        if self.pre_submission == self.post_submission:
            raise ValueError("distinct submission identities required")
        if (
            self.secret.scope.tenant_id
            != self.configuration.configuration.application.scope.tenant_id
        ):
            raise ValueError("use tenant mismatch")


class SourceEvent(Enum):
    PREPARED = "prepared"
    ACCEPTED = "accepted"


@dataclass(frozen=True, slots=True)
class SecretUseFact:
    plan: SecretUsePlan
    event: SourceEvent
    occurred_at: datetime

    def __post_init__(self) -> None:
        if type(self.plan) is not SecretUsePlan or type(self.event) is not SourceEvent:
            raise TypeError("invalid source fact")
        _time(self.occurred_at)
        if self.event is SourceEvent.PREPARED:
            if self.occurred_at != self.plan.prepared_at:
                raise ValueError("prepared time mismatch")
        elif not self.plan.prepared_at <= self.occurred_at < self.plan.expires_at:
            raise ValueError("acceptance outside declared interval")

    @property
    def revision(self) -> int:
        return 1 if self.event is SourceEvent.PREPARED else 2

    @property
    def submission(self) -> RequestId:
        return (
            self.plan.pre_submission
            if self.event is SourceEvent.PREPARED
            else self.plan.post_submission
        )


class SourceDutyState(Enum):
    PENDING = "pending"
    SATISFIED = "satisfied"
    REQUIRES_INTERVENTION = "requires_intervention"


class UseRecoveryCategory(Enum):
    PREPARED_ONLY = "prepared_only"
    ACCEPTED_ATTRIBUTION_OUTSTANDING = "accepted_attribution_outstanding"
    ACCEPTED_ATTRIBUTED = "accepted_attributed"
    RECONCILED_REQUIRES_INTERVENTION = "reconciled_requires_intervention"
    UNKNOWN_GAP = "unknown_gap"


class ApprovalObservation(Enum):
    NOT_APPLICABLE = "not_applicable"
    POSSIBLY_CONSUMED = "possibly_consumed"
    CONSUMED = "consumed"


@dataclass(frozen=True, slots=True)
class SecretUseStatus:
    """Safe inspection projection, never a replayable use result."""

    use_id: SecretUseId
    category: UseRecoveryCategory
    duty: SourceDutyState
    revision: int
    approval: ApprovalObservation
    accepted_fact: SecretUseFact | None

    def __post_init__(self) -> None:
        if (
            type(self.use_id) is not SecretUseId
            or type(self.category) is not UseRecoveryCategory
        ):
            raise TypeError("invalid status identity/category")
        if (
            type(self.duty) is not SourceDutyState
            or type(self.approval) is not ApprovalObservation
        ):
            raise TypeError("invalid duty/approval observation")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("invalid source revision")
        if self.accepted_fact is not None and (
            type(self.accepted_fact) is not SecretUseFact
            or self.accepted_fact.event is not SourceEvent.ACCEPTED
            or self.accepted_fact.plan.use_id != self.use_id
        ):
            raise ValueError("invalid retained acceptance fact")
