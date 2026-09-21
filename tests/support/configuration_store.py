"""In-memory test fake for legoai.application.ports.ConfigurationStorePort.

Test infrastructure only -- never a production reference persistence
realization (Gate-1 plan SS9.1: "Put it in tests/support, never ship it as a
runtime fallback"). Proves the Protocol's contract cheaply and
deterministically; a future F6a SQLite realization must independently
demonstrate the same contract-test vectors (see tests/contract/), not merely
match this fake's internal structure.

Atomicity note: each mutating call below builds every new record locally and
assigns them into this object's dictionaries only in a final, uninterrupted
block. This models "all owner-local records become visible together, or none
do" structurally (single-threaded, no suspension point between the checks and
the assignments) -- it does NOT prove SQLite (or any real backend's)
transactional atomicity, which F6a must qualify independently (ADR-004 SS15).
"""

from __future__ import annotations

from itertools import count

from legoai.application.ports import UnknownRevisionError
from legoai.application.values import (
    ComposedConfiguration,
    ConfigurationPublicationOperation,
    ConfigurationPublicationResult,
    ConfigurationSourceSubmissionDuty,
    OperationStage,
)
from legoai.evidence.values import EvidenceRequirement
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorCause, ErrorDetail, Recoverability
from legoai.kernel.provenance import DutyId, DutyKind
from legoai.kernel.references import (
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    OwnerRevision,
)

_SOURCE_SUBMISSION = DutyKind("source-submission")


class InMemoryConfigurationStore:
    """Deterministic, in-process implementation of ConfigurationStorePort.

    Not thread-safe, not durable, not a substitute for F6a's real recovery
    qualification. Every scoped lookup is keyed by full, tenant-owning
    reference equality -- no ambient/default tenant or owner is assumed.
    """

    def __init__(self) -> None:
        self._heads: dict[ConfigurationRef, OwnerRevision] = {}
        self._published: dict[ConfigurationRef, ConfigurationRevisionRef] = {}
        self._revision_counters: dict[ConfigurationRef, int] = {}
        self._history: dict[ConfigurationRevisionRef, ComposedConfiguration] = {}
        self._results: dict[OperationRef, ConfigurationPublicationResult] = {}
        self._duties: dict[ConfigurationRef, list[ConfigurationSourceSubmissionDuty]] = {}
        self._duty_ids = count(1)

    def current_head(self, target: ConfigurationRef) -> OwnerRevision | None:
        return self._heads.get(target)

    def current_published(
        self, target: ConfigurationRef
    ) -> ConfigurationRevisionRef | None:
        return self._published.get(target)

    def read_revision(
        self, revision: ConfigurationRevisionRef
    ) -> ComposedConfiguration:
        try:
            return self._history[revision]
        except KeyError:
            raise UnknownRevisionError(
                "exact requested configuration revision is unavailable"
            ) from None

    def publish(
        self, operation: ConfigurationPublicationOperation
    ) -> ConfigurationPublicationResult:
        existing = self._results.get(operation.operation)
        if existing is not None:
            return existing

        current_head = self._heads.get(operation.target)
        if current_head != operation.expected_revision:
            result = ConfigurationPublicationResult(
                operation=operation.operation,
                stage=OperationStage.REJECTED,
                resulting_revision=None,
                published=None,
                effect=EffectExtent.NONE,
                error=ErrorDetail(
                    category=ErrorCategory.CONFLICT,
                    recoverability=Recoverability.REQUIRES_INTERVENTION,
                    causes=(
                        ErrorCause(
                            category=ErrorCategory.CONFLICT,
                            operation=operation.operation,
                            record_key="expected-revision-mismatch",
                        ),
                    ),
                ),
                duties=(),
            )
            self._results[operation.operation] = result
            return result

        next_head_value = (current_head.value if current_head is not None else 0) + 1
        new_head = OwnerRevision(subject=operation.target, value=next_head_value)

        revision_value = self._revision_counters.get(operation.target, 0) + 1
        self._revision_counters[operation.target] = revision_value
        published = ConfigurationRevisionRef(
            configuration=operation.target,
            revision=f"r{revision_value}",
            contract_version=operation.candidate.effective.contract_version,
        )

        duty_id = DutyId(f"duty-{next(self._duty_ids)}")
        duty = ConfigurationSourceSubmissionDuty(
            duty_id=duty_id,
            kind=_SOURCE_SUBMISSION,
            operation=operation.operation,
            published=published,
            responsible_principal=operation.requested_by,
            tenant_context=TenantContext(
                tenant_id=operation.target.application.scope.tenant_id
            ),
            requirement=EvidenceRequirement(
                subject=published,
                description="source submission evidence required for this publication",
            ),
        )

        result = ConfigurationPublicationResult(
            operation=operation.operation,
            stage=OperationStage.COMMITTED,
            resulting_revision=new_head,
            published=published,
            effect=EffectExtent.COMPLETED,
            error=None,
            duties=(duty_id,),
        )

        # Commit point: every derived record becomes visible together.
        self._heads[operation.target] = new_head
        self._published[operation.target] = published
        self._history[published] = operation.candidate
        self._results[operation.operation] = result
        self._duties.setdefault(operation.target, []).append(duty)

        return result

    def operation_result(
        self, operation: OperationRef
    ) -> ConfigurationPublicationResult | None:
        return self._results.get(operation)

    def outstanding_duties(
        self, target: ConfigurationRef
    ) -> tuple[ConfigurationSourceSubmissionDuty, ...]:
        return tuple(self._duties.get(target, ()))
