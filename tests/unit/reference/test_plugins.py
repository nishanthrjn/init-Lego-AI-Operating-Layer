"""Gate-2 M5: ADR-006 SS8 -- deterministic reference lifecycle transitions.
Stage-collapse is structurally impossible: each function is independent and
must be invoked explicitly; none produces a Catalog entry or an executable
binding.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

import pytest

from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import TenantId
from legoai.kernel.versions import Version
from legoai.plugins.ports import (
    LifecycleTransitionError,
    PluginAdmissionId,
    PluginLifecycleRecord,
    PluginLifecycleState,
    ValidationOutcome,
)
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.reference import plugins as lifecycle

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _declaration() -> PluginDeclaration:
    return PluginDeclaration(
        PluginId("legoai", "deterministic-fixture"),
        Version(0, 1, 0),
        (CapabilityOffer(CapabilityId("text-normalize"), Version(1, 0, 0)),),
        (),
    )


def _tenant() -> TenantContext:
    return TenantContext(TenantId("tenant"))


def _validated_record() -> PluginLifecycleRecord:
    declaration = _declaration()
    discovered = lifecycle.inspect(declaration)
    validation = lifecycle.validate(discovered, declaration, evaluated_at=_EPOCH)
    return lifecycle.admit(
        validation, _tenant(), PluginAdmissionId("admission-1"), established_at=_EPOCH
    )


# --- inspect / validate --------------------------------------------------------


def test_inspect_reads_identity_without_side_effect() -> None:
    declaration = _declaration()
    discovered = lifecycle.inspect(declaration)
    assert discovered.plugin_id == declaration.plugin_id
    assert discovered.release == declaration.release


def test_inspect_rejects_non_declaration() -> None:
    with pytest.raises(TypeError, match="PluginDeclaration"):
        lifecycle.inspect(object())  # type: ignore[arg-type]


def test_validate_rejects_wrong_type_arguments() -> None:
    declaration = _declaration()
    discovered = lifecycle.inspect(declaration)
    with pytest.raises(TypeError, match="DiscoveredPluginRef"):
        lifecycle.validate(object(), declaration, evaluated_at=_EPOCH)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="PluginDeclaration"):
        lifecycle.validate(discovered, object(), evaluated_at=_EPOCH)  # type: ignore[arg-type]


def test_validate_matches_discovery_to_declaration() -> None:
    declaration = _declaration()
    discovered = lifecycle.inspect(declaration)
    result = lifecycle.validate(discovered, declaration, evaluated_at=_EPOCH)
    assert result.outcome is ValidationOutcome.COMPATIBLE


def test_validate_detects_substituted_declaration() -> None:
    # Discovery claimed one release; a *different* declaration is inspected --
    # ADR-006 SS5's substitution-prevention requirement.
    declaration = _declaration()
    discovered = lifecycle.inspect(declaration)
    substituted = PluginDeclaration(declaration.plugin_id, Version(9, 9, 9))
    result = lifecycle.validate(discovered, substituted, evaluated_at=_EPOCH)
    assert result.outcome is ValidationOutcome.INCOMPATIBLE


def test_validate_does_not_admit() -> None:
    declaration = _declaration()
    discovered = lifecycle.inspect(declaration)
    result = lifecycle.validate(discovered, declaration, evaluated_at=_EPOCH)
    assert not hasattr(result, "state")
    assert not hasattr(result, "admission_id")


# --- admit ---------------------------------------------------------------------


def test_admit_commits_validated_state() -> None:
    record = _validated_record()
    assert record.state is PluginLifecycleState.VALIDATED
    assert record.revision == 1


def test_admit_refuses_incompatible_validation() -> None:
    declaration = _declaration()
    discovered = lifecycle.inspect(declaration)
    substituted = PluginDeclaration(declaration.plugin_id, Version(9, 9, 9))
    bad_validation = lifecycle.validate(discovered, substituted, evaluated_at=_EPOCH)
    with pytest.raises(LifecycleTransitionError, match="incompatible"):
        lifecycle.admit(
            bad_validation,
            _tenant(),
            PluginAdmissionId("admission-1"),
            established_at=_EPOCH,
        )


def test_admit_rejects_wrong_type_arguments() -> None:
    declaration = _declaration()
    discovered = lifecycle.inspect(declaration)
    validation = lifecycle.validate(discovered, declaration, evaluated_at=_EPOCH)
    with pytest.raises(TypeError, match="ValidationResult"):
        lifecycle.admit(
            object(),  # type: ignore[arg-type]
            _tenant(),
            PluginAdmissionId("a1"),
            established_at=_EPOCH,
        )
    with pytest.raises(TypeError, match="TenantContext"):
        lifecycle.admit(
            validation,
            object(),  # type: ignore[arg-type]
            PluginAdmissionId("a1"),
            established_at=_EPOCH,
        )
    with pytest.raises(TypeError, match="PluginAdmissionId"):
        bad_admission_id = cast(PluginAdmissionId, object())
        lifecycle.admit(validation, _tenant(), bad_admission_id, established_at=_EPOCH)


def test_admit_does_not_activate() -> None:
    record = _validated_record()
    assert record.state is not PluginLifecycleState.ACTIVE
    assert record.state is not PluginLifecycleState.INITIALIZED


# --- initialize / activate happy path -------------------------------------------


def test_full_happy_path_validated_to_active() -> None:
    validated = _validated_record()
    initialized = lifecycle.initialize(validated, established_at=_EPOCH)
    assert initialized.state is PluginLifecycleState.INITIALIZED
    assert initialized.revision == 2
    active = lifecycle.activate(initialized, established_at=_EPOCH)
    assert active.state is PluginLifecycleState.ACTIVE
    assert active.revision == 3


def test_initialize_does_not_publish_catalog() -> None:
    validated = _validated_record()
    initialized = lifecycle.initialize(validated, established_at=_EPOCH)
    assert not hasattr(initialized, "catalog_entry")
    assert not hasattr(initialized, "published")


def test_transitions_never_mutate_predecessor_record() -> None:
    validated = _validated_record()
    initialized = lifecycle.initialize(validated, established_at=_EPOCH)
    assert validated.state is PluginLifecycleState.VALIDATED
    assert validated.revision == 1
    assert initialized is not validated


# --- illegal transitions --------------------------------------------------------


def test_activate_before_initialize_is_rejected() -> None:
    validated = _validated_record()
    with pytest.raises(LifecycleTransitionError, match="cannot transition"):
        lifecycle.activate(validated, established_at=_EPOCH)


def test_initialize_twice_is_rejected() -> None:
    validated = _validated_record()
    initialized = lifecycle.initialize(validated, established_at=_EPOCH)
    with pytest.raises(LifecycleTransitionError):
        lifecycle.initialize(initialized, established_at=_EPOCH)


def test_retired_record_accepts_no_further_transition() -> None:
    validated = _validated_record()
    stopped = lifecycle.stop(validated, established_at=_EPOCH)
    retired = lifecycle.retire(stopped, established_at=_EPOCH)
    transitions: tuple[
        Callable[[PluginLifecycleRecord], PluginLifecycleRecord], ...
    ] = (
        lambda r: lifecycle.initialize(r, established_at=_EPOCH),
        lambda r: lifecycle.activate(r, established_at=_EPOCH),
        lambda r: lifecycle.stop(r, established_at=_EPOCH),
        lambda r: lifecycle.mark_failed(r, established_at=_EPOCH),
        lambda r: lifecycle.retire(r, established_at=_EPOCH),
    )
    for transition in transitions:
        with pytest.raises(LifecycleTransitionError):
            transition(retired)


# --- failure / degrade / stopping paths -----------------------------------------


@pytest.mark.parametrize(
    "build_to_state",
    [
        lambda: _validated_record(),
        lambda: lifecycle.initialize(_validated_record(), established_at=_EPOCH),
        lambda: lifecycle.activate(
            lifecycle.initialize(_validated_record(), established_at=_EPOCH),
            established_at=_EPOCH,
        ),
    ],
)
def test_mark_failed_permitted_from_validated_initialized_and_active(
    build_to_state: Callable[[], PluginLifecycleRecord],
) -> None:
    record = build_to_state()
    failed = lifecycle.mark_failed(record, established_at=_EPOCH)
    assert failed.state is PluginLifecycleState.FAILED


def test_failed_record_can_only_move_to_stopping() -> None:
    validated = _validated_record()
    failed = lifecycle.mark_failed(validated, established_at=_EPOCH)
    with pytest.raises(LifecycleTransitionError):
        lifecycle.activate(failed, established_at=_EPOCH)
    stopping = lifecycle.begin_stopping(failed, established_at=_EPOCH)
    assert stopping.state is PluginLifecycleState.STOPPING


def test_degraded_active_recovers_via_activate() -> None:
    initialized = lifecycle.initialize(_validated_record(), established_at=_EPOCH)
    active = lifecycle.activate(initialized, established_at=_EPOCH)
    degraded = lifecycle.degrade(active, established_at=_EPOCH)
    assert degraded.state is PluginLifecycleState.DEGRADED
    recovered = lifecycle.activate(degraded, established_at=_EPOCH)
    assert recovered.state is PluginLifecycleState.ACTIVE


def test_stopping_to_stopped_to_retired() -> None:
    initialized = lifecycle.initialize(_validated_record(), established_at=_EPOCH)
    active = lifecycle.activate(initialized, established_at=_EPOCH)
    stopping = lifecycle.begin_stopping(active, established_at=_EPOCH)
    stopped = lifecycle.stop(stopping, established_at=_EPOCH)
    retired = lifecycle.retire(stopped, established_at=_EPOCH)
    assert retired.state is PluginLifecycleState.RETIRED


def test_stop_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="PluginLifecycleRecord"):
        lifecycle.stop(object(), established_at=_EPOCH)  # type: ignore[arg-type]
