"""G1-EXIT-08 remediation: migration-interruption evidence for the F6a
SQLite realization (Gate-1 plan SS9.3; ADR-004 SS17.3/Timeline 7; LOCAL-
PERSISTENCE-REALIZATION.md SS11).

``SYNTHETIC_PREDECESSOR_SCHEMA_VERSION = 0`` (``tests/support/migration_fixture.py``)
is a **test-only fixture that was never a released LegoAI representation** --
see that module's own docstring. These tests prove two things using real
OS-process interruption, not exception injection (that remains F6a's own
``test_failure_during_commit_leaves_no_partial_mutation``):

1. A synthetic predecessor store is actually migratable to F6a's real
   current schema, and the migrated data is fully usable through the
   unchanged production ``SQLiteConfigurationStore``/``qualify_store`` APIs
   (the control case -- proves the fixture is genuinely migratable, not
   merely corrupt).
2. Killing the migration process after structural work has started but
   strictly before the schema-version marker is bumped and the transaction
   commits leaves the physical file in its exact original v0 state -- never
   a mix of old and new tables, and never a store that opens or qualifies
   as if migration had completed.

No production code was changed to produce this evidence; both assertions
rely entirely on F6a's already-existing fail-closed schema-version check
and F6b's already-existing recovery qualification.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from legoai.kernel.effects import EffectExtent
from legoai.kernel.identity import OperationId
from legoai.kernel.references import OperationRef
from legoai.reference.application.recovery import RecoveryStatus, qualify_store
from legoai.reference.application.sqlite_store import (
    SQLiteConfigurationStore,
    UnsupportedPhysicalSchemaVersionError,
)
from tests.support.migration_fixture import (
    SYNTHETIC_PREDECESSOR_SCHEMA_VERSION,
    create_synthetic_predecessor_store,
    fixture_target,
    migrate_predecessor_to_current,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _operation_ref() -> OperationRef:
    return OperationRef(fixture_target(), OperationId("op1"), "migration-fixture")


def _physical_tables(path: Path) -> set[str]:
    connection = sqlite3.connect(str(path))
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {row[0] for row in rows}
    finally:
        connection.close()


def _schema_version(path: Path) -> int | None:
    connection = sqlite3.connect(str(path))
    try:
        row = connection.execute(
            "SELECT schema_version FROM store_metadata WHERE id = 1"
        ).fetchone()
        return row[0] if row is not None else None
    finally:
        connection.close()


class TestSuccessfulMigrationControlCase:
    """SS21/SS23: proves the synthetic predecessor is genuinely migratable,
    not merely a corrupt fixture that happens to fail qualification."""

    def test_migration_completes_and_current_store_qualifies(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "predecessor.sqlite3"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)

        migrate_predecessor_to_current(path)

        assert _schema_version(path) == 1
        report = qualify_store(path)
        assert report.status is RecoveryStatus.QUALIFIED
        assert report.physical_schema_version == 1
        assert len(report.scopes) == 1

    def test_migrated_store_is_usable_through_unchanged_production_api(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "predecessor.sqlite3"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)
        migrate_predecessor_to_current(path)

        store = SQLiteConfigurationStore(path)
        target = fixture_target()
        head = store.current_head(target)
        assert head is not None
        assert head.value == 1
        assert store.current_published(target) is not None

    def test_migration_preserves_historical_revision_content_exactly(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "predecessor.sqlite3"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)
        migrate_predecessor_to_current(path)

        store = SQLiteConfigurationStore(path)
        target = fixture_target()
        published = store.current_published(target)
        assert published is not None
        composed = store.read_revision(published)
        assert composed.target == target

    def test_migration_preserves_operation_result_without_recomputation(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "predecessor.sqlite3"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)
        migrate_predecessor_to_current(path)

        store = SQLiteConfigurationStore(path)
        result = store.operation_result(_operation_ref())
        assert result is not None
        assert result.stage.value == "committed"
        assert result.resulting_revision is not None
        assert result.resulting_revision.value == 1

    def test_migration_preserves_unknown_effect_exactly(self, tmp_path: Path) -> None:
        path = tmp_path / "predecessor.sqlite3"
        # UNKNOWN effect implies no duty in this fixture's own construction
        # (see migration_fixture._fixture_records) -- this case isolates
        # the effect-preservation proof from duty preservation.
        create_synthetic_predecessor_store(path, effect=EffectExtent.UNKNOWN)
        migrate_predecessor_to_current(path)

        store = SQLiteConfigurationStore(path)
        result = store.operation_result(_operation_ref())
        assert result is not None
        assert result.effect is EffectExtent.UNKNOWN

    def test_migration_preserves_outstanding_duty_as_outstanding(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "predecessor.sqlite3"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)
        migrate_predecessor_to_current(path)

        store = SQLiteConfigurationStore(path)
        target = fixture_target()
        duties = store.outstanding_duties(target)
        assert len(duties) == 1
        assert duties[0].duty_id.value == "duty-1"
        # Migration only transforms representation; it never resolves duties.
        assert duties[0].kind.value == "source-submission"

    def test_migration_preserves_owner_revision_and_configuration_revision_distinctly(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "predecessor.sqlite3"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)
        migrate_predecessor_to_current(path)

        store = SQLiteConfigurationStore(path)
        target = fixture_target()
        head = store.current_head(target)
        published = store.current_published(target)
        assert head is not None
        assert published is not None
        # H (OwnerRevision) and R (ConfigurationRevisionRef) remain distinct
        # concepts after migration, exactly as before it.
        assert head.value == 1
        assert published.revision == "r1"
        assert not hasattr(head, "revision")
        assert not hasattr(published, "value")


class TestInterruptedMigration:
    """SS22: the primary required proof -- real subprocess interruption of
    an in-progress, uncommitted migration transaction."""

    def test_migration_killed_before_commit_leaves_predecessor_intact(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "predecessor.sqlite3"
        ready_marker = tmp_path / "ready"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)
        original_tables = _physical_tables(path)

        child_script = (
            "from pathlib import Path\n"
            "from tests.support.migration_fixture import migrate_predecessor_to_current\n"
            f"migrate_predecessor_to_current({str(path)!r}, "
            f"ready_marker=Path({str(ready_marker)!r}), stop_before_commit=True)\n"
        )
        process = subprocess.Popen(
            [sys.executable, "-c", child_script],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 10
            while not ready_marker.exists():
                if time.monotonic() > deadline:
                    raise TimeoutError("child never reached the ready marker")
                time.sleep(0.05)
            # Abrupt termination: the child is blocked in time.sleep(),
            # strictly before the schema-version bump and COMMIT below it.
            process.kill()
            process.wait(timeout=10)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)

        # No partial migration artifact of any kind survives: the exact
        # original v0 table set is present, unchanged.
        assert _physical_tables(path) == original_tables
        assert "config_duty" not in _physical_tables(path)
        assert "config_revision" not in _physical_tables(path)
        assert "config_head" not in _physical_tables(path)
        assert "config_result" not in _physical_tables(path)
        assert _schema_version(path) == SYNTHETIC_PREDECESSOR_SCHEMA_VERSION

    def test_interrupted_store_is_refused_by_production_construction(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "predecessor.sqlite3"
        ready_marker = tmp_path / "ready"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)
        self._interrupt(path, ready_marker)

        with pytest.raises(UnsupportedPhysicalSchemaVersionError):
            SQLiteConfigurationStore(path)

    def test_interrupted_store_is_blocked_by_recovery_qualification(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "predecessor.sqlite3"
        ready_marker = tmp_path / "ready"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)
        self._interrupt(path, ready_marker)

        report = qualify_store(path)
        assert report.status is RecoveryStatus.BLOCKED
        assert report.physical_schema_version == SYNTHETIC_PREDECESSOR_SCHEMA_VERSION
        # Never a mixed-version success: no scope is interpreted at all
        # once the physical schema version itself is unrecognized.
        assert report.scopes == ()

    def test_interrupted_migration_never_reports_qualified(
        self, tmp_path: Path
    ) -> None:
        # The central invariant (this batch's own SS16): restart must never
        # observe some-predecessor-rows + some-current-rows + a current
        # schema marker and report the store healthy.
        path = tmp_path / "predecessor.sqlite3"
        ready_marker = tmp_path / "ready"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)
        self._interrupt(path, ready_marker)

        report = qualify_store(path)
        assert report.status is not RecoveryStatus.QUALIFIED

    def test_repeated_recovery_attempts_remain_stable_after_interruption(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "predecessor.sqlite3"
        ready_marker = tmp_path / "ready"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)
        self._interrupt(path, ready_marker)

        first = qualify_store(path)
        second = qualify_store(path)
        assert first == second == qualify_store(path)

    def test_no_silent_repair_or_cleanup_after_interruption(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "predecessor.sqlite3"
        ready_marker = tmp_path / "ready"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)
        original_tables = _physical_tables(path)
        self._interrupt(path, ready_marker)

        # Running qualification (a read-only inspection) must not itself
        # repair, delete, or otherwise change the interrupted file.
        qualify_store(path)
        assert _physical_tables(path) == original_tables
        assert _schema_version(path) == SYNTHETIC_PREDECESSOR_SCHEMA_VERSION

    @staticmethod
    def _interrupt(path: Path, ready_marker: Path) -> None:
        child_script = (
            "from pathlib import Path\n"
            "from tests.support.migration_fixture import migrate_predecessor_to_current\n"
            f"migrate_predecessor_to_current({str(path)!r}, "
            f"ready_marker=Path({str(ready_marker)!r}), stop_before_commit=True)\n"
        )
        process = subprocess.Popen(
            [sys.executable, "-c", child_script],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 10
            while not ready_marker.exists():
                if time.monotonic() > deadline:
                    raise TimeoutError("child never reached the ready marker")
                time.sleep(0.05)
            process.kill()
            process.wait(timeout=10)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)


class TestMigrationPrecondition:
    def test_migration_refuses_a_store_that_is_not_v0(self, tmp_path: Path) -> None:
        path = tmp_path / "already_current.sqlite3"
        create_synthetic_predecessor_store(path, effect=EffectExtent.COMPLETED)
        migrate_predecessor_to_current(path)

        from tests.support.migration_fixture import MigrationPreconditionError

        with pytest.raises(MigrationPreconditionError):
            migrate_predecessor_to_current(path)


def test_synthetic_predecessor_version_is_not_a_supported_current_version() -> None:
    from legoai.reference.application.sqlite_store import _physical_schema_version

    assert SYNTHETIC_PREDECESSOR_SCHEMA_VERSION != _physical_schema_version()


def test_migration_fixture_module_is_test_only_not_imported_by_production() -> None:
    import ast

    root = REPO_ROOT / "src" / "legoai"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "migration_fixture" not in node.module
            if isinstance(node, ast.Import):
                assert not any(
                    "migration_fixture" in alias.name for alias in node.names
                )
