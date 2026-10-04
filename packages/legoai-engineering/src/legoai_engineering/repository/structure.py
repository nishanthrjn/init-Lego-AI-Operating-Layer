"""DISCOVERY-1 immutable structure data; no I/O, Core or authority dependency."""

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import Enum

from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.workspace import (
    RepositoryPath,
    WorkspaceEntry,
    WorkspaceEntryKind,
)

MANDATORY_EXCLUDED_NAMES = frozenset(
    {
        "secrets",
        "credentials",
        "private",
        "node_modules",
        "build",
        "dist",
        "generated",
        "vendor",
        "__pycache__",
    }
)


class StructureFailure(Enum):
    CONFIGURATION_INVALID = "invalid structure configuration"
    AUTHORIZATION_DENIED = "structure authorization denied"
    AUTHORITY_UNAVAILABLE = "structure authority unavailable"
    WORKSPACE_UNAVAILABLE = "structure workspace unavailable"
    BOUNDARY_VIOLATION = "structure boundary violation"
    STRUCTURE_LIMIT_EXCEEDED = "structure limit exceeded"
    UNSUPPORTED_ENTRY = "unsupported structure entry"
    STRUCTURE_CHANGED = "structure changed"


class StructureError(RuntimeError):
    """Safe category only. Chained causes are restricted trusted diagnostics."""

    def __init__(self, reason: StructureFailure) -> None:
        if type(reason) is not StructureFailure:
            raise TypeError("structure failure requires StructureFailure")
        self.reason = reason
        super().__init__(reason.value)


def _path(path: RepositoryPath) -> None:
    if type(path) is not RepositoryPath:
        raise StructureError(StructureFailure.UNSUPPORTED_ENTRY)
    try:
        encoded = path.value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise StructureError(StructureFailure.UNSUPPORTED_ENTRY) from error
    if len(encoded) > 960 or any(len(p) > 128 for p in path.value.split("/")):
        raise StructureError(StructureFailure.STRUCTURE_LIMIT_EXCEEDED)
    if any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in path.value):
        raise StructureError(StructureFailure.UNSUPPORTED_ENTRY)


def _below(path: str, parent: str) -> bool:
    return path == parent or path.startswith(parent + "/")


@dataclass(frozen=True, slots=True)
class RepositoryStructurePolicy:
    """Trusted policy. Bound workspace must exclude only these approved filters.

    Its per-directory scan ceiling must be <=512 (including excluded entries).
    The Port cannot introspect that adapter configuration; composition owns it.
    No implicit workspace-root scan, Git filtering or secret-classifier claim.
    """

    roots: tuple[RepositoryPath, ...] = field(repr=False)
    excluded_names: tuple[str, ...] = field(default=(), repr=False)
    excluded_subtrees: tuple[RepositoryPath, ...] = field(default=(), repr=False)
    max_depth: int = 6
    max_entries: int = 512
    max_list_calls: int = 64
    max_serialized_bytes: int = 16384

    def __post_init__(self) -> None:
        try:
            self._validate()
        except (ValueError, TypeError, StructureError, WorkspaceError) as error:
            raise StructureError(StructureFailure.CONFIGURATION_INVALID) from error

    def _validate(self) -> None:
        for value, ceiling in (
            (self.max_depth, 6),
            (self.max_entries, 512),
            (self.max_list_calls, 64),
            (self.max_serialized_bytes, 16384),
        ):
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError("invalid structure ceiling")
        if type(self.roots) is not tuple or not 1 <= len(self.roots) <= 8:
            raise ValueError("invalid structure roots")
        if type(self.excluded_names) is not tuple or len(self.excluded_names) > 32:
            raise ValueError("invalid component exclusions")
        for name in self.excluded_names:
            if type(name) is not str or "/" in name:
                raise ValueError("invalid component exclusion")
            _path(RepositoryPath(name))
        if len({n.casefold() for n in self.excluded_names}) != len(self.excluded_names):
            raise ValueError("duplicate component exclusions")
        if (
            type(self.excluded_subtrees) is not tuple
            or len(self.excluded_subtrees) > 32
        ):
            raise ValueError("invalid subtree exclusions")
        for path in (*self.roots, *self.excluded_subtrees):
            _path(path)
        subtrees = [p.value.casefold() for p in self.excluded_subtrees]
        if len(set(subtrees)) != len(subtrees):
            raise ValueError("duplicate subtree exclusions")
        roots = [p.value.casefold() for p in self.roots]
        if any(
            _below(a, b)
            for i, a in enumerate(roots)
            for j, b in enumerate(roots)
            if i != j
        ):
            raise ValueError("overlapping roots")
        for root in self.roots:
            if self.excludes(root) or len(root.value.split("/")) >= self.max_depth:
                raise ValueError("excluded or too-deep root")
        if len(self.roots) > min(self.max_entries, self.max_list_calls):
            raise ValueError("root count exceeds budget")

    def excludes(self, path: RepositoryPath) -> bool:
        names = MANDATORY_EXCLUDED_NAMES | {n.casefold() for n in self.excluded_names}
        return any(
            p.startswith(".") or p.casefold() in names for p in path.value.split("/")
        ) or any(
            _below(path.value.casefold(), p.value.casefold())
            for p in self.excluded_subtrees
        )

    def _identity(self) -> dict[str, object]:
        return {
            "roots": sorted(p.value for p in self.roots),
            "excluded_names": sorted(n.casefold() for n in self.excluded_names),
            "excluded_subtrees": sorted(
                p.value.casefold() for p in self.excluded_subtrees
            ),
            "mandatory_profile": 1,
            "max_depth": self.max_depth,
            "max_entries": self.max_entries,
            "max_list_calls": self.max_list_calls,
            "max_serialized_bytes": self.max_serialized_bytes,
        }


def _json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class RepositoryStructure:
    """Filtered advisory data, never authority, a snapshot or content evidence.

    Explicit serialization reveals approved relative names to trusted consumers.
    Calling it does not authorize logging or later model disclosure.
    """

    policy: RepositoryStructurePolicy = field(repr=False)
    entries: tuple[WorkspaceEntry, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.policy) is not RepositoryStructurePolicy
            or type(self.entries) is not tuple
        ):
            raise StructureError(StructureFailure.UNSUPPORTED_ENTRY)
        if len(self.entries) > self.policy.max_entries:
            raise StructureError(StructureFailure.STRUCTURE_LIMIT_EXCEEDED)
        seen: dict[str, WorkspaceEntryKind] = {}
        aliases: set[str] = set()
        roots = {p.value for p in self.policy.roots}
        for entry in self.entries:
            if (
                type(entry) is not WorkspaceEntry
                or type(entry.kind) is not WorkspaceEntryKind
            ):
                raise StructureError(StructureFailure.UNSUPPORTED_ENTRY)
            _path(entry.path)
            path = entry.path.value
            if path.casefold() in aliases or self.policy.excludes(entry.path):
                raise StructureError(StructureFailure.BOUNDARY_VIOLATION)
            if not any(_below(path, root) for root in roots):
                raise StructureError(StructureFailure.BOUNDARY_VIOLATION)
            depth = len(path.split("/"))
            if depth > self.policy.max_depth or (
                depth == self.policy.max_depth
                and entry.kind is WorkspaceEntryKind.DIRECTORY
            ):
                raise StructureError(StructureFailure.STRUCTURE_LIMIT_EXCEEDED)
            aliases.add(path.casefold())
            seen[path] = entry.kind
        if tuple(sorted(self.entries, key=lambda e: e.path.value)) != self.entries:
            raise StructureError(StructureFailure.UNSUPPORTED_ENTRY)
        for root in roots:
            if seen.get(root) is not WorkspaceEntryKind.DIRECTORY:
                raise StructureError(StructureFailure.BOUNDARY_VIOLATION)
        for path in seen:
            if (
                path not in roots
                and seen.get(path.rpartition("/")[0])
                is not WorkspaceEntryKind.DIRECTORY
            ):
                raise StructureError(StructureFailure.BOUNDARY_VIOLATION)
        if len(self.model_bytes()) > self.policy.max_serialized_bytes:
            raise StructureError(StructureFailure.STRUCTURE_LIMIT_EXCEEDED)

    def model_bytes(self) -> bytes:
        """Versioned strict UTF-8 map envelope; no internal policy or digest."""
        return _json(
            {
                "version": 1,
                "coverage": "Selected roots only; policy exclusions apply; not the whole repository.",
                "entries": [
                    {"path": e.path.value, "kind": e.kind.value} for e in self.entries
                ],
            }
        )

    def identity_bytes(self) -> bytes:
        """Internal canonical policy + map representation; confidential too."""
        return _json(
            {
                "version": 1,
                "policy": self.policy._identity(),
                "map": json.loads(self.model_bytes()),
            }
        )

    def digest(self) -> str:
        """SHA-256 of identity_bytes; not authority, anonymity or content integrity."""
        return hashlib.sha256(self.identity_bytes()).hexdigest()
