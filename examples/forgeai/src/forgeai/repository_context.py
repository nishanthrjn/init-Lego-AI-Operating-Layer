"""Explicit-path preflight observations; never model or mutation authority."""

from dataclasses import dataclass
from enum import Enum

from legoai_engineering.analyst.values import EvidenceAcquisitionError
from legoai_engineering.coding.api import CodingEvidencePort
from legoai_engineering.coding.values import CodingEvidence, CodingRequest
from legoai_engineering.repository.mutation import ContentDigest, digest_text
from legoai_engineering.repository.workspace import RepositoryPath


class ContextOutcome(Enum):
    READY_FOR_CONTEXT_CONFIRMATION = "READY_FOR_CONTEXT_CONFIRMATION"
    CONTEXT_INCOMPLETE = "CONTEXT_INCOMPLETE"


class ContextReason(Enum):
    DENIED = "DENIED"
    UNAVAILABLE = "UNAVAILABLE"
    BOUNDARY = "BOUNDARY"
    BUDGET = "BUDGET"
    ACQUISITION_FAILED = "ACQUISITION_FAILED"
    EVIDENCE_MISMATCH = "EVIDENCE_MISMATCH"


@dataclass(frozen=True, slots=True)
class ContextItem:
    path: RepositoryPath
    # CREATE requires verified absence, not an existing required file.
    role: str
    exists: bool
    size_bytes: int
    digest: ContentDigest | None

    def __post_init__(self) -> None:
        if type(self.path) is not RepositoryPath:
            raise TypeError("context path required")
        if len(self.path.value.encode("utf-8")) > 960:
            raise ValueError("context path exceeds bound")
        if self.role not in {"create", "update", "reference"}:
            raise ValueError("closed context role required")
        if type(self.exists) is not bool or type(self.size_bytes) is not int:
            raise TypeError("context observation requires bool and int")
        if not 0 <= self.size_bytes <= 8192:
            raise ValueError("context file exceeds bound")
        if self.role == "create":
            if self.exists or self.size_bytes or self.digest is not None:
                raise ValueError("create requires observed absence")
        elif not self.exists or type(self.digest) is not ContentDigest:
            raise ValueError("existing context requires digest")


@dataclass(frozen=True, slots=True)
class ContextPreflight:
    outcome: ContextOutcome
    inventory: tuple[ContextItem, ...] = ()
    reason: ContextReason | None = None

    def __post_init__(self) -> None:
        if type(self.outcome) is not ContextOutcome:
            raise TypeError("context outcome required")
        if type(self.inventory) is not tuple or len(self.inventory) > 16:
            raise ValueError("context inventory exceeds bound")
        if any(type(item) is not ContextItem for item in self.inventory):
            raise TypeError("context items required")
        paths = [item.path.value for item in self.inventory]
        if paths != sorted(paths) or len({p.casefold() for p in paths}) != len(paths):
            raise ValueError("context inventory must be sorted and unique")
        references = [item for item in self.inventory if item.role == "reference"]
        targets = [item for item in self.inventory if item.role != "reference"]
        if (
            len(references) > 8
            or len(targets) > 8
            or sum(item.size_bytes for item in references) > 16384
            or sum(item.size_bytes for item in targets) > 24576
        ):
            raise ValueError("context aggregate exceeds bound")
        ready = self.outcome is ContextOutcome.READY_FOR_CONTEXT_CONFIRMATION
        if ready != bool(self.inventory) or ready != (self.reason is None):
            raise ValueError("inconsistent context result")
        if self.reason is not None and type(self.reason) is not ContextReason:
            raise TypeError("closed context reason required")


async def preflight_context(
    reader: CodingEvidencePort, request: CodingRequest
) -> ContextPreflight:
    """Acquire exact declared targets/references through their existing grants.

    No recursive discovery, optional paths, content retention or invocation.
    Missing/unreadable paths deliberately share the public UNAVAILABLE reason.
    Cancellation propagates; unexpected acquisition errors retain no raw text.
    """
    if type(request) is not CodingRequest:
        raise TypeError("preflight requires CodingRequest")
    try:
        evidence = await reader.acquire(
            request.targets, request.context.tenant_context, request.references
        )
    except EvidenceAcquisitionError as error:
        return ContextPreflight(
            ContextOutcome.CONTEXT_INCOMPLETE,
            reason=ContextReason[error.reason.name],
        )
    except Exception:
        return ContextPreflight(
            ContextOutcome.CONTEXT_INCOMPLETE,
            reason=ContextReason.ACQUISITION_FAILED,
        )
    if (
        type(evidence) is not CodingEvidence
        or {file.target for file in evidence.files} != set(request.targets)
        or set(evidence.reference_paths) != set(request.references)
    ):
        return ContextPreflight(
            ContextOutcome.CONTEXT_INCOMPLETE,
            reason=ContextReason.EVIDENCE_MISMATCH,
        )
    items = [
        ContextItem(
            file.target.path,
            file.target.operation.value,
            file.current is not None,
            len(file.current.text.encode("utf-8")) if file.current else 0,
            file.digest,
        )
        for file in evidence.files
    ]
    if evidence.references is not None:
        items.extend(
            ContextItem(
                RepositoryPath(text.path),
                "reference",
                True,
                len(text.text.encode("utf-8")),
                digest_text(text.text),
            )
            for text in evidence.references.files
        )
    return ContextPreflight(
        ContextOutcome.READY_FOR_CONTEXT_CONFIRMATION,
        tuple(sorted(items, key=lambda item: item.path.value)),
    )


def context_summary(result: ContextPreflight) -> str:
    """Metadata only; acquired text and arbitrary error messages never appear."""
    lines = [result.outcome.value]
    if result.reason is not None:
        lines.append("context reason: " + result.reason.value)
    for item in result.inventory:
        digest = item.digest.value if item.digest is not None else "absent"
        lines.append(
            f"{item.path.value}: required {item.role}; "
            f"exists={item.exists}; bytes={item.size_bytes}; digest={digest}"
        )
    return "\n".join(lines)
