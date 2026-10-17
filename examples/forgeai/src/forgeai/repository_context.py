"""Explicit-path preflight observations; never model or mutation authority."""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from legoai.kernel.context import TenantContext
from legoai_engineering.analyst.values import (
    AcquisitionFailure,
    EvidenceAcquisitionError,
)
from legoai_engineering.coding.api import CodingEvidencePort
from legoai_engineering.coding.values import CodingEvidence, CodingRequest, CodingTarget
from legoai_engineering.git.values import GitHead
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
    return inventory_from_evidence(evidence, request)


def inventory_from_evidence(
    evidence: CodingEvidence, request: CodingRequest
) -> ContextPreflight:
    """One metadata projection for both preflight and the disclosure gate."""
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
    if result.outcome is ContextOutcome.READY_FOR_CONTEXT_CONFIRMATION:
        lines.append("inventory identity: " + inventory_digest(result).value)
    if result.reason is not None:
        lines.append("context reason: " + result.reason.value)
    for item in result.inventory:
        digest = item.digest.value if item.digest is not None else "absent"
        lines.append(
            f"{item.path.value}: required {item.role}; "
            f"exists={item.exists}; bytes={item.size_bytes}; digest={digest}"
        )
    return "\n".join(lines)


class ConfirmationReason(Enum):
    REQUIRED = "CONTEXT_CONFIRMATION_REQUIRED"
    DECLINED = "CONTEXT_CONFIRMATION_DECLINED"
    INVALID = "CONTEXT_CONFIRMATION_INVALID"
    INCOMPLETE = "CONTEXT_INCOMPLETE"
    STALE = "CONTEXT_CONFIRMATION_STALE"
    REPOSITORY = "CONTEXT_REPOSITORY_MISMATCH"
    SCOPE = "CONTEXT_SCOPE_MISMATCH"
    TASK = "CONTEXT_TASK_MISMATCH"
    INVENTORY = "CONTEXT_INVENTORY_CHANGED"


def _digest(value: object) -> ContentDigest:
    return digest_text(json.dumps(value, ensure_ascii=True, separators=(",", ":")))


@dataclass(frozen=True, slots=True)
class ContextBinding:
    """Versioned, run-local identity; hashes only, never repository contents."""

    repository: ContentDigest
    scope: ContentDigest
    task: ContentDigest
    lifecycle: ContentDigest
    inventory: ContentDigest

    def __post_init__(self) -> None:
        if any(
            type(value) is not ContentDigest
            for value in (
                self.repository,
                self.scope,
                self.task,
                self.lifecycle,
                self.inventory,
            )
        ):
            raise TypeError("context binding requires digests")

    @property
    def identity(self) -> ContentDigest:
        return _digest(
            (
                "forgeai-context-confirmation-v1",
                self.repository.value,
                self.scope.value,
                self.task.value,
                self.lifecycle.value,
                self.inventory.value,
            )
        )


def bind_context(
    workspace: str,
    head: GitHead,
    request: CodingRequest,
    preflight: ContextPreflight,
) -> ContextBinding:
    if preflight.outcome is not ContextOutcome.READY_FOR_CONTEXT_CONFIRMATION:
        raise ValueError("only ready context can be bound")
    expected = sorted(
        [(target.path.value, target.operation.value) for target in request.targets]
        + [(path.value, "reference") for path in request.references]
    )
    if expected != [(item.path.value, item.role) for item in preflight.inventory]:
        raise ValueError("preflight does not match request scope")
    return ContextBinding(
        _digest(
            (
                workspace,
                head.kind.value,
                head.branch,
                head.commit.value if head.commit else None,
            )
        ),
        _digest(("required-scope-v1", expected)),
        _digest((request.objective, request.constraints)),
        _digest(
            (
                request.context.execution_id.value,
                request.context.tenant_context.tenant_id.value,
            )
        ),
        inventory_digest(preflight),
    )


def inventory_digest(preflight: ContextPreflight) -> ContentDigest:
    return _digest(
        [
            (
                item.path.value,
                item.role,
                item.exists,
                item.size_bytes,
                item.digest.value if item.digest else None,
            )
            for item in preflight.inventory
        ]
    )


@dataclass(frozen=True, slots=True)
class ContextConfirmation:
    binding: ContextBinding
    approved: bool
    reason: ConfirmationReason | None = None

    def __post_init__(self) -> None:
        if type(self.binding) is not ContextBinding or type(self.approved) is not bool:
            raise TypeError("typed confirmation required")
        if self.reason is not None and type(self.reason) is not ConfirmationReason:
            raise TypeError("closed confirmation reason required")
        if not self.approved and self.reason is None:
            raise ValueError("refusal requires a reason")

    @property
    def confirmed(self) -> bool:
        return self.approved and self.reason is None


def confirm_inventory(
    binding: ContextBinding,
    inventory: ContextPreflight,
    confirm: Callable[[ContextPreflight], bool] | None,
) -> ContextConfirmation:
    """The trusted operator callback approves only this immutable inventory.

    The worker constructs the binding before calling it; no external receipt
    or persisted approval is accepted. This function performs no I/O itself.
    """
    reason = ConfirmationReason.REQUIRED
    if inventory.outcome is ContextOutcome.CONTEXT_INCOMPLETE:
        reason = ConfirmationReason.INCOMPLETE
    elif binding.inventory != inventory_digest(inventory):
        reason = ConfirmationReason.INVENTORY
    elif confirm is not None:
        try:
            if confirm(inventory) is True:
                return ContextConfirmation(binding, True)
            reason = ConfirmationReason.DECLINED
        except Exception, KeyboardInterrupt:
            reason = ConfirmationReason.INVALID
    return ContextConfirmation(binding, False, reason)


def confirmation_mismatch(
    confirmation: ContextConfirmation, current: ContextBinding
) -> ConfirmationReason | None:
    if not confirmation.confirmed:
        return confirmation.reason
    for name, reason in (
        ("repository", ConfirmationReason.REPOSITORY),
        ("scope", ConfirmationReason.SCOPE),
        ("task", ConfirmationReason.TASK),
        ("lifecycle", ConfirmationReason.STALE),
        ("inventory", ConfirmationReason.INVENTORY),
    ):
        if getattr(confirmation.binding, name) != getattr(current, name):
            return reason
    return None


@dataclass(frozen=True, slots=True)
class ConfirmedEvidence:
    """Ephemeral exact bundle for one CodingAgent call, never a reusable grant.

    Acquisition and authorization have just completed in the worker. Avoid a
    third filesystem read between comparison and serialization by CodingAgent.
    """

    request: CodingRequest = field(repr=False)
    evidence: CodingEvidence = field(repr=False)

    async def acquire(
        self,
        targets: tuple[CodingTarget, ...],
        tenant: TenantContext,
        references: tuple[RepositoryPath, ...] = (),
    ) -> CodingEvidence:
        if (
            targets != self.request.targets
            or tenant != self.request.context.tenant_context
            or references != self.request.references
        ):
            raise EvidenceAcquisitionError(AcquisitionFailure.DENIED)
        return self.evidence
