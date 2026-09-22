"""Gate-2 M8: deterministic in-memory reference realization of
`EvidenceCustodyPort`, plus the pure `EvidenceRequirement` satisfaction
check.

No persistence, no filesystem/network I/O, no background task, no asyncio.
`InMemoryEvidenceCustody` guards its internal store only against the
ordinary single-threaded call sequence a reference/test process makes; it
makes **no concurrency or thread-safety claim** (the same scope limitation
already accepted for M6's `InMemoryCatalog`).

Append-only, exact-ID custody: an unknown `EvidenceId` reads back `None`
(never a fabricated empty record); an exact equivalent resubmission is an
idempotent no-op returning the already-committed record; a resubmission
under the same `EvidenceId` with materially different content raises
`EvidenceConflictError` rather than silently overwriting.
"""

from legoai.evidence.ports import EvidenceConflictError, EvidenceId, EvidenceRecord
from legoai.evidence.values import EvidenceRequirement
from legoai.kernel.context import TenantContext
from legoai.kernel.references import ConfigurationRevisionRef


def satisfies_requirement(
    requirement: EvidenceRequirement, record: EvidenceRecord
) -> bool:
    """Whether `record` satisfies `requirement` (task SS38): exact subject
    identity only -- no fuzzy/partial matching, and a record whose subject
    is not the same `ConfigurationRevisionRef` never satisfies it.
    """
    if type(requirement) is not EvidenceRequirement:
        raise TypeError("satisfies_requirement requires EvidenceRequirement")
    if type(record) is not EvidenceRecord:
        raise TypeError("satisfies_requirement requires EvidenceRecord")
    return (
        type(record.subject) is ConfigurationRevisionRef
        and record.subject == requirement.subject
    )


class InMemoryEvidenceCustody:
    """Reference `EvidenceCustodyPort` realization. Construction commits
    nothing and holds an empty store.
    """

    def __init__(self) -> None:
        self._records: dict[EvidenceId, EvidenceRecord] = {}

    def record(self, record: EvidenceRecord) -> EvidenceRecord:
        if type(record) is not EvidenceRecord:
            raise TypeError("record requires EvidenceRecord")
        existing = self._records.get(record.evidence_id)
        if existing is not None:
            if existing == record:
                return existing
            raise EvidenceConflictError(
                "evidence id already recorded with different content"
            )
        self._records[record.evidence_id] = record
        return record

    def read(
        self, evidence_id: EvidenceId, tenant_context: TenantContext
    ) -> EvidenceRecord | None:
        if type(evidence_id) is not EvidenceId:
            raise TypeError("read requires EvidenceId")
        if type(tenant_context) is not TenantContext:
            raise TypeError("read requires TenantContext")
        record = self._records.get(evidence_id)
        if record is None or record.tenant_context != tenant_context:
            return None
        return record
