"""Contract tests for ConfigurationStorePort implementations.

Reusable verbatim once F6a introduces a real SQLite realization: add a new
factory to STORE_FACTORIES below and every test in this module runs
unchanged against the new backend, proving the Protocol boundary is real
rather than merely matching the in-memory fake's internal structure
(Gate-1 plan SS9.1).
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from legoai.application.ports import ConfigurationStorePort, UnknownRevisionError
from legoai.application.values import (
    ComposedConfiguration,
    ConfigurationPublicationOperation,
    ConfigurationPublicationResult,
    OperationStage,
)
from legoai.governance.values import Principal
from legoai.kernel.identity import ApplicationId, OperationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    OwnerRevision,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.reference.application.configuration import compose_configuration
from tests.support.configuration_store import InMemoryConfigurationStore

VERSION = Version(0, 1, 0)


def _in_memory_factory() -> ConfigurationStorePort:
    return InMemoryConfigurationStore()


STORE_FACTORIES: list[Callable[[], ConfigurationStorePort]] = [
    _in_memory_factory,
    # F6a adds a second factory here (e.g. a SQLite-backed realization) --
    # every test below must pass unchanged against it.
]


@pytest.fixture(params=STORE_FACTORIES, ids=["in-memory-fake"])
def store(request: pytest.FixtureRequest) -> ConfigurationStorePort:
    factory: Callable[[], ConfigurationStorePort] = request.param
    return factory()


def _target(
    instance: str = "inst1",
    tenant: str = "t1",
    owner: str = "owner1",
    app: str = "app1",
) -> ConfigurationRef:
    scope = ReferenceScope(owner, TenantId(tenant))
    return ConfigurationRef(ApplicationRef(scope, ApplicationId(app)), instance)


def _operation(target: ConfigurationRef, op_id: str) -> OperationRef:
    return OperationRef(target, OperationId(op_id), "contract-fixture")


def _principal(pid: str = "p1") -> Principal:
    return Principal(PrincipalRef("issuer1", PrincipalId(pid)))


def _candidate(target: ConfigurationRef) -> ComposedConfiguration:
    return compose_configuration(
        target, (), contract_version=VERSION, interpretation_version=VERSION
    )


def _publish(
    store: ConfigurationStorePort,
    target: ConfigurationRef,
    op_id: str,
    expected: OwnerRevision | None = None,
) -> ConfigurationPublicationResult:
    operation = ConfigurationPublicationOperation(
        operation=_operation(target, op_id),
        target=target,
        expected_revision=expected,
        candidate=_candidate(target),
        requested_by=_principal(),
    )
    return store.publish(operation)


def test_in_memory_fake_structurally_implements_the_port() -> None:
    assert isinstance(InMemoryConfigurationStore(), ConfigurationStorePort)


class TestWriteReadCurrentRecord:
    def test_first_publish_succeeds_with_expected_absence(
        self, store: ConfigurationStorePort
    ) -> None:
        target = _target()
        result = _publish(store, target, "op1", expected=None)
        assert result.stage is OperationStage.COMMITTED
        assert store.current_published(target) == result.published

    def test_revision_advances_correctly(self, store: ConfigurationStorePort) -> None:
        target = _target()
        first = _publish(store, target, "op1", expected=None)
        head_after_first = store.current_head(target)
        assert head_after_first is not None
        second = _publish(store, target, "op2", expected=head_after_first)
        head_after_second = store.current_head(target)
        assert head_after_second is not None
        assert head_after_second.value == head_after_first.value + 1
        assert second.published != first.published


class TestConditionalMutation:
    def test_expected_revision_success(self, store: ConfigurationStorePort) -> None:
        target = _target()
        _publish(store, target, "op1", expected=None)
        head = store.current_head(target)
        result = _publish(store, target, "op2", expected=head)
        assert result.stage is OperationStage.COMMITTED

    def test_stale_expected_revision_rejected(
        self, store: ConfigurationStorePort
    ) -> None:
        target = _target()
        _publish(store, target, "op1", expected=None)
        stale = OwnerRevision(target, 999)
        result = _publish(store, target, "op2", expected=stale)
        assert result.stage is OperationStage.REJECTED
        assert result.error is not None

    def test_expected_absence_rejected_once_something_is_published(
        self, store: ConfigurationStorePort
    ) -> None:
        target = _target()
        _publish(store, target, "op1", expected=None)
        result = _publish(store, target, "op2", expected=None)
        assert result.stage is OperationStage.REJECTED


class TestHistoricalReads:
    def test_exact_historical_revision_read(
        self, store: ConfigurationStorePort
    ) -> None:
        target = _target()
        result = _publish(store, target, "op1", expected=None)
        assert result.published is not None
        composed = store.read_revision(result.published)
        assert composed.target == target

    def test_missing_historical_revision_does_not_fall_back(
        self, store: ConfigurationStorePort
    ) -> None:
        target = _target()
        _publish(store, target, "op1", expected=None)
        bad_ref = ConfigurationRevisionRef(target, "does-not-exist", VERSION)
        with pytest.raises(UnknownRevisionError):
            store.read_revision(bad_ref)

    def test_old_revision_remains_readable_after_a_new_publish(
        self, store: ConfigurationStorePort
    ) -> None:
        target = _target()
        first = _publish(store, target, "op1", expected=None)
        head = store.current_head(target)
        _publish(store, target, "op2", expected=head)
        assert first.published is not None
        # The superseded revision's own meaning is never rewritten or lost.
        store.read_revision(first.published)


class TestOperationResultRecovery:
    def test_operation_result_persistence_and_recovery(
        self, store: ConfigurationStorePort
    ) -> None:
        target = _target()
        result = _publish(store, target, "op1", expected=None)
        recovered = store.operation_result(_operation(target, "op1"))
        assert recovered == result

    def test_lost_acknowledgment_does_not_create_second_commit(
        self, store: ConfigurationStorePort
    ) -> None:
        target = _target()
        result = _publish(store, target, "op1", expected=None)
        replay = _publish(store, target, "op1", expected=None)
        assert replay == result
        head = store.current_head(target)
        assert head is not None
        assert head.value == 1

    def test_same_stored_result_recovered_unchanged(
        self, store: ConfigurationStorePort
    ) -> None:
        target = _target()
        _publish(store, target, "op1", expected=None)
        first_read = store.operation_result(_operation(target, "op1"))
        second_read = store.operation_result(_operation(target, "op1"))
        assert first_read == second_read

    def test_unknown_operation_result_is_none(
        self, store: ConfigurationStorePort
    ) -> None:
        target = _target()
        assert store.operation_result(_operation(target, "never-happened")) is None


class TestOutstandingDuties:
    def test_duty_persisted_after_publish(self, store: ConfigurationStorePort) -> None:
        target = _target()
        result = _publish(store, target, "op1", expected=None)
        duties = store.outstanding_duties(target)
        assert len(duties) == 1
        assert duties[0].duty_id in result.duties

    def test_duty_discovery_is_scoped(self, store: ConfigurationStorePort) -> None:
        target_a = _target(instance="a")
        target_b = _target(instance="b")
        _publish(store, target_a, "op1", expected=None)
        assert store.outstanding_duties(target_b) == ()


class TestOwnerAndTenantIsolation:
    def test_owner_isolation(self, store: ConfigurationStorePort) -> None:
        target_a = _target(owner="owner-a")
        target_b = _target(owner="owner-b")
        _publish(store, target_a, "op1", expected=None)
        assert store.current_head(target_b) is None

    def test_tenant_isolation(self, store: ConfigurationStorePort) -> None:
        target_a = _target(tenant="tenant-a")
        target_b = _target(tenant="tenant-b")
        _publish(store, target_a, "op1", expected=None)
        assert store.current_head(target_b) is None
        assert store.outstanding_duties(target_b) == ()


class TestCompoundOwnerLocalMutation:
    def test_commit_makes_head_published_result_and_duty_visible_together(
        self, store: ConfigurationStorePort
    ) -> None:
        """Models the atomicity the Port promises: after publish() returns,
        every derived owner-local fact agrees with the returned result. This
        proves the fake's (and, later, F6a's) behavior against the Port
        contract -- it does not by itself prove crash-safe transactional
        atomicity, which F6a must qualify independently (ADR-004 SS15)."""
        target = _target()
        result = _publish(store, target, "op1", expected=None)
        assert store.current_head(target) == result.resulting_revision
        assert store.current_published(target) == result.published
        assert store.operation_result(_operation(target, "op1")) == result
        assert {duty.duty_id for duty in store.outstanding_duties(target)} == set(
            result.duties
        )
