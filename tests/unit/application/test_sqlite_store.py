"""F6a: SQLite-realization-specific tests beyond the reusable Port contract
suite in ``tests/contract/test_configuration_store.py``.

These exercise SQL/transaction/durability mechanics that the Port contract
deliberately does not (and should not) know about: schema initialization,
transaction rollback under injected failure, restart/file-reopen durability,
uniqueness/foreign-key constraints, corrupt-payload handling, physical
schema-version behavior, and real concurrent-writer contention.
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Any

import pytest

from legoai.application.ports import UnknownRevisionError
from legoai.application.values import ConfigurationPublicationOperation, OperationStage
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
from legoai.reference.application import codec
from legoai.reference.application.configuration import compose_configuration
from legoai.reference.application.sqlite_store import (
    SQLiteConfigurationStore,
    StorageUnavailableError,
    UnsupportedPhysicalSchemaVersionError,
)
from tests.support.configuration_store import InMemoryConfigurationStore

VERSION = Version(0, 1, 0)


def _target(
    tenant: str = "t1", owner: str = "owner1", app: str = "app1", instance: str = "i1"
) -> ConfigurationRef:
    scope = ReferenceScope(owner, TenantId(tenant))
    return ConfigurationRef(ApplicationRef(scope, ApplicationId(app)), instance)


def _operation(target: ConfigurationRef, op_id: str = "op1") -> OperationRef:
    return OperationRef(target, OperationId(op_id), "sqlite-fixture")


def _principal(pid: str = "p1") -> Principal:
    return Principal(PrincipalRef("issuer1", PrincipalId(pid)))


def _publish_op(
    target: ConfigurationRef, op_id: str = "op1", expected: OwnerRevision | None = None
) -> ConfigurationPublicationOperation:
    candidate = compose_configuration(
        target, (), contract_version=VERSION, interpretation_version=VERSION
    )
    return ConfigurationPublicationOperation(
        _operation(target, op_id), target, expected, candidate, _principal()
    )


# --------------------------------------------------------------------------
# Schema initialization
# --------------------------------------------------------------------------


def test_schema_initialization_is_safe_on_new_database(tmp_path: Path) -> None:
    path = tmp_path / "new.sqlite3"
    assert not path.exists()
    store = SQLiteConfigurationStore(path)
    assert path.exists()
    target = _target()
    assert store.current_head(target) is None


def test_schema_initialization_is_idempotent_on_existing_database(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reopen.sqlite3"
    SQLiteConfigurationStore(path)
    # Reopening an already-initialized store must not fail or reset state.
    store_again = SQLiteConfigurationStore(path)
    target = _target()
    store_again.publish(_publish_op(target))
    assert store_again.current_head(target) is not None


def test_unsupported_physical_schema_version_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "bad_version.sqlite3"
    SQLiteConfigurationStore(path)
    connection = sqlite3.connect(str(path), autocommit=True)
    try:
        connection.execute("UPDATE store_metadata SET schema_version = 999")
    finally:
        connection.close()
    with pytest.raises(UnsupportedPhysicalSchemaVersionError):
        SQLiteConfigurationStore(path)


# --------------------------------------------------------------------------
# Restart / file-reopen durability (not F6b recovery orchestration)
# --------------------------------------------------------------------------


def test_records_survive_reopening_the_same_file(tmp_path: Path) -> None:
    path = tmp_path / "durable.sqlite3"
    target = _target()
    first_store = SQLiteConfigurationStore(path)
    result = first_store.publish(_publish_op(target))
    del first_store  # simulate closing/discarding this process's handle

    assert result.published is not None
    reopened = SQLiteConfigurationStore(path)
    assert reopened.current_head(target) == result.resulting_revision
    assert reopened.current_published(target) == result.published
    assert reopened.operation_result(_operation(target)) == result
    assert reopened.read_revision(result.published) is not None
    duties = reopened.outstanding_duties(target)
    assert len(duties) == 1
    assert duties[0].duty_id in result.duties


# --------------------------------------------------------------------------
# Historical immutability across subsequent publishes
# --------------------------------------------------------------------------


def test_historical_revision_immutable_across_later_publish(tmp_path: Path) -> None:
    path = tmp_path / "immutable.sqlite3"
    store = SQLiteConfigurationStore(path)
    target = _target()
    first = store.publish(_publish_op(target, "op1"))
    head = store.current_head(target)
    store.publish(_publish_op(target, "op2", expected=head))
    assert first.published is not None
    reread = store.read_revision(first.published)
    original = codec.decode_revision_content(
        codec.loads(codec.dumps(codec.encode_revision_content(reread)))
    )
    assert reread == original
    assert store.read_revision(first.published) == reread


# --------------------------------------------------------------------------
# Transaction rollback under injected failure: no partial mutation visible
# --------------------------------------------------------------------------


def test_failure_during_commit_leaves_no_partial_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # sqlite3.Connection is an immutable C type -- its methods cannot be
    # monkeypatched directly. Instead, patch the module-level `connect`
    # factory the store calls, wrapping the real connection so exactly one
    # statement fails partway through the transaction.
    path = tmp_path / "rollback.sqlite3"
    store = SQLiteConfigurationStore(path)
    target = _target()

    real_connect = sqlite3.connect

    class _FailingConnection:
        def __init__(self, real: sqlite3.Connection) -> None:
            self._real = real

        def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
            if "INSERT INTO config_duty" in sql:
                raise sqlite3.OperationalError("injected failure before commit")
            return self._real.execute(sql, *args)  # type: ignore[arg-type]

        def __getattr__(self, name: str) -> object:
            return getattr(self._real, name)

    def _connect(*args: Any, **kwargs: Any) -> _FailingConnection:
        return _FailingConnection(real_connect(*args, **kwargs))

    monkeypatch.setattr(sqlite3, "connect", _connect)
    with pytest.raises(StorageUnavailableError):
        store.publish(_publish_op(target))
    monkeypatch.undo()

    # Nothing from the failed attempt is visible: no head, no history, no
    # result, no duty -- the whole owner-local set is absent, not partial.
    assert store.current_head(target) is None
    assert store.current_published(target) is None
    assert store.operation_result(_operation(target)) is None
    assert store.outstanding_duties(target) == ()

    # A fresh, correctly-formed publish still succeeds afterward.
    result = store.publish(_publish_op(target))
    assert result.stage is OperationStage.COMMITTED


# --------------------------------------------------------------------------
# Uniqueness / foreign-key behavior
# --------------------------------------------------------------------------


def test_foreign_keys_are_actually_enabled(tmp_path: Path) -> None:
    path = tmp_path / "fk.sqlite3"
    SQLiteConfigurationStore(path)
    connection = sqlite3.connect(str(path), autocommit=True)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO config_head "
                "(tenant_id, owner, application_id, instance, head_revision, "
                "published_revision_id) VALUES ('t', 'o', 'a', 'i', 1, 'missing-r')"
            )
    finally:
        connection.close()


def test_revision_uniqueness_constraint_enforced(tmp_path: Path) -> None:
    path = tmp_path / "unique.sqlite3"
    SQLiteConfigurationStore(path)
    connection = sqlite3.connect(str(path), autocommit=True)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO config_revision "
            "(tenant_id, owner, application_id, instance, revision_id, "
            "published_head_revision, record_json) "
            "VALUES ('t', 'o', 'a', 'i', 'r1', 1, '{}')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO config_revision "
                "(tenant_id, owner, application_id, instance, revision_id, "
                "published_head_revision, record_json) "
                "VALUES ('t', 'o', 'a', 'i', 'r2', 1, '{}')"
            )
    finally:
        connection.close()


# --------------------------------------------------------------------------
# Corrupt payload handling: surface the F5 failure, never skip/default
# --------------------------------------------------------------------------


def test_corrupt_revision_payload_fails_visibly_not_silently(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.sqlite3"
    store = SQLiteConfigurationStore(path)
    target = _target()
    result = store.publish(_publish_op(target))
    assert result.published is not None

    connection = sqlite3.connect(str(path), autocommit=True)
    try:
        connection.execute(
            "UPDATE config_revision SET record_json = 'not valid json at all'"
        )
    finally:
        connection.close()

    with pytest.raises(codec.RepresentationError):
        store.read_revision(result.published)
    with pytest.raises(codec.RepresentationError):
        store.current_published(target)


def test_corrupt_result_payload_fails_visibly(tmp_path: Path) -> None:
    path = tmp_path / "corrupt_result.sqlite3"
    store = SQLiteConfigurationStore(path)
    target = _target()
    store.publish(_publish_op(target))

    connection = sqlite3.connect(str(path), autocommit=True)
    try:
        connection.execute("UPDATE config_result SET result_json = '{\"bad\": true}'")
    finally:
        connection.close()

    with pytest.raises(codec.RepresentationError):
        store.operation_result(_operation(target))


def test_missing_historical_revision_raises_unknown_revision_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "unknown.sqlite3"
    store = SQLiteConfigurationStore(path)
    target = _target()
    store.publish(_publish_op(target))
    bad_ref = ConfigurationRevisionRef(target, "does-not-exist", VERSION)
    with pytest.raises(UnknownRevisionError):
        store.read_revision(bad_ref)


# --------------------------------------------------------------------------
# Real concurrent-writer contention (fail-fast, no retry engine)
# --------------------------------------------------------------------------


def test_concurrent_writer_is_rejected_fail_fast(tmp_path: Path) -> None:
    path = tmp_path / "contention.sqlite3"
    store = SQLiteConfigurationStore(path)
    target = _target()
    store.publish(_publish_op(target, "op1"))
    head = store.current_head(target)

    # Hold the write lock open on an independent raw connection.
    blocker = sqlite3.connect(str(path), autocommit=True, timeout=0.0)
    blocker.execute("PRAGMA busy_timeout = 0")
    blocker.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(StorageUnavailableError):
            store.publish(_publish_op(target, "op2", expected=head))
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()

    # After the blocker releases, a correctly-formed publish succeeds, and
    # the earlier contention left no partial trace.
    result = store.publish(_publish_op(target, "op2", expected=head))
    assert result.stage is OperationStage.COMMITTED
    assert store.operation_result(_operation(target, "op2")) == result


def test_two_writers_expecting_same_head_only_one_advances(tmp_path: Path) -> None:
    path = tmp_path / "two_writers.sqlite3"
    store = SQLiteConfigurationStore(path)
    target = _target()
    store.publish(_publish_op(target, "op1"))
    head = store.current_head(target)

    winner = store.publish(_publish_op(target, "op2", expected=head))
    loser = store.publish(_publish_op(target, "op3", expected=head))

    assert winner.stage is OperationStage.COMMITTED
    assert loser.stage is OperationStage.REJECTED
    assert loser.error is not None


# --------------------------------------------------------------------------
# No test-fake fallback in production store
# --------------------------------------------------------------------------


def test_sqlite_store_never_falls_back_to_the_in_memory_fake() -> None:
    import ast

    import legoai.reference.application.sqlite_store as module

    assert module.__file__ is not None
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    assert "InMemoryConfigurationStore" not in names
    assert "tests" not in {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }


def test_sqlite_store_is_not_the_fake_type(tmp_path: Path) -> None:
    store = SQLiteConfigurationStore(tmp_path / "distinct.sqlite3")
    assert not isinstance(store, InMemoryConfigurationStore)


# --------------------------------------------------------------------------
# Multi-owner isolation (SQLite-specific: shared physical file)
# --------------------------------------------------------------------------


def test_connect_failure_at_construction_raises_storage_unavailable(
    tmp_path: Path,
) -> None:
    # A parent directory that does not exist makes sqlite3.connect fail
    # immediately -- proves the connect-failure path is translated to the
    # store's own error surface rather than leaking a raw sqlite3 exception.
    unreachable = tmp_path / "does-not-exist" / "nested" / "store.sqlite3"
    with pytest.raises(StorageUnavailableError):
        SQLiteConfigurationStore(unreachable)


def test_operation_result_rejects_operation_scoped_to_application_ref(
    tmp_path: Path,
) -> None:
    from legoai.kernel.references import ApplicationRef

    store = SQLiteConfigurationStore(tmp_path / "wrong_subject.sqlite3")
    target = _target()
    wrong_subject_operation = OperationRef(
        target.application, OperationId("op1"), "sqlite-fixture"
    )
    assert isinstance(wrong_subject_operation.subject, ApplicationRef)
    with pytest.raises(TypeError):
        store.operation_result(wrong_subject_operation)


def test_multi_owner_isolation_within_one_physical_database(tmp_path: Path) -> None:
    path = tmp_path / "multi_owner.sqlite3"
    store = SQLiteConfigurationStore(path)
    target_a = _target(owner="owner-a", instance=uuid.uuid4().hex)
    target_b = _target(owner="owner-b", instance=uuid.uuid4().hex)

    result_a = store.publish(_publish_op(target_a))
    assert store.current_head(target_b) is None
    assert store.current_published(target_b) is None
    assert store.outstanding_duties(target_b) == ()
    assert store.current_head(target_a) == result_a.resulting_revision
