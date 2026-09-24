"""Trusted authorized acquisition, reusing M8.1 policy and M2 filesystem semantics."""

from dataclasses import dataclass, field

from legoai.kernel.context import TenantContext

from legoai_engineering.analyst._composition import AuthorizedRepositoryEvidence
from legoai_engineering.analyst.values import (
    AcquisitionFailure,
    EvidenceAcquisitionError,
)
from legoai_engineering.coding.values import (
    CodingEvidence,
    CodingFile,
    CodingTarget,
    _targets,
)
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath


def _failure(error: WorkspaceError) -> EvidenceAcquisitionError:
    reason = (
        AcquisitionFailure.BOUNDARY
        if error.reason is WorkspaceFailure.BOUNDARY
        else AcquisitionFailure.BUDGET
        if error.reason is WorkspaceFailure.LIMIT
        else AcquisitionFailure.UNAVAILABLE
    )
    return EvidenceAcquisitionError(reason)


@dataclass(frozen=True, slots=True)
class AuthorizedCodingEvidence:
    """M8.1-bound operator scope also authorizes bounded CREATE parent metadata.

    Uses the existing private authorization check for CREATE observations, never
    issues a new grant. Listings are not disclosed. Absence is only an observation;
    independently authorized M4 application must recheck later. Stable M2 workspace
    and synchronous I/O limits remain. No parent creation, writes or retries.
    """

    reads: AuthorizedRepositoryEvidence = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.reads) is not AuthorizedRepositoryEvidence:
            raise TypeError("coding acquisition requires authorized repository composition")

    async def acquire(
        self, targets: tuple[CodingTarget, ...], tenant: TenantContext
    ) -> CodingEvidence:
        _targets(targets)
        if type(tenant) is not TenantContext:
            raise TypeError("coding acquisition requires TenantContext")
        if any(target.path not in self.reads.allowed_paths for target in targets):
            raise EvidenceAcquisitionError(AcquisitionFailure.DENIED)
        files: list[CodingFile] = []
        for target in sorted(targets, key=lambda item: item.path.value):
            if target.operation is FileChangeKind.UPDATE:
                acquired = await self.reads.acquire((target.path,), tenant)
                file = CodingFile(target, acquired.files[0])
            else:
                parent, _, _ = target.path.value.rpartition("/")
                self.reads._authorize(tenant)
                try:
                    entries = self.reads.workspace.list_entries(
                        RepositoryPath(parent) if parent else None
                    )
                except WorkspaceError as error:
                    raise _failure(error) from None
                if any(
                    entry.path.value.casefold() == target.path.value.casefold()
                    for entry in entries
                ):
                    raise EvidenceAcquisitionError(AcquisitionFailure.UNAVAILABLE)
                # Validate target-specific M2 exclusions/depth and distinguish
                # actual absence from a hidden or unreadable existing target.
                self.reads._authorize(tenant)
                try:
                    self.reads.workspace.read_text(target.path)
                except WorkspaceError as error:
                    if error.reason is not WorkspaceFailure.MISSING:
                        raise _failure(error) from None
                else:
                    raise EvidenceAcquisitionError(AcquisitionFailure.UNAVAILABLE)
                file = CodingFile(target, None)
            files.append(file)
            try:
                CodingEvidence(tuple(files))
            except ValueError:
                raise EvidenceAcquisitionError(AcquisitionFailure.BUDGET) from None
        self.reads._authorize(tenant)
        return CodingEvidence(tuple(files))
