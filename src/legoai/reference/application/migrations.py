"""Explicit owner-local representation maintenance; no released upgrade exists.

Trusted, reviewed callbacks are supplied by code, never by record content.
Preparation is pure and produces no committed marker. A future maintainer must
establish exclusion, authority, storage identity and actual atomic commit/reopen
proof. Caller-supplied observations here are inputs, never proof of those facts.
"""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from legoai.kernel.identity import _validate
from legoai.reference.application.records import (
    OwnerRecord,
    RecordFailure,
    RecordKind,
    RecordProblem,
    _integer,
    _object,
    _parse,
    _text,
    record_subject,
)


def artifact_fingerprint(artifact: bytes) -> str:
    """Bind reviewed bytes only; not a signature, trust, authority or record ID."""
    if type(artifact) is not bytes or not 1 <= len(artifact) <= 65536:
        raise ValueError("reviewed migration artifact requires 1-65536 bytes")
    return hashlib.sha256(artifact).hexdigest()


@dataclass(frozen=True, slots=True)
class MigrationDescriptor:
    owner: str = field(repr=False)
    migration_id: str = field(repr=False)
    kind: RecordKind
    source_schema: int
    target_schema: int
    source_reader: int
    target_reader: int
    fingerprint: str

    def __post_init__(self) -> None:
        _validate(self.owner)
        _validate(self.migration_id)
        if type(self.kind) is not RecordKind:
            raise TypeError("migration requires record kind")
        for version in (
            self.source_schema,
            self.target_schema,
            self.source_reader,
            self.target_reader,
        ):
            _integer(version, 1)
        if (
            self.target_schema <= self.source_schema
            or self.target_reader < self.source_reader
        ):
            raise ValueError("migration must advance representation without downgrade")
        if (
            type(self.fingerprint) is not str
            or len(self.fingerprint) != 64
            or any(
                character not in "0123456789abcdef" for character in self.fingerprint
            )
        ):
            raise ValueError("migration requires lowercase SHA-256 fingerprint")


class MigrationStage(Enum):
    PREPARED = "prepared, not committed"
    COMMITTED = "committed marker observation"


@dataclass(frozen=True, slots=True)
class MigrationMarker:
    descriptor: MigrationDescriptor
    stage: MigrationStage

    def __post_init__(self) -> None:
        if (
            type(self.descriptor) is not MigrationDescriptor
            or type(self.stage) is not MigrationStage
        ):
            raise TypeError("migration marker requires descriptor and stage")


@dataclass(frozen=True, slots=True)
class MigrationObservation:
    schema: int
    reader: int
    complete: bool
    marker: MigrationMarker | None

    def __post_init__(self) -> None:
        _integer(self.schema, 1)
        _integer(self.reader, 1)
        if type(self.complete) is not bool:
            raise TypeError("migration completeness must be explicit bool")
        if self.marker is not None and type(self.marker) is not MigrationMarker:
            raise TypeError("migration observation requires exact marker")


class MigrationDecision(Enum):
    PREPARE = "complete source; explicit preparation permitted"
    VALIDATE_TARGET = "complete committed target; validate without rerunning"
    INTERVENTION = "unknown or inconsistent; block"


def assess_migration(
    selected: MigrationDescriptor, observed: MigrationObservation
) -> MigrationDecision:
    if (
        type(selected) is not MigrationDescriptor
        or type(observed) is not MigrationObservation
    ):
        raise TypeError(
            "migration assessment requires explicit descriptor and observation"
        )
    if not observed.complete:
        return MigrationDecision.INTERVENTION
    if (observed.schema, observed.reader) == (
        selected.source_schema,
        selected.source_reader,
    ):
        return (
            MigrationDecision.PREPARE
            if observed.marker is None
            else MigrationDecision.INTERVENTION
        )
    if (observed.schema, observed.reader) == (
        selected.target_schema,
        selected.target_reader,
    ) and observed.marker == MigrationMarker(selected, MigrationStage.COMMITTED):
        return MigrationDecision.VALIDATE_TARGET
    return MigrationDecision.INTERVENTION


@dataclass(frozen=True, slots=True)
class MigrationTransition:
    descriptor: MigrationDescriptor
    reviewed_artifact: bytes = field(repr=False)
    transform: Callable[[bytes], bytes] = field(repr=False)
    source_reader: Callable[[bytes], OwnerRecord | RecordFailure] = field(repr=False)
    target_reader: Callable[[bytes], OwnerRecord | RecordFailure] = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.descriptor) is not MigrationDescriptor:
            raise TypeError("transition requires migration descriptor")
        if artifact_fingerprint(self.reviewed_artifact) != self.descriptor.fingerprint:
            raise ValueError("reviewed migration artifact mismatch")
        if not all(
            callable(callback)
            for callback in (self.transform, self.source_reader, self.target_reader)
        ):
            raise TypeError("transition requires trusted code callbacks")


@dataclass(frozen=True, slots=True)
class MigrationRegistry:
    """Finite explicit transitions, no discovery or multi-step graph search.

    Registration review binds callbacks to the fingerprinted artifact. Hashing
    supplied bytes cannot establish that arbitrary Python callbacks implement it.
    """

    transitions: tuple[MigrationTransition, ...]

    def __post_init__(self) -> None:
        if type(self.transitions) is not tuple or len(self.transitions) > 16:
            raise ValueError("registry requires at most sixteen explicit transitions")
        identities: set[tuple[str, str]] = set()
        starts: set[tuple[str, RecordKind, int]] = set()
        for transition in self.transitions:
            if type(transition) is not MigrationTransition:
                raise TypeError("registry requires reviewed transitions")
            descriptor = transition.descriptor
            identity = (descriptor.owner, descriptor.migration_id)
            start = (descriptor.owner, descriptor.kind, descriptor.source_schema)
            if identity in identities or start in starts:
                raise ValueError("duplicate migration identity or ambiguous transition")
            identities.add(identity)
            starts.add(start)


def supported_migrations() -> MigrationRegistry:
    """Schema 1 is the first format: no real historical transition is supported."""
    return MigrationRegistry(())


@dataclass(frozen=True, slots=True)
class PreparedMigration:
    data: bytes = field(repr=False)
    marker: MigrationMarker

    def __post_init__(self) -> None:
        if type(self.data) is not bytes or not 1 <= len(self.data) <= 65536:
            raise ValueError("prepared migration requires bounded bytes")
        if (
            type(self.marker) is not MigrationMarker
            or self.marker.stage is not MigrationStage.PREPARED
        ):
            raise ValueError("prepared output cannot assert committed migration")


def _matches(data: bytes, descriptor: MigrationDescriptor, *, target: bool) -> None:
    obj = _object(
        _parse(data),
        "record_kind record_schema_version reader_contract_version subject payload",
    )
    schema = descriptor.target_schema if target else descriptor.source_schema
    reader = descriptor.target_reader if target else descriptor.source_reader
    if (
        RecordKind(_text(obj["record_kind"])) is not descriptor.kind
        or _integer(obj["record_schema_version"], 1) != schema
        or _integer(obj["reader_contract_version"], 1) != reader
    ):
        raise ValueError("migration envelope mismatch")


def prepare_migration(
    data: bytes,
    *,
    selected: MigrationDescriptor,
    registry: MigrationRegistry,
    observed: MigrationObservation,
) -> PreparedMigration | RecordFailure:
    """Pure single-record preparation, comparing full interpreted source/target.

    No callback runs for unknown, completed or unregistered transitions. Complete
    target observations require separate validation, never implicit rerun. Any
    callback/interpretation failure returns a safe failure without partial output.
    Batch/cross-row preservation and atomic interruption proof belong to F6.
    """
    if type(registry) is not MigrationRegistry:
        raise TypeError("explicit migration registry required")
    if assess_migration(selected, observed) is not MigrationDecision.PREPARE:
        return RecordFailure(RecordProblem.MALFORMED)
    transition = next(
        (item for item in registry.transitions if item.descriptor == selected), None
    )
    if transition is None:
        return RecordFailure(RecordProblem.UNSUPPORTED)
    try:
        _matches(data, selected, target=False)
        source = transition.source_reader(data)
        if isinstance(source, RecordFailure):
            return source
        if record_subject(source).application.scope.owner != selected.owner:
            return RecordFailure(RecordProblem.MALFORMED)
        transformed = transition.transform(data)
        _matches(transformed, selected, target=True)
        target = transition.target_reader(transformed)
        if isinstance(target, RecordFailure):
            return target
        if source != target:
            return RecordFailure(RecordProblem.MALFORMED)
        return PreparedMigration(
            transformed, MigrationMarker(selected, MigrationStage.PREPARED)
        )
    except Exception:
        # Trusted callbacks can fail unexpectedly. No partial output, callback
        # exception text or source bytes cross this semantic failure boundary.
        return RecordFailure(RecordProblem.MALFORMED)
