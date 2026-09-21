"""F6b: restart qualification and recovery inspection for the Application
Composition configuration owner's SQLite realization (ADR-004 SS13-14;
LOCAL-PERSISTENCE-REALIZATION.md SS12-13, SS17-18).

This module answers, after restart: is the persisted state safe to admit,
what owner scopes exist, which revisions/results are recoverable, which
durable duties remain outstanding, and are there integrity or representation
failures that must block admission? It is an inspection/qualification layer,
not an Execution engine, not a retry/compensation mechanism, and not an
authorization decision (ADR-004 SS13 item 7: "this ADR does not authorize a
store or Plugin to admit itself"). A record having been authorized
historically does not prove it is authorized now -- current authorization
remains later governed runtime's responsibility, untouched here.

Projections (ADR-004 SS14) do not apply to this schema: `config_head` /
`config_revision` / `config_result` / `config_duty` are authoritative owner
records, not derived/non-authoritative views, so there is nothing to
rebuild here. Inventing one would be ceremonial, not required.

Recovery reuses the unchanged F6a store and F5 codecs. It calls
``SQLiteConfigurationStore``'s own public Port methods wherever the Port
already exposes what is needed (``current_head``, ``current_published``,
``outstanding_duties``), and reads this owner's own physical tables
directly only for what the Port cannot express: enumerating which owner
scopes physically exist, and decoding *every* retained historical
revision/result row (not just the current one) to prove exact historical
meaning survived restart.

Failure model scope (ADR-004 SS6/SS13; LOCAL-PERSISTENCE-REALIZATION.md
SS12, SS17-18): qualifies restart after process/runtime restart, or machine
termination over otherwise-intact storage, with a possibly lost caller
acknowledgement. It does NOT qualify disk destruction, filesystem
corruption beyond what ``PRAGMA integrity_check``/``foreign_key_check`` can
detect, backup restore, or multi-machine failure. ``synchronous=EXTRA`` is
not claimed here as a universal durability guarantee under arbitrary
hardware failure -- only what the accepted settings and this batch's own
tests actually exercise.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import cast
from urllib.parse import quote

from legoai.application.values import ConfigurationSourceSubmissionDuty
from legoai.kernel.identity import ApplicationId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    OwnerRevision,
    ReferenceScope,
)
from legoai.reference.application import codec
from legoai.reference.application.sqlite_store import (
    SQLiteConfigurationStore,
    StorageUnavailableError,
    _physical_schema_version,
    _scope_columns,
)


class RecoveryStatus(Enum):
    """Admission-gating verdict this batch actually proves (ADR-004 SS13
    item 7). Not a business/authorization decision -- only whether the
    persisted representation itself is trustworthy enough to hand to a
    later authorized admission process."""

    QUALIFIED = "qualified"
    BLOCKED = "blocked"


class RecoveryUnavailableError(RuntimeError):
    """The physical store cannot even be opened/read for inspection
    (missing file, I/O failure) -- distinct from a store that opens but
    fails qualification, which is reported as ``RecoveryStatus.BLOCKED``
    in a returned :class:`RecoveryReport`, never raised."""


@dataclass(frozen=True, slots=True)
class ScopeQualification:
    """Recovery findings for one Application configuration-owner scope.

    ``outstanding_duties`` is ``None`` exactly when duty discovery itself
    could not be completed (a representation failure while reading duties)
    -- never conflated with a genuinely empty tuple (no outstanding duties).
    """

    target: ConfigurationRef
    current_head: OwnerRevision | None
    current_published: ConfigurationRevisionRef | None
    revision_count: int
    result_count: int
    outstanding_duties: tuple[ConfigurationSourceSubmissionDuty, ...] | None
    representation_failures: tuple[str, ...]

    @property
    def qualified(self) -> bool:
        return not self.representation_failures


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    """Recovery/qualification result for one physical SQLite store.

    A diagnostic/admission-gating fact record -- not an Observability
    backend, not authoritative business state, and not itself a Grant,
    Approval, or any other authorization decision.
    """

    status: RecoveryStatus
    physical_schema_version: int | None
    integrity_check: str
    foreign_key_violations: tuple[str, ...]
    scopes: tuple[ScopeQualification, ...]

    @property
    def outstanding_duty_count(self) -> int:
        return sum(
            len(scope.outstanding_duties)
            for scope in self.scopes
            if scope.outstanding_duties is not None
        )


def _connect_for_inspection(path: str | Path) -> sqlite3.Connection:
    # Read-only URI mode: recovery must never create a database file merely
    # by inspecting a path that does not exist (ordinary sqlite3.connect
    # would silently do so).
    resolved = Path(path)
    uri = f"file:{quote(resolved.as_posix())}?mode=ro"
    try:
        connection = sqlite3.connect(
            uri, uri=True, timeout=0.0, check_same_thread=True, autocommit=True
        )
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 0")
    except sqlite3.Error as exc:
        raise RecoveryUnavailableError(
            f"cannot open store for recovery: {exc}"
        ) from exc
    return connection


def _run_integrity_check(connection: sqlite3.Connection) -> str:
    try:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
    except sqlite3.Error as exc:
        raise RecoveryUnavailableError(f"integrity_check failed: {exc}") from exc
    if len(rows) == 1 and rows[0][0] == "ok":
        return "ok"
    return "; ".join(str(row[0]) for row in rows)


def _run_foreign_key_check(connection: sqlite3.Connection) -> tuple[str, ...]:
    try:
        rows = connection.execute("PRAGMA foreign_key_check").fetchall()
    except sqlite3.Error as exc:
        raise RecoveryUnavailableError(f"foreign_key_check failed: {exc}") from exc
    return tuple(
        f"{row[0]} row {row[1]} violates foreign key to {row[2]}" for row in rows
    )


def _read_physical_schema_version(connection: sqlite3.Connection) -> int | None:
    try:
        row = connection.execute(
            "SELECT schema_version FROM store_metadata WHERE id = 1"
        ).fetchone()
    except sqlite3.Error:
        # store_metadata itself does not exist -- not a recognizable store.
        return None
    return cast(int, row[0]) if row is not None else None


def _discover_scopes(connection: sqlite3.Connection) -> tuple[ConfigurationRef, ...]:
    try:
        rows = connection.execute(
            "SELECT DISTINCT tenant_id, owner, application_id, instance FROM ("
            "SELECT tenant_id, owner, application_id, instance FROM config_head "
            "UNION SELECT tenant_id, owner, application_id, instance FROM config_revision "
            "UNION SELECT tenant_id, owner, application_id, instance FROM config_result "
            "UNION SELECT tenant_id, owner, application_id, instance FROM config_duty"
            ") ORDER BY tenant_id, owner, application_id, instance"
        ).fetchall()
    except sqlite3.Error as exc:
        raise RecoveryUnavailableError(f"scope discovery failed: {exc}") from exc
    return tuple(
        ConfigurationRef(
            ApplicationRef(
                ReferenceScope(owner, TenantId(tenant_id)),
                ApplicationId(application_id),
            ),
            instance,
        )
        for tenant_id, owner, application_id, instance in rows
    )


def _qualify_scope(
    connection: sqlite3.Connection,
    store: SQLiteConfigurationStore,
    target: ConfigurationRef,
) -> ScopeQualification:
    failures: list[str] = []

    current_head: OwnerRevision | None
    try:
        current_head = store.current_head(target)
    except (codec.RepresentationError, StorageUnavailableError) as exc:
        failures.append(f"current_head: {type(exc).__name__}")
        current_head = None

    current_published: ConfigurationRevisionRef | None
    try:
        current_published = store.current_published(target)
    except (codec.RepresentationError, StorageUnavailableError) as exc:
        failures.append(f"current_published: {type(exc).__name__}")
        current_published = None

    scope = _scope_columns(target)

    try:
        revision_rows = connection.execute(
            "SELECT revision_id, record_json FROM config_revision "
            "WHERE tenant_id = ? AND owner = ? AND application_id = ? "
            "AND instance = ?",
            scope,
        ).fetchall()
    except sqlite3.Error as exc:
        raise RecoveryUnavailableError(f"revision scan failed: {exc}") from exc
    revision_count = 0
    for revision_id, record_json in revision_rows:
        revision_count += 1
        try:
            codec.decode_revision_content(codec.loads(record_json))
        except codec.RepresentationError as exc:
            failures.append(f"revision {revision_id}: {type(exc).__name__}")

    try:
        result_rows = connection.execute(
            "SELECT operation_id, result_json FROM config_result "
            "WHERE tenant_id = ? AND owner = ? AND application_id = ? "
            "AND instance = ?",
            scope,
        ).fetchall()
    except sqlite3.Error as exc:
        raise RecoveryUnavailableError(f"result scan failed: {exc}") from exc
    result_count = 0
    for operation_id, result_json in result_rows:
        result_count += 1
        try:
            codec.decode_publication_result(codec.loads(result_json))
        except codec.RepresentationError as exc:
            failures.append(f"result {operation_id}: {type(exc).__name__}")

    outstanding_duties: tuple[ConfigurationSourceSubmissionDuty, ...] | None
    try:
        outstanding_duties = store.outstanding_duties(target)
    except (codec.RepresentationError, StorageUnavailableError) as exc:
        failures.append(f"outstanding_duties: {type(exc).__name__}")
        outstanding_duties = None

    return ScopeQualification(
        target=target,
        current_head=current_head,
        current_published=current_published,
        revision_count=revision_count,
        result_count=result_count,
        outstanding_duties=outstanding_duties,
        representation_failures=tuple(failures),
    )


def qualify_store(path: str | Path) -> RecoveryReport:
    """Inspect one physical SQLite store and report whether it is safe to
    hand to a later authorized admission process.

    Purely observational: opens the store read-only for the physical checks
    (integrity/foreign-key/schema-version), and afterward uses
    ``SQLiteConfigurationStore``'s own unchanged public methods for the
    per-scope semantic inspection. Never mutates domain state, never
    executes or resolves a duty, never recomputes a result, and never
    substitutes current/latest data for missing or corrupt historical
    content (ADR-004 SS13.1).

    Raises :class:`RecoveryUnavailableError` only when the store cannot be
    opened/read at all; every representation or integrity problem found in
    an openable store is instead reported via ``RecoveryReport.status``.
    """
    connection = _connect_for_inspection(path)
    try:
        integrity = _run_integrity_check(connection)
        foreign_key_violations = _run_foreign_key_check(connection)
        physical_version = _read_physical_schema_version(connection)

        if physical_version is None:
            return RecoveryReport(
                RecoveryStatus.BLOCKED, None, integrity, foreign_key_violations, ()
            )
        if (
            integrity != "ok"
            or foreign_key_violations
            or physical_version != _physical_schema_version()
        ):
            # Physical corruption or an unrecognized schema can affect every
            # owner in this shared file (LOCAL-PERSISTENCE-REALIZATION.md
            # SS16); do not attempt per-scope interpretation of tables whose
            # trustworthiness is not yet established.
            return RecoveryReport(
                RecoveryStatus.BLOCKED,
                physical_version,
                integrity,
                foreign_key_violations,
                (),
            )

        scopes = _discover_scopes(connection)
        store = SQLiteConfigurationStore(path)
        scope_reports = tuple(
            _qualify_scope(connection, store, target) for target in scopes
        )
    finally:
        connection.close()

    status = (
        RecoveryStatus.QUALIFIED
        if all(scope.qualified for scope in scope_reports)
        else RecoveryStatus.BLOCKED
    )
    return RecoveryReport(
        status, physical_version, integrity, foreign_key_violations, scope_reports
    )
