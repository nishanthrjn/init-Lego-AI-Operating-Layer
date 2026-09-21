"""G1-EXIT-08 remediation: synthetic predecessor persistence fixture and its
migration to F6a's real current physical schema.

``SYNTHETIC_PREDECESSOR_SCHEMA_VERSION = 0`` was **never a released LegoAI
representation**. F6a's real physical schema has been version 1 since its
first implementation (``legoai.reference.application.sqlite_store``); no
LegoAI release ever shipped a version-0 store. This fixture exists solely
to prove migration-interruption safety per Gate-1 plan SS9.3: "Use a
clearly synthetic predecessor fixture to exercise interrupted migration
before a real upgrade exists; do not invent a historical supported
release." It is not, and must never be read as, a historical schema.

v0's plausible (but entirely synthetic) structural difference from v1: the
outstanding-duty record is embedded as a nullable JSON column directly on
the result row (``duty_json_embedded``) instead of living in its own
``config_duty`` table. Migration extracts it into a real ``config_duty``
row, matching F6a's current normalized shape exactly (created via F6a's own
``_schema_statements()`` -- never a hand-duplicated second schema
definition, so there is no drift between "current" here and in production).

Everything else -- the F5 JSON envelope format inside
``record_json``/``descriptor_json``/``result_json``/``duty_json`` -- is
unchanged: ``RecordSchemaVersion`` stays at 1 throughout. Only the
*physical* SQL table layout differs between v0 and v1; F5's codec remains
the single, unmodified authority for the payloads themselves.

Test-only: never imported by ``src/legoai`` production code.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from legoai.application.values import (
    ConfigurationPublicationOperation,
    ConfigurationPublicationResult,
    ConfigurationSourceSubmissionDuty,
    OperationStage,
)
from legoai.evidence.values import EvidenceRequirement
from legoai.governance.values import Principal
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.identity import ApplicationId, OperationId, PrincipalId, TenantId
from legoai.kernel.provenance import DutyId, DutyKind
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
    _physical_schema_version,
    _schema_statements,
)

SYNTHETIC_PREDECESSOR_SCHEMA_VERSION = 0
VERSION = Version(0, 1, 0)
SCOPE = ("t1", "owner1", "app1", "inst1")


class MigrationPreconditionError(RuntimeError):
    """The store is not a v0 synthetic predecessor; migration refused."""


def fixture_target() -> ConfigurationRef:
    tenant_id, owner, application_id, instance = SCOPE
    scope = ReferenceScope(owner, TenantId(tenant_id))
    return ConfigurationRef(
        ApplicationRef(scope, ApplicationId(application_id)), instance
    )


def _connect(path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), autocommit=True, timeout=0.0)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = DELETE")
    connection.execute("PRAGMA synchronous = EXTRA")
    connection.execute("PRAGMA busy_timeout = 0")
    return connection


def _fixture_records(
    effect: EffectExtent,
) -> tuple[
    ConfigurationRevisionRef,
    str,
    ConfigurationPublicationResult,
    str,
    str,
    str | None,
]:
    """Build one full owner-local record set: a historical revision, its
    publication result (with the requested ``effect``), and -- for
    COMMITTED results only -- one outstanding duty."""
    target = fixture_target()
    candidate = compose_configuration(
        target, (), contract_version=VERSION, interpretation_version=VERSION
    )
    head = OwnerRevision(target, 1)
    published = ConfigurationRevisionRef(target, "r1", VERSION)
    operation_ref = OperationRef(target, OperationId("op1"), "migration-fixture")
    principal = Principal(PrincipalRef("issuer1", PrincipalId("p1")))

    operation = ConfigurationPublicationOperation(
        operation_ref, target, None, candidate, principal
    )
    duty: ConfigurationSourceSubmissionDuty | None = None
    if effect is EffectExtent.COMPLETED:
        duty_id = DutyId("duty-1")
        duty = ConfigurationSourceSubmissionDuty(
            duty_id=duty_id,
            kind=DutyKind("source-submission"),
            operation=operation_ref,
            published=published,
            responsible_principal=principal,
            tenant_context=TenantContext(target.application.scope.tenant_id),
            requirement=EvidenceRequirement(published, "evidence needed"),
        )
        duties: tuple[DutyId, ...] = (duty_id,)
    else:
        duties = ()

    result = ConfigurationPublicationResult(
        operation=operation_ref,
        stage=OperationStage.COMMITTED,
        resulting_revision=head,
        published=published,
        effect=effect,
        error=None,
        duties=duties,
    )

    record_json = codec.dumps(codec.encode_revision_content(candidate))
    descriptor_json = codec.dumps(codec.encode_publication_operation(operation))
    result_json = codec.dumps(codec.encode_publication_result(result))
    duty_json = (
        codec.dumps(codec.encode_source_submission_duty(duty))
        if duty is not None
        else None
    )
    return published, record_json, result, descriptor_json, result_json, duty_json


def create_synthetic_predecessor_store(
    path: Path | str, *, effect: EffectExtent = EffectExtent.COMPLETED
) -> None:
    """Create one v0 synthetic predecessor database at ``path`` containing
    one full owner-local record set (head, published revision, historical
    content, operation result, and -- for a COMPLETED effect -- one
    outstanding duty embedded per v0's own layout)."""
    published, record_json, result, descriptor_json, result_json, duty_json = (
        _fixture_records(effect)
    )
    tenant_id, owner, application_id, instance = SCOPE

    connection = _connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            CREATE TABLE store_metadata (
                id INTEGER NOT NULL,
                schema_version INTEGER NOT NULL,
                PRIMARY KEY (id),
                CHECK (id = 1)
            ) STRICT
            """
        )
        connection.execute(
            "INSERT INTO store_metadata (id, schema_version) VALUES (1, ?)",
            (SYNTHETIC_PREDECESSOR_SCHEMA_VERSION,),
        )
        connection.execute(
            """
            CREATE TABLE config_revision_v0 (
                tenant_id TEXT NOT NULL,
                owner TEXT NOT NULL,
                application_id TEXT NOT NULL,
                instance TEXT NOT NULL,
                revision_id TEXT NOT NULL,
                published_head_revision INTEGER NOT NULL,
                record_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, owner, application_id, instance, revision_id),
                UNIQUE (tenant_id, owner, application_id, instance, published_head_revision)
            ) STRICT
            """
        )
        connection.execute(
            """
            CREATE TABLE config_head_v0 (
                tenant_id TEXT NOT NULL,
                owner TEXT NOT NULL,
                application_id TEXT NOT NULL,
                instance TEXT NOT NULL,
                head_revision INTEGER NOT NULL,
                published_revision_id TEXT NOT NULL,
                PRIMARY KEY (tenant_id, owner, application_id, instance),
                FOREIGN KEY (tenant_id, owner, application_id, instance, published_revision_id)
                    REFERENCES config_revision_v0
                        (tenant_id, owner, application_id, instance, revision_id)
            ) STRICT
            """
        )
        connection.execute(
            """
            CREATE TABLE config_result_v0 (
                tenant_id TEXT NOT NULL,
                owner TEXT NOT NULL,
                application_id TEXT NOT NULL,
                instance TEXT NOT NULL,
                operation_id TEXT NOT NULL,
                contract_identity TEXT NOT NULL,
                descriptor_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                duty_json_embedded TEXT,
                PRIMARY KEY (tenant_id, owner, application_id, instance, operation_id)
            ) STRICT
            """
        )
        connection.execute(
            "INSERT INTO config_revision_v0 "
            "(tenant_id, owner, application_id, instance, revision_id, "
            "published_head_revision, record_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                tenant_id,
                owner,
                application_id,
                instance,
                published.revision,
                1,
                record_json,
            ),
        )
        connection.execute(
            "INSERT INTO config_head_v0 "
            "(tenant_id, owner, application_id, instance, head_revision, "
            "published_revision_id) VALUES (?, ?, ?, ?, ?, ?)",
            (tenant_id, owner, application_id, instance, 1, published.revision),
        )
        connection.execute(
            "INSERT INTO config_result_v0 "
            "(tenant_id, owner, application_id, instance, operation_id, "
            "contract_identity, descriptor_json, result_json, duty_json_embedded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                tenant_id,
                owner,
                application_id,
                instance,
                result.operation.operation_id.value,
                result.operation.contract_identity,
                descriptor_json,
                result_json,
                duty_json,
            ),
        )
        connection.execute("COMMIT")
    finally:
        connection.close()


def migrate_predecessor_to_current(
    path: Path | str,
    *,
    ready_marker: Path | None = None,
    stop_before_commit: bool = False,
) -> None:
    """Migrate a v0 synthetic predecessor store at ``path`` to F6a's real
    current physical schema, entirely within one SQLite transaction
    (LOCAL-PERSISTENCE-REALIZATION.md SS11: "Use one explicit transaction
    for the first bounded owner migration").

    When ``stop_before_commit`` is true, every structural step below runs,
    ``ready_marker`` (if given) is written to signal a waiting parent
    process, and this function then blocks forever *before* the schema-
    version marker is bumped and before ``COMMIT`` -- deliberately never
    returning normally. A parent that kills this process at that point
    exercises real OS-level interruption of an in-progress, uncommitted
    migration transaction.
    """
    connection = _connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT schema_version FROM store_metadata WHERE id = 1"
        ).fetchone()
        if row is None or row[0] != SYNTHETIC_PREDECESSOR_SCHEMA_VERSION:
            raise MigrationPreconditionError(
                "migrate_predecessor_to_current requires a v0 synthetic "
                "predecessor store"
            )

        # Structurally-unchanged tables: rename in place, preserving data
        # and (per SQLite's RENAME TABLE semantics) updating the FOREIGN
        # KEY reference in config_head_v0 to point at the new name.
        connection.execute("ALTER TABLE config_revision_v0 RENAME TO config_revision")
        connection.execute("ALTER TABLE config_head_v0 RENAME TO config_head")

        # Create the current-shape tables using F6a's own real schema
        # definitions -- never a hand-duplicated second copy.
        for statement in _schema_statements():
            connection.execute(statement)

        # Extract each v0-embedded duty into its own current-shape row.
        embedded = connection.execute(
            "SELECT tenant_id, owner, application_id, instance, duty_json_embedded "
            "FROM config_result_v0 WHERE duty_json_embedded IS NOT NULL"
        ).fetchall()
        for tenant_id, owner, application_id, instance, duty_json in embedded:
            duty_id = json.loads(duty_json)["duty_id"]
            connection.execute(
                "INSERT INTO config_duty "
                "(tenant_id, owner, application_id, instance, duty_id, duty_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (tenant_id, owner, application_id, instance, duty_id, duty_json),
            )

        # Copy result rows without the now-obsolete embedded-duty column.
        connection.execute(
            "INSERT INTO config_result "
            "(tenant_id, owner, application_id, instance, operation_id, "
            "contract_identity, descriptor_json, result_json) "
            "SELECT tenant_id, owner, application_id, instance, operation_id, "
            "contract_identity, descriptor_json, result_json FROM config_result_v0"
        )
        connection.execute("DROP TABLE config_result_v0")

        if ready_marker is not None:
            ready_marker.write_text("ready", encoding="utf-8")

        if stop_before_commit:
            # Deliberately never reach the marker bump or COMMIT below --
            # the parent process kills this one at this exact point.
            time.sleep(3600)
            return  # pragma: no cover -- unreachable under normal test timing

        # The schema-version marker is bumped last, only once every
        # structural step in this same transaction has already succeeded
        # (this batch's own requirement: prove it cannot indicate a
        # completed migration while required work remains incomplete).
        connection.execute(
            "UPDATE store_metadata SET schema_version = ?",
            (_physical_schema_version(),),
        )
        connection.execute("COMMIT")
    finally:
        connection.close()
