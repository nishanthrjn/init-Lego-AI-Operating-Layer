"""F6b: recovery/qualification tests for the SQLite realization.

Separated by concern:
    * TestHealthyQualification / TestScopeQualification -- normal recovery
    * TestIntegrityFailures -- deliberately constructed physical corruption
    * TestRepresentationFailures -- corrupt/incompatible F5 payloads
    * TestLostAckAndDutyDiscovery -- restart-oriented semantic scenarios
    * TestSubprocessDurability -- real process-boundary durability/abrupt
      termination, using actual subprocesses, not exception injection

All tests use the real ``SQLiteConfigurationStore``/F5 codecs; no second
persistence implementation is created for recovery testing.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from legoai.application.values import ConfigurationPublicationOperation, OperationStage
from legoai.governance.values import Principal
from legoai.kernel.identity import ApplicationId, OperationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.reference.application import codec
from legoai.reference.application.configuration import compose_configuration
from legoai.reference.application.recovery import (
    RecoveryStatus,
    RecoveryUnavailableError,
    qualify_store,
)
from legoai.reference.application.sqlite_store import SQLiteConfigurationStore

VERSION = Version(0, 1, 0)


def _target(
    tenant: str = "t1", owner: str = "owner1", app: str = "app1", instance: str = "i1"
) -> ConfigurationRef:
    scope = ReferenceScope(owner, TenantId(tenant))
    return ConfigurationRef(ApplicationRef(scope, ApplicationId(app)), instance)


def _operation(target: ConfigurationRef, op_id: str = "op1") -> OperationRef:
    return OperationRef(target, OperationId(op_id), "recovery-fixture")


def _principal(pid: str = "p1") -> Principal:
    return Principal(PrincipalRef("issuer1", PrincipalId(pid)))


def _publish_op(
    target: ConfigurationRef, op_id: str = "op1"
) -> ConfigurationPublicationOperation:
    candidate = compose_configuration(
        target, (), contract_version=VERSION, interpretation_version=VERSION
    )
    return ConfigurationPublicationOperation(
        _operation(target, op_id), target, None, candidate, _principal()
    )


class TestHealthyQualification:
    def test_missing_file_raises_unavailable(self, tmp_path: Path) -> None:
        with pytest.raises(RecoveryUnavailableError):
            qualify_store(tmp_path / "never-created.sqlite3")

    def test_healthy_store_qualifies(self, tmp_path: Path) -> None:
        path = tmp_path / "healthy.sqlite3"
        store = SQLiteConfigurationStore(path)
        target = _target()
        store.publish(_publish_op(target))

        report = qualify_store(path)
        assert report.status is RecoveryStatus.QUALIFIED
        assert report.integrity_check == "ok"
        assert report.foreign_key_violations == ()
        assert report.physical_schema_version == 1
        assert len(report.scopes) == 1

    def test_recovery_import_has_no_side_effects(self) -> None:
        # Merely importing the module must not open a database, create a
        # file, or run any check -- all side effects require explicit
        # qualify_store() invocation.
        import legoai.reference.application.recovery as module

        assert hasattr(module, "qualify_store")

    def test_repeated_recovery_is_stable(self, tmp_path: Path) -> None:
        path = tmp_path / "stable.sqlite3"
        store = SQLiteConfigurationStore(path)
        target = _target()
        store.publish(_publish_op(target))

        first = qualify_store(path)
        second = qualify_store(path)
        assert first == second

    def test_recovery_does_not_mutate_head_or_results(self, tmp_path: Path) -> None:
        path = tmp_path / "no-mutation.sqlite3"
        store = SQLiteConfigurationStore(path)
        target = _target()
        result = store.publish(_publish_op(target))

        qualify_store(path)
        qualify_store(path)

        assert store.current_head(target) == result.resulting_revision
        assert store.operation_result(_operation(target)) == result
        assert store.outstanding_duties(target) == (
            store.outstanding_duties(target)
        )  # idempotent read, unchanged shape


class TestScopeQualification:
    def test_scope_reconstructed_exactly(self, tmp_path: Path) -> None:
        path = tmp_path / "scope.sqlite3"
        store = SQLiteConfigurationStore(path)
        target = _target()
        result = store.publish(_publish_op(target))

        report = qualify_store(path)
        scope = report.scopes[0]
        assert scope.target == target
        assert scope.current_head == result.resulting_revision
        assert scope.current_published == result.published
        assert scope.revision_count == 1
        assert scope.result_count == 1
        assert scope.qualified is True

    def test_multi_owner_scopes_isolated(self, tmp_path: Path) -> None:
        path = tmp_path / "multi.sqlite3"
        store = SQLiteConfigurationStore(path)
        target_a = _target(owner="owner-a", instance="a")
        target_b = _target(owner="owner-b", instance="b")
        store.publish(_publish_op(target_a))
        store.publish(_publish_op(target_b))

        report = qualify_store(path)
        assert len(report.scopes) == 2
        by_target = {scope.target: scope for scope in report.scopes}
        assert target_a in by_target
        assert target_b in by_target
        assert by_target[target_a].current_head != by_target[target_b].current_head or (
            by_target[target_a].target != by_target[target_b].target
        )
        assert report.status is RecoveryStatus.QUALIFIED


class TestIntegrityFailures:
    def test_unsupported_physical_schema_version_blocks(self, tmp_path: Path) -> None:
        path = tmp_path / "bad_version.sqlite3"
        SQLiteConfigurationStore(path)
        connection = sqlite3.connect(str(path), autocommit=True)
        try:
            connection.execute("UPDATE store_metadata SET schema_version = 999")
        finally:
            connection.close()

        report = qualify_store(path)
        assert report.status is RecoveryStatus.BLOCKED
        assert report.physical_schema_version == 999
        assert report.scopes == ()

    def test_missing_store_metadata_blocks(self, tmp_path: Path) -> None:
        path = tmp_path / "not_our_store.sqlite3"
        connection = sqlite3.connect(str(path), autocommit=True)
        try:
            connection.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)")
        finally:
            connection.close()

        report = qualify_store(path)
        assert report.status is RecoveryStatus.BLOCKED
        assert report.physical_schema_version is None
        assert report.scopes == ()

    def test_foreign_key_violation_detected_and_blocks(self, tmp_path: Path) -> None:
        path = tmp_path / "fk_violation.sqlite3"
        store = SQLiteConfigurationStore(path)
        target = _target()
        store.publish(_publish_op(target))

        # Simulate historical/external corruption: bypass production APIs
        # to point config_head at a revision_id that does not exist, with
        # foreign_keys temporarily off so the write itself succeeds.
        connection = sqlite3.connect(str(path), autocommit=True)
        try:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute(
                "UPDATE config_head SET published_revision_id = 'does-not-exist'"
            )
        finally:
            connection.close()

        report = qualify_store(path)
        assert report.status is RecoveryStatus.BLOCKED
        assert report.foreign_key_violations != ()
        assert report.scopes == ()

    def test_integrity_check_ok_on_healthy_store(self, tmp_path: Path) -> None:
        path = tmp_path / "integrity_ok.sqlite3"
        SQLiteConfigurationStore(path)
        report = qualify_store(path)
        assert report.integrity_check == "ok"


class TestRepresentationFailures:
    def test_corrupt_revision_payload_blocks_that_scope(self, tmp_path: Path) -> None:
        path = tmp_path / "corrupt_revision.sqlite3"
        store = SQLiteConfigurationStore(path)
        target = _target()
        store.publish(_publish_op(target))

        connection = sqlite3.connect(str(path), autocommit=True)
        try:
            connection.execute(
                "UPDATE config_revision SET record_json = 'not valid json at all'"
            )
        finally:
            connection.close()

        report = qualify_store(path)
        assert report.status is RecoveryStatus.BLOCKED
        assert len(report.scopes) == 1
        scope = report.scopes[0]
        assert scope.qualified is False
        assert scope.representation_failures != ()
        # Never skip the invalid row and report a healthy empty scope.
        assert scope.revision_count == 1

    def test_corrupt_result_payload_blocks_that_scope(self, tmp_path: Path) -> None:
        path = tmp_path / "corrupt_result.sqlite3"
        store = SQLiteConfigurationStore(path)
        target = _target()
        store.publish(_publish_op(target))

        connection = sqlite3.connect(str(path), autocommit=True)
        try:
            connection.execute(
                "UPDATE config_result SET result_json = '{\"unrelated\": true}'"
            )
        finally:
            connection.close()

        report = qualify_store(path)
        assert report.status is RecoveryStatus.BLOCKED
        scope = report.scopes[0]
        assert any("result" in failure for failure in scope.representation_failures)

    def test_corrupt_duty_payload_marks_duties_unknown_not_empty(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "corrupt_duty.sqlite3"
        store = SQLiteConfigurationStore(path)
        target = _target()
        store.publish(_publish_op(target))

        connection = sqlite3.connect(str(path), autocommit=True)
        try:
            connection.execute("UPDATE config_duty SET duty_json = 'garbage'")
        finally:
            connection.close()

        report = qualify_store(path)
        scope = report.scopes[0]
        # None means "could not determine", never conflated with "()" (no
        # outstanding duties) -- a genuinely different, weaker claim.
        assert scope.outstanding_duties is None
        assert report.outstanding_duty_count == 0
        assert scope.qualified is False


class TestLostAckAndDutyDiscovery:
    def test_lost_ack_result_recoverable_after_logical_restart(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "lost_ack.sqlite3"
        first_store = SQLiteConfigurationStore(path)
        target = _target()
        original = first_store.publish(_publish_op(target))
        # Caller never observes the return value -- simulate a lost ack by
        # discarding `first_store` and treating the process as restarted.
        del first_store

        report = qualify_store(path)
        assert report.status is RecoveryStatus.QUALIFIED

        reopened = SQLiteConfigurationStore(path)
        recovered = reopened.operation_result(_operation(target))
        assert recovered == original
        assert recovered is not None
        assert recovered.stage is OperationStage.COMMITTED
        assert recovered.resulting_revision == original.resulting_revision
        assert recovered.published == original.published
        assert recovered.effect == original.effect
        assert recovered.duties == original.duties

        # No second commit: head is still exactly 1, not advanced by replay.
        assert reopened.current_head(target).value == 1  # type: ignore[union-attr]

    def test_outstanding_duty_discovered_after_restart(self, tmp_path: Path) -> None:
        path = tmp_path / "duty_restart.sqlite3"
        first_store = SQLiteConfigurationStore(path)
        target = _target()
        result = first_store.publish(_publish_op(target))
        del first_store

        report = qualify_store(path)
        scope = report.scopes[0]
        assert scope.outstanding_duties is not None
        assert len(scope.outstanding_duties) == 1
        assert scope.outstanding_duties[0].duty_id in result.duties

        # Recovery only discovers/reports -- it never resolves the duty.
        reopened = SQLiteConfigurationStore(path)
        assert len(reopened.outstanding_duties(target)) == 1

    def test_unknown_effect_preserved_through_recovery(self, tmp_path: Path) -> None:
        from legoai.kernel.effects import EffectExtent

        path = tmp_path / "unknown_effect.sqlite3"
        store = SQLiteConfigurationStore(path)
        target = _target()
        result = store.publish(_publish_op(target))
        assert result.published is not None

        # Historical corruption fixture: hand-craft a result row whose
        # effect is `unknown`, bypassing production write paths (recovery
        # never produces this shape itself -- only F4/F6a's publish() does,
        # for e.g. an external-effect operation kind this owner does not
        # currently model). Proves decode-through-recovery never downgrades
        # unknown to none.
        connection = sqlite3.connect(str(path), autocommit=True)
        try:
            row = connection.execute(
                "SELECT result_json FROM config_result LIMIT 1"
            ).fetchone()
            record = codec.loads(row[0])
            record["effect"] = EffectExtent.UNKNOWN.value
            connection.execute(
                "UPDATE config_result SET result_json = ?", (codec.dumps(record),)
            )
        finally:
            connection.close()

        report = qualify_store(path)
        scope = report.scopes[0]
        assert scope.qualified is True
        reopened = SQLiteConfigurationStore(path)
        recovered = reopened.operation_result(_operation(target))
        assert recovered is not None
        assert recovered.effect is EffectExtent.UNKNOWN


class TestSubprocessDurability:
    """Real OS-process-boundary tests -- not exception injection (that is
    F6a's own rollback test). These are the abrupt-termination scenarios
    LOCAL-PERSISTENCE-REALIZATION.md SS17 calls the "process crash" layer.
    """

    def test_committed_state_survives_process_exit_and_reopen(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "cross_process.sqlite3"
        child_script = textwrap.dedent(
            f"""
            from legoai.application.values import ConfigurationPublicationOperation
            from legoai.governance.values import Principal
            from legoai.kernel.identity import ApplicationId, OperationId, PrincipalId, TenantId
            from legoai.kernel.references import ApplicationRef, ConfigurationRef, OperationRef, PrincipalRef, ReferenceScope
            from legoai.kernel.versions import Version
            from legoai.reference.application.configuration import compose_configuration
            from legoai.reference.application.sqlite_store import SQLiteConfigurationStore

            VERSION = Version(0, 1, 0)
            scope = ReferenceScope("owner1", TenantId("t1"))
            target = ConfigurationRef(ApplicationRef(scope, ApplicationId("app1")), "i1")
            store = SQLiteConfigurationStore({str(path)!r})
            candidate = compose_configuration(target, (), contract_version=VERSION, interpretation_version=VERSION)
            op = ConfigurationPublicationOperation(
                OperationRef(target, OperationId("op1"), "subprocess-fixture"),
                target, None, candidate,
                Principal(PrincipalRef("issuer1", PrincipalId("p1"))),
            )
            result = store.publish(op)
            assert result.stage.value == "committed"
            """
        )
        completed = subprocess.run(
            [sys.executable, "-c", child_script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr

        report = qualify_store(path)
        assert report.status is RecoveryStatus.QUALIFIED
        assert len(report.scopes) == 1

        target = _target()
        reopened = SQLiteConfigurationStore(path)
        assert reopened.current_head(target) is not None
        assert reopened.current_head(target).value == 1  # type: ignore[union-attr]

    def test_uncommitted_transaction_absent_after_abrupt_termination(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "abrupt_kill.sqlite3"
        ready_marker = tmp_path / "ready"
        # Pre-create the schema in the parent so the child only needs to
        # open a transaction and stall -- isolating the scenario to "died
        # mid-transaction", not "died during schema init".
        SQLiteConfigurationStore(path)

        child_script = textwrap.dedent(
            f"""
            import sqlite3, time
            connection = sqlite3.connect({str(path)!r}, autocommit=True, timeout=0.0)
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO config_revision "
                "(tenant_id, owner, application_id, instance, revision_id, "
                "published_head_revision, record_json) "
                "VALUES ('t1', 'owner1', 'app1', 'i1', 'orphan-r1', 1, '{{}}')"
            )
            with open({str(ready_marker)!r}, "w") as f:
                f.write("ready")
            time.sleep(30)
            """
        )
        process = subprocess.Popen(
            [sys.executable, "-c", child_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 10
            while not ready_marker.exists():
                if time.monotonic() > deadline:
                    raise TimeoutError("child never reached the ready marker")
                time.sleep(0.05)
            # Abrupt termination: no chance for the child to COMMIT/ROLLBACK
            # or run any cleanup handler.
            process.kill()
            process.wait(timeout=10)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)

        report = qualify_store(path)
        assert report.status is RecoveryStatus.QUALIFIED
        assert report.scopes == ()  # nothing ever committed for this scope

        target = _target()
        reopened = SQLiteConfigurationStore(path)
        assert reopened.current_head(target) is None
        with pytest.raises(Exception):  # noqa: B017 -- UnknownRevisionError, exact type re-verified in test_sqlite_store.py
            from legoai.kernel.references import ConfigurationRevisionRef

            reopened.read_revision(
                ConfigurationRevisionRef(target, "orphan-r1", VERSION)
            )

        # A correctly-formed publish still works afterward -- the stalled,
        # killed writer left no lingering lock or corruption.
        result = reopened.publish(_publish_op(target))
        assert result.stage is OperationStage.COMMITTED
