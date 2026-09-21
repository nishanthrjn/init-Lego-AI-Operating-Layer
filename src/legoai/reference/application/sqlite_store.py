"""F6a: SQLite realization of ``ConfigurationStorePort`` (LOCAL-PERSISTENCE-
REALIZATION.md; ADR-004/008/009).

This module implements the existing F4 Port and reuses the existing F5 codecs
unchanged. It does not redefine either. Layering on every durable write/read:

    semantic value -> F5 codec -> versioned JSON text -> SQLite TEXT column

and the reverse on reads. No pickle, no Python-object storage, no
SQLite-specific semantic encoding of domain values.

Connection ownership
---------------------
One fresh synchronous connection per Port operation call (LOCAL-PERSISTENCE-
REALIZATION.md SS5): open, set required PRAGMAs, do bounded work, close. No
ambient/global singleton connection is held by this store.

Transaction discipline
------------------------
``publish`` is the only mutating operation. It opens one ``BEGIN IMMEDIATE``
transaction, performs the idempotent-replay check, the expected-revision
guard, and (on success) every required insert/update, then issues one
``COMMIT``. All required records -- new head, published pointer, immutable
revision content, retained result, and the new outstanding duty -- become
durable together or not at all; this module never commits them individually.

PRAGMAs applied (LOCAL-PERSISTENCE-REALIZATION.md SS4.1), on every connection:

* ``foreign_keys = ON`` -- composite scope FKs actually enforced.
* ``journal_mode = DELETE`` -- the accepted first engine choice, not WAL.
* ``synchronous = EXTRA`` -- conservative commit-adjacent durability.
* ``busy_timeout = 0`` -- fail-fast contention; no hidden internal retry.

Physical schema version vs. F5 RecordSchemaVersion vs. OwnerRevision vs.
ConfigurationRevisionRef are four distinct concerns (F6a task SS9) and are
never conflated: this module's ``_physical_schema_version()`` describes only
the SQL table shape below; the JSON payloads stored in ``record_json`` /
``descriptor_json`` / ``result_json`` / ``duty_json`` carry their own F5
``record_schema_version`` independently, validated by the F5 codec itself.

Error surface
-------------
* ``UnknownRevisionError`` (reused from ``legoai.application.ports``, never
  redefined) -- an exact historical revision is unavailable.
* ``legoai.reference.application.codec.RepresentationError`` (and subclasses)
  -- a stored JSON payload is corrupt or uses an unsupported record schema
  version. Surfaced unchanged; never silently skipped, never treated as an
  empty/healthy result.
* :class:`UnsupportedPhysicalSchemaVersionError` -- the SQL schema-version
  marker does not match this reader. Fails closed; no migration is attempted.
* :class:`StorageUnavailableError` -- a real SQLite operational failure
  (busy/locked, I/O, disk full) unrelated to domain semantics. Never
  reinterpreted as ``Conflict``, ``UnknownRevisionError``, or any other
  domain outcome, and never durably recorded as a publication result.
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from legoai.application.ports import UnknownRevisionError
from legoai.application.values import (
    ComposedConfiguration,
    ConfigurationPublicationOperation,
    ConfigurationPublicationResult,
    ConfigurationSourceSubmissionDuty,
    OperationStage,
)
from legoai.evidence.values import EvidenceRequirement
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorCause, ErrorDetail, Recoverability
from legoai.kernel.provenance import DutyId, DutyKind
from legoai.kernel.references import (
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    OwnerRevision,
)
from legoai.reference.application import codec


def _physical_schema_version() -> int:
    return 1


def _schema_statements() -> tuple[str, ...]:
    return (
        """
        CREATE TABLE IF NOT EXISTS store_metadata (
            id INTEGER NOT NULL,
            schema_version INTEGER NOT NULL,
            PRIMARY KEY (id),
            CHECK (id = 1),
            CHECK (schema_version >= 1)
        ) STRICT
        """,
        """
        CREATE TABLE IF NOT EXISTS config_revision (
            tenant_id TEXT NOT NULL,
            owner TEXT NOT NULL,
            application_id TEXT NOT NULL,
            instance TEXT NOT NULL,
            revision_id TEXT NOT NULL,
            published_head_revision INTEGER NOT NULL,
            record_json TEXT NOT NULL,
            PRIMARY KEY (tenant_id, owner, application_id, instance, revision_id),
            UNIQUE (tenant_id, owner, application_id, instance, published_head_revision),
            CHECK (published_head_revision >= 1)
        ) STRICT
        """,
        """
        CREATE TABLE IF NOT EXISTS config_head (
            tenant_id TEXT NOT NULL,
            owner TEXT NOT NULL,
            application_id TEXT NOT NULL,
            instance TEXT NOT NULL,
            head_revision INTEGER NOT NULL,
            published_revision_id TEXT NOT NULL,
            PRIMARY KEY (tenant_id, owner, application_id, instance),
            CHECK (head_revision >= 1),
            FOREIGN KEY (tenant_id, owner, application_id, instance, published_revision_id)
                REFERENCES config_revision
                    (tenant_id, owner, application_id, instance, revision_id)
        ) STRICT
        """,
        """
        CREATE TABLE IF NOT EXISTS config_result (
            tenant_id TEXT NOT NULL,
            owner TEXT NOT NULL,
            application_id TEXT NOT NULL,
            instance TEXT NOT NULL,
            operation_id TEXT NOT NULL,
            contract_identity TEXT NOT NULL,
            descriptor_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            PRIMARY KEY (tenant_id, owner, application_id, instance, operation_id)
        ) STRICT
        """,
        """
        CREATE TABLE IF NOT EXISTS config_duty (
            tenant_id TEXT NOT NULL,
            owner TEXT NOT NULL,
            application_id TEXT NOT NULL,
            instance TEXT NOT NULL,
            duty_id TEXT NOT NULL,
            duty_json TEXT NOT NULL,
            PRIMARY KEY (tenant_id, owner, application_id, instance, duty_id)
        ) STRICT
        """,
    )


class StorageUnavailableError(RuntimeError):
    """A real SQLite operational failure (busy/locked, I/O, disk full).

    Distinct from every domain outcome: never reinterpreted as ``Conflict``,
    ``UnknownRevisionError``, or any other semantic result, and never
    durably recorded as a publication result (LOCAL-PERSISTENCE-
    REALIZATION.md SS5's failure-response table).
    """


class UnsupportedPhysicalSchemaVersionError(RuntimeError):
    """The store's physical SQL schema-version marker does not match this
    reader. Fails closed; no migration is attempted by F6a."""


def _scope_columns(target: ConfigurationRef) -> tuple[str, str, str, str]:
    return (
        target.application.scope.tenant_id.value,
        target.application.scope.owner,
        target.application.application_id.value,
        target.instance,
    )


class SQLiteConfigurationStore:
    """Production ``ConfigurationStorePort`` realization backed by one local
    SQLite database file (LOCAL-PERSISTENCE-REALIZATION.md SS3, "Select A").

    Never falls back to ``InMemoryConfigurationStore`` on any error; that
    fake remains tests-only (Gate-1 plan SS9.1; this module's own SS38).
    """

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                self._path,
                timeout=0.0,
                check_same_thread=True,
                autocommit=True,
            )
        except sqlite3.Error as exc:
            raise StorageUnavailableError(f"cannot open store: {exc}") from exc
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.execute("PRAGMA synchronous = EXTRA")
            connection.execute("PRAGMA busy_timeout = 0")
        except sqlite3.Error as exc:
            connection.close()
            raise StorageUnavailableError(f"cannot configure store: {exc}") from exc
        return connection

    def _initialize_schema(self) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            try:
                current_version = _physical_schema_version()
                for statement in _schema_statements():
                    connection.execute(statement)
                row = connection.execute(
                    "SELECT schema_version FROM store_metadata WHERE id = 1"
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO store_metadata (id, schema_version) VALUES (1, ?)",
                        (current_version,),
                    )
                elif row[0] != current_version:
                    connection.execute("ROLLBACK")
                    raise UnsupportedPhysicalSchemaVersionError(
                        f"store schema_version {row[0]} is not supported "
                        f"(reader supports {current_version})"
                    )
                connection.execute("COMMIT")
            except sqlite3.Error as exc:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise StorageUnavailableError(
                    f"schema initialization failed: {exc}"
                ) from exc
        finally:
            connection.close()

    # -- reads --------------------------------------------------------

    def current_head(self, target: ConfigurationRef) -> OwnerRevision | None:
        connection = self._connect()
        try:
            scope = _scope_columns(target)
            try:
                row = connection.execute(
                    "SELECT head_revision FROM config_head "
                    "WHERE tenant_id = ? AND owner = ? AND application_id = ? "
                    "AND instance = ?",
                    scope,
                ).fetchone()
            except sqlite3.Error as exc:
                raise StorageUnavailableError(f"current_head failed: {exc}") from exc
        finally:
            connection.close()
        if row is None:
            return None
        return OwnerRevision(target, row[0])

    def current_published(
        self, target: ConfigurationRef
    ) -> ConfigurationRevisionRef | None:
        connection = self._connect()
        try:
            scope = _scope_columns(target)
            try:
                row = connection.execute(
                    "SELECT r.revision_id, r.record_json "
                    "FROM config_head h "
                    "JOIN config_revision r "
                    "ON h.tenant_id = r.tenant_id AND h.owner = r.owner "
                    "AND h.application_id = r.application_id "
                    "AND h.instance = r.instance "
                    "AND h.published_revision_id = r.revision_id "
                    "WHERE h.tenant_id = ? AND h.owner = ? "
                    "AND h.application_id = ? AND h.instance = ?",
                    scope,
                ).fetchone()
            except sqlite3.Error as exc:
                raise StorageUnavailableError(
                    f"current_published failed: {exc}"
                ) from exc
        finally:
            connection.close()
        if row is None:
            return None
        revision_id, record_json = row
        composed = codec.decode_revision_content(codec.loads(record_json))
        return ConfigurationRevisionRef(
            target, revision_id, composed.effective.contract_version
        )

    def read_revision(
        self, revision: ConfigurationRevisionRef
    ) -> ComposedConfiguration:
        target = revision.configuration
        connection = self._connect()
        try:
            scope = _scope_columns(target)
            try:
                row = connection.execute(
                    "SELECT record_json FROM config_revision "
                    "WHERE tenant_id = ? AND owner = ? AND application_id = ? "
                    "AND instance = ? AND revision_id = ?",
                    (*scope, revision.revision),
                ).fetchone()
            except sqlite3.Error as exc:
                raise StorageUnavailableError(f"read_revision failed: {exc}") from exc
        finally:
            connection.close()
        if row is None:
            raise UnknownRevisionError(
                "exact requested configuration revision is unavailable"
            )
        return codec.decode_revision_content(codec.loads(row[0]))

    def operation_result(
        self, operation: OperationRef
    ) -> ConfigurationPublicationResult | None:
        target = _operation_target(operation)
        connection = self._connect()
        try:
            scope = _scope_columns(target)
            try:
                row = connection.execute(
                    "SELECT result_json FROM config_result "
                    "WHERE tenant_id = ? AND owner = ? AND application_id = ? "
                    "AND instance = ? AND operation_id = ?",
                    (*scope, operation.operation_id.value),
                ).fetchone()
            except sqlite3.Error as exc:
                raise StorageUnavailableError(
                    f"operation_result failed: {exc}"
                ) from exc
        finally:
            connection.close()
        if row is None:
            return None
        return codec.decode_publication_result(codec.loads(row[0]))

    def outstanding_duties(
        self, target: ConfigurationRef
    ) -> tuple[ConfigurationSourceSubmissionDuty, ...]:
        connection = self._connect()
        try:
            scope = _scope_columns(target)
            try:
                rows = connection.execute(
                    "SELECT duty_json FROM config_duty "
                    "WHERE tenant_id = ? AND owner = ? AND application_id = ? "
                    "AND instance = ? ORDER BY duty_id",
                    scope,
                ).fetchall()
            except sqlite3.Error as exc:
                raise StorageUnavailableError(
                    f"outstanding_duties failed: {exc}"
                ) from exc
        finally:
            connection.close()
        return tuple(
            codec.decode_source_submission_duty(codec.loads(row[0])) for row in rows
        )

    # -- mutation -------------------------------------------------------

    def publish(
        self, operation: ConfigurationPublicationOperation
    ) -> ConfigurationPublicationResult:
        target = operation.target
        scope = _scope_columns(target)
        connection = self._connect()
        try:
            try:
                connection.execute("BEGIN IMMEDIATE")
            except sqlite3.Error as exc:
                raise StorageUnavailableError(f"publish contention: {exc}") from exc
            try:
                result = self._publish_within_transaction(
                    connection, operation, target, scope
                )
                connection.execute("COMMIT")
                return result
            except BaseException:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        finally:
            connection.close()

    def _publish_within_transaction(
        self,
        connection: sqlite3.Connection,
        operation: ConfigurationPublicationOperation,
        target: ConfigurationRef,
        scope: tuple[str, str, str, str],
    ) -> ConfigurationPublicationResult:
        try:
            existing_row = connection.execute(
                "SELECT result_json FROM config_result "
                "WHERE tenant_id = ? AND owner = ? AND application_id = ? "
                "AND instance = ? AND operation_id = ?",
                (*scope, operation.operation.operation_id.value),
            ).fetchone()
        except sqlite3.Error as exc:
            raise StorageUnavailableError(f"publish lookup failed: {exc}") from exc
        if existing_row is not None:
            # ADR-008 lost-acknowledgment recovery: the exact same logical
            # operation returns its original retained outcome, never a
            # second semantic commit (matches the F4 in-memory fake).
            return codec.decode_publication_result(codec.loads(existing_row[0]))

        try:
            head_row = connection.execute(
                "SELECT head_revision FROM config_head "
                "WHERE tenant_id = ? AND owner = ? AND application_id = ? "
                "AND instance = ?",
                scope,
            ).fetchone()
        except sqlite3.Error as exc:
            raise StorageUnavailableError(f"publish head read failed: {exc}") from exc
        current_head = (
            OwnerRevision(target, head_row[0]) if head_row is not None else None
        )

        if current_head != operation.expected_revision:
            return self._insert_rejected_result(connection, operation, scope)

        return self._insert_committed_result(
            connection, operation, target, scope, current_head
        )

    def _insert_rejected_result(
        self,
        connection: sqlite3.Connection,
        operation: ConfigurationPublicationOperation,
        scope: tuple[str, str, str, str],
    ) -> ConfigurationPublicationResult:
        result = ConfigurationPublicationResult(
            operation=operation.operation,
            stage=OperationStage.REJECTED,
            resulting_revision=None,
            published=None,
            effect=EffectExtent.NONE,
            error=ErrorDetail(
                category=ErrorCategory.CONFLICT,
                recoverability=Recoverability.REQUIRES_INTERVENTION,
                causes=(
                    ErrorCause(
                        category=ErrorCategory.CONFLICT,
                        operation=operation.operation,
                        record_key="expected-revision-mismatch",
                    ),
                ),
            ),
            duties=(),
        )
        self._store_result_row(connection, operation, scope, result)
        return result

    def _insert_committed_result(
        self,
        connection: sqlite3.Connection,
        operation: ConfigurationPublicationOperation,
        target: ConfigurationRef,
        scope: tuple[str, str, str, str],
        current_head: OwnerRevision | None,
    ) -> ConfigurationPublicationResult:
        next_head_value = (current_head.value if current_head is not None else 0) + 1
        new_head = OwnerRevision(target, next_head_value)
        revision_id = uuid.uuid4().hex
        published = ConfigurationRevisionRef(
            target, revision_id, operation.candidate.effective.contract_version
        )
        duty_id = DutyId(f"duty-{uuid.uuid4().hex}")
        duty = ConfigurationSourceSubmissionDuty(
            duty_id=duty_id,
            kind=DutyKind("source-submission"),
            operation=operation.operation,
            published=published,
            responsible_principal=operation.requested_by,
            tenant_context=TenantContext(target.application.scope.tenant_id),
            requirement=EvidenceRequirement(
                published, "source submission evidence required for this publication"
            ),
        )
        result = ConfigurationPublicationResult(
            operation=operation.operation,
            stage=OperationStage.COMMITTED,
            resulting_revision=new_head,
            published=published,
            effect=EffectExtent.COMPLETED,
            error=None,
            duties=(duty_id,),
        )

        record_json = codec.dumps(codec.encode_revision_content(operation.candidate))
        try:
            connection.execute(
                "INSERT INTO config_revision "
                "(tenant_id, owner, application_id, instance, revision_id, "
                "published_head_revision, record_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (*scope, revision_id, next_head_value, record_json),
            )
            if current_head is None:
                connection.execute(
                    "INSERT INTO config_head "
                    "(tenant_id, owner, application_id, instance, head_revision, "
                    "published_revision_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (*scope, next_head_value, revision_id),
                )
            else:
                cursor = connection.execute(
                    "UPDATE config_head SET head_revision = ?, "
                    "published_revision_id = ? "
                    "WHERE tenant_id = ? AND owner = ? AND application_id = ? "
                    "AND instance = ? AND head_revision = ?",
                    (
                        next_head_value,
                        revision_id,
                        *scope,
                        current_head.value,
                    ),
                )
                if cursor.rowcount != 1:
                    raise StorageUnavailableError(
                        "concurrent head mutation detected during publish"
                    )
            self._store_result_row(connection, operation, scope, result)
            connection.execute(
                "INSERT INTO config_duty "
                "(tenant_id, owner, application_id, instance, duty_id, duty_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    *scope,
                    duty_id.value,
                    codec.dumps(codec.encode_source_submission_duty(duty)),
                ),
            )
        except sqlite3.Error as exc:
            raise StorageUnavailableError(f"publish commit failed: {exc}") from exc
        return result

    def _store_result_row(
        self,
        connection: sqlite3.Connection,
        operation: ConfigurationPublicationOperation,
        scope: tuple[str, str, str, str],
        result: ConfigurationPublicationResult,
    ) -> None:
        descriptor_json = codec.dumps(codec.encode_publication_operation(operation))
        result_json = codec.dumps(codec.encode_publication_result(result))
        try:
            connection.execute(
                "INSERT INTO config_result "
                "(tenant_id, owner, application_id, instance, operation_id, "
                "contract_identity, descriptor_json, result_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    *scope,
                    operation.operation.operation_id.value,
                    operation.operation.contract_identity,
                    descriptor_json,
                    result_json,
                ),
            )
        except sqlite3.Error as exc:
            raise StorageUnavailableError(f"result insert failed: {exc}") from exc


def _operation_target(operation: OperationRef) -> ConfigurationRef:
    if type(operation.subject) is not ConfigurationRef:
        raise TypeError(
            "SQLiteConfigurationStore requires an OperationRef scoped to "
            "ConfigurationRef for this owner"
        )
    return operation.subject
