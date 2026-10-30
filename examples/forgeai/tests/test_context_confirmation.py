"""Exact context decisions, stale observations and independent authority gates."""

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REVIEW_CHANGES,
    REWORK,
    FakeSandbox,
    approve,
    config,
    proposal,
    replay,
    repository,
    snapshot,
    task,
)
from legoai.kernel.context import TenantContext
from legoai_engineering.analyst.values import (
    AcquisitionFailure,
    EvidenceAcquisitionError,
)
from legoai_engineering.coding.values import CodingEvidence, CodingRequest, CodingTarget
from legoai_engineering.git.values import GitCommitId
from legoai_engineering.repository.mutation import digest_text
from legoai_engineering.repository.workspace import RepositoryPath

from forgeai.cli import ReplayModel, summarize
from forgeai.composition import PreparedRun, prepare_run
from forgeai.domain import OperatorDecision, TaskDisposition, TaskEvidence, TaskFailure
from forgeai.guard import WorkspaceGuard
from forgeai.repository_context import (
    ConfirmationReason,
    ConfirmedEvidence,
    ContextBinding,
    ContextConfirmation,
    ContextOutcome,
    ContextPreflight,
    ContextReason,
    bind_context,
    confirm_inventory,
    confirmation_mismatch,
    preflight_context,
)


@pytest.fixture
def ready(tmp_path: Path) -> tuple[PreparedRun, CodingRequest, ContextPreflight]:
    prepared = prepare_run(
        config(repository(tmp_path), replay()),
        WorkspaceGuard(),
        approve=approve,
        sandbox=FakeSandbox(),
    )
    selected = task()
    request = CodingRequest(
        selected.objective, selected.targets, selected.constraints, prepared.context
    )
    inventory = asyncio.run(
        preflight_context(prepared.worker.agent.evidence_reader, request)
    )
    return prepared, request, inventory


def binding(
    prepared: PreparedRun, request: CodingRequest, inventory: ContextPreflight
) -> ContextBinding:
    return bind_context(
        prepared.worker.workspace,
        prepared.worker.git.inspect().head,
        request,
        inventory,
    )


def test_exact_confirmation_is_deterministic_metadata_only(
    ready: tuple[PreparedRun, CodingRequest, ContextPreflight],
) -> None:
    prepared, request, inventory = ready
    identity = binding(*ready)
    seen: list[ContextPreflight] = []

    def approve_inventory(value: ContextPreflight) -> bool:
        seen.append(value)
        return True

    first = confirm_inventory(identity, inventory, approve_inventory)
    second = confirm_inventory(identity, inventory, approve_inventory)
    assert first == second and first.confirmed
    assert seen == [inventory, inventory]
    assert confirmation_mismatch(first, binding(prepared, request, inventory)) is None
    assert "def " not in repr(first) and request.objective not in repr(first)
    assert len(first.binding.identity.value) == 64
    with pytest.raises(ValueError):
        TaskEvidence("run", context_confirmations=(first,) * 3)
    with pytest.raises(ValueError):
        TaskEvidence("run", context_preflight=inventory, context_confirmed=True)


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("repository", ConfirmationReason.REPOSITORY),
        ("scope", ConfirmationReason.SCOPE),
        ("task", ConfirmationReason.TASK),
        ("lifecycle", ConfirmationReason.STALE),
        ("inventory", ConfirmationReason.INVENTORY),
    ],
)
def test_each_binding_dimension_invalidates(
    ready: tuple[PreparedRun, CodingRequest, ContextPreflight],
    field: str,
    reason: ConfirmationReason,
) -> None:
    identity = binding(*ready)
    decision = ContextConfirmation(identity, True)
    changed = replace(identity, **{field: digest_text("changed")})
    assert changed.identity != identity.identity
    assert confirmation_mismatch(decision, changed) is reason


def test_binding_covers_real_task_repository_head_and_run(
    ready: tuple[PreparedRun, CodingRequest, ContextPreflight],
) -> None:
    prepared, request, inventory = ready
    worker = prepared.worker
    head = worker.git.inspect().head
    original = ContextConfirmation(binding(*ready), True)
    changed_task = binding(prepared, replace(request, objective="different"), inventory)
    assert confirmation_mismatch(original, changed_task) is ConfirmationReason.TASK
    reduced_request = replace(request, targets=request.targets[:1])
    reduced_inventory = replace(
        inventory,
        inventory=tuple(
            item for item in inventory.inventory if item.path == request.targets[0].path
        ),
    )
    reduced = binding(prepared, reduced_request, reduced_inventory)
    assert confirmation_mismatch(original, reduced) is ConfirmationReason.SCOPE
    changed_root = bind_context("another root", head, request, inventory)
    assert confirmation_mismatch(original, changed_root) is (
        ConfirmationReason.REPOSITORY
    )
    changed_head = bind_context(
        worker.workspace,
        replace(head, commit=GitCommitId("ab" * 20)),
        request,
        inventory,
    )
    assert confirmation_mismatch(original, changed_head) is (
        ConfirmationReason.REPOSITORY
    )
    fresh = replace(request, context=worker.coding_context(prepared.context))
    assert confirmation_mismatch(original, binding(prepared, fresh, inventory)) is (
        ConfirmationReason.STALE
    )


@pytest.mark.parametrize("change", ["remove", "add", "alias", "digest"])
def test_inventory_cannot_be_substituted_after_confirmation(
    ready: tuple[PreparedRun, CodingRequest, ContextPreflight], change: str
) -> None:
    prepared, request, inventory = ready
    identity = binding(*ready)
    items = list(inventory.inventory)
    if change == "remove":
        items.pop()
    elif change == "add":
        items.append(replace(items[0], path=RepositoryPath("extra.py")))
    elif change == "alias":
        items[0] = replace(items[0], path=RepositoryPath(items[0].path.value.upper()))
    else:
        items[0] = replace(items[0], digest=digest_text("changed"))
    changed = replace(
        inventory, inventory=tuple(sorted(items, key=lambda x: x.path.value))
    )
    called: list[bool] = []

    def unexpected(value: ContextPreflight) -> bool:
        called.append(True)
        return True

    result = confirm_inventory(identity, changed, unexpected)
    assert result.reason is ConfirmationReason.INVENTORY and not called
    if change != "digest":
        with pytest.raises(ValueError, match="scope"):
            binding(prepared, request, changed)


def test_incomplete_and_duplicate_inventories_cannot_be_confirmed(
    ready: tuple[PreparedRun, CodingRequest, ContextPreflight],
) -> None:
    prepared, request, inventory = ready
    incomplete = ContextPreflight(
        ContextOutcome.CONTEXT_INCOMPLETE, reason=ContextReason.UNAVAILABLE
    )
    result = confirm_inventory(binding(*ready), incomplete, lambda value: True)
    assert result.reason is ConfirmationReason.INCOMPLETE
    with pytest.raises(ValueError):
        binding(prepared, request, incomplete)
    with pytest.raises(ValueError):
        replace(inventory, inventory=(inventory.inventory[0],) * 2)


@pytest.mark.parametrize("answer", [None, False, "yes", 1])
def test_only_explicit_boolean_true_approves(
    ready: tuple[PreparedRun, CodingRequest, ContextPreflight], answer: object
) -> None:
    def invalid(value: ContextPreflight) -> bool:
        return answer  # type: ignore[return-value]

    decision = confirm_inventory(binding(*ready), ready[2], invalid)
    assert not decision.confirmed and decision.reason is ConfirmationReason.DECLINED
    missing = confirm_inventory(binding(*ready), ready[2], None)
    assert missing.reason is ConfirmationReason.REQUIRED


def test_callback_error_never_leaks_or_authorizes(tmp_path: Path) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    model, sandbox = replay(), FakeSandbox()

    def broken(value: ContextPreflight) -> bool:
        raise ValueError("SECRET-CANARY bearer prompt raw body")

    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=approve,
        sandbox=sandbox,
        confirm_context=broken,
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert result.failure is TaskFailure.CONTEXT_DECLINED
    assert result.evidence.context_confirmations[0].reason is ConfirmationReason.INVALID
    assert "SECRET-CANARY" not in repr(result.evidence) + summarize(result)
    assert model.calls == sandbox.calls == 0 and snapshot(root) == before


def test_file_change_after_confirmation_stops_before_coding(tmp_path: Path) -> None:
    root = repository(tmp_path)
    model, sandbox = replay(), FakeSandbox()

    def confirm(value: ContextPreflight) -> bool:
        (root / value.inventory[0].path.value).write_text(
            "# changed\n", encoding="utf-8"
        )
        return True

    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=approve,
        sandbox=sandbox,
        confirm_context=confirm,
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert result.failure is TaskFailure.CONTEXT_STALE
    assert result.evidence.context_confirmations[0].reason is (
        ConfirmationReason.INVENTORY
    )
    assert result.evidence.coding_status is None
    assert model.calls == sandbox.calls == 0


def test_exact_checked_bundle_is_used_without_third_acquisition(tmp_path: Path) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    model = replay()
    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=lambda value: OperatorDecision.decline(value),
        sandbox=FakeSandbox(),
        confirm_context=lambda value: True,
    )
    inner = prepared.worker.agent.evidence_reader

    class TwiceOnly:
        calls = 0

        async def acquire(
            self,
            targets: tuple[CodingTarget, ...],
            tenant: TenantContext,
            references: tuple[RepositoryPath, ...] = (),
        ) -> CodingEvidence:
            self.calls += 1
            assert self.calls <= 2, "no unchecked third acquisition"
            return await inner.acquire(targets, tenant, references)

    reader = TwiceOnly()
    worker = replace(
        prepared.worker, agent=replace(prepared.worker.agent, evidence_reader=reader)
    )
    result = asyncio.run(worker.run(task(), prepared.context))
    assert result.failure is TaskFailure.PROPOSAL_DECLINED
    assert reader.calls == 2 and model.calls == 1
    assert result.evidence.context_confirmations[0].confirmed
    assert snapshot(root) == before


def test_captured_bundle_refuses_another_scope(
    ready: tuple[PreparedRun, CodingRequest, ContextPreflight],
) -> None:
    prepared, request, _ = ready
    acquired = asyncio.run(
        prepared.worker.agent.evidence_reader.acquire(
            request.targets, request.context.tenant_context, request.references
        )
    )
    captured = ConfirmedEvidence(request, acquired)
    with pytest.raises(EvidenceAcquisitionError):
        asyncio.run(
            captured.acquire(request.targets[:1], request.context.tenant_context)
        )
    with pytest.raises(EvidenceAcquisitionError):
        asyncio.run(
            captured.acquire(
                request.targets,
                request.context.tenant_context,
                (RepositoryPath("extra.py"),),
            )
        )


@pytest.mark.parametrize("approve_rework", [False, True])
def test_rework_requires_fresh_confirmation(
    tmp_path: Path, approve_rework: bool
) -> None:
    root = repository(tmp_path)
    model = ReplayModel(proposal(), REVIEW_CHANGES, REWORK, REVIEW_ACCEPT)
    decisions: list[ContextPreflight] = []

    def confirm(value: ContextPreflight) -> bool:
        decisions.append(value)
        return len(decisions) == 1 or approve_rework

    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=approve,
        sandbox=FakeSandbox(),
        confirm_context=confirm,
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert len(decisions) == 2 and decisions[0] != decisions[1]
    first, second = result.evidence.context_confirmations
    assert first.binding.identity != second.binding.identity
    assert first.confirmed and second.confirmed is approve_rework
    if approve_rework:
        assert result.disposition is TaskDisposition.SUCCEEDED and model.calls == 4
    else:
        assert result.failure is TaskFailure.CONTEXT_DECLINED and model.calls == 2
        assert result.evidence.attempts[0].applied is not None
        assert result.evidence.attempts[1].coding_status is None


@pytest.mark.parametrize("failure", ["denied", "unexpected", "cancelled"])
def test_fresh_acquisition_failure_cannot_use_old_approval(
    tmp_path: Path, failure: str
) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    model, sandbox = replay(), FakeSandbox()
    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=approve,
        sandbox=sandbox,
        confirm_context=lambda value: True,
    )
    inner = prepared.worker.agent.evidence_reader

    class RevokedReader:
        calls = 0

        async def acquire(
            self,
            targets: tuple[CodingTarget, ...],
            tenant: TenantContext,
            references: tuple[RepositoryPath, ...] = (),
        ) -> CodingEvidence:
            self.calls += 1
            if self.calls == 1:
                return await inner.acquire(targets, tenant, references)
            if failure == "cancelled":
                raise asyncio.CancelledError
            if failure == "denied":
                raise EvidenceAcquisitionError(AcquisitionFailure.DENIED)
            raise ValueError("SECRET-CANARY")

    worker = replace(
        prepared.worker,
        agent=replace(prepared.worker.agent, evidence_reader=RevokedReader()),
    )
    if failure == "cancelled":
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(worker.run(task(), prepared.context))
    else:
        result = asyncio.run(worker.run(task(), prepared.context))
        assert result.failure is (
            TaskFailure.EVIDENCE_DENIED
            if failure == "denied"
            else TaskFailure.CONTEXT_STALE
        )
        assert not result.evidence.context_confirmed
        assert "SECRET-CANARY" not in summarize(result)
    assert worker.guard.acquire(worker.workspace)
    worker.guard.release(worker.workspace)
    assert model.calls == sandbox.calls == 0 and snapshot(root) == before
