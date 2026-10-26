"""Deterministic guidance candidates and metadata; no reads or authority."""

from dataclasses import dataclass
from enum import Enum

from legoai_engineering.repository.mutation import ContentDigest
from legoai_engineering.repository.workspace import RepositoryPath

from forgeai.domain import TaskRequest

MAX_CANDIDATES = 16
MAX_GUIDANCE_FILES = 4
MAX_GUIDANCE_BYTES = 12288
MAX_REFERENCE_FILES = 8
MAX_REFERENCE_BYTES = 16384
MAX_FILE_BYTES = 8192


class GuidanceStatus(Enum):
    INCLUDED = "INCLUDED"
    NOT_PRESENT = "NOT_PRESENT"
    EXCEEDS_FILE_BOUND = "EXCEEDS_FILE_BOUND"
    EXCLUDED_BUDGET = "EXCLUDED_BUDGET"
    NOT_CONSIDERED_LIMIT = "NOT_CONSIDERED_LIMIT"


class GuidanceRefusal(Enum):
    DENIED = "DENIED"
    BOUNDARY = "BOUNDARY"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    OPERATOR_CONTEXT_UNAVAILABLE = "OPERATOR_CONTEXT_UNAVAILABLE"
    OPERATOR_CONTEXT_BUDGET = "OPERATOR_CONTEXT_BUDGET"
    UNSUPPORTED_BINDING = "UNSUPPORTED_BINDING"


def guidance_candidates(task: TaskRequest) -> tuple[RepositoryPath, ...]:
    """Compute ancestors only, with deterministic case-insensitive deduplication."""
    directories = {"": ""}
    for target in sorted(task.targets, key=lambda item: item.path.value):
        parts = target.path.value.split("/")[:-1]
        if any(part.startswith(".") for part in parts):
            raise ValueError("hidden guidance ancestry is unsupported")
        for depth in range(1, len(parts) + 1):
            directory = "/".join(parts[:depth])
            directories.setdefault(directory.casefold(), directory)
    ordered = sorted(
        directories.values(),
        key=lambda path: (len(path.split("/")) if path else 0, path.casefold()),
    )
    excluded = {target.path.value.casefold() for target in task.targets}
    excluded.update(path.value.casefold() for path in task.context)
    paths = [
        f"{directory}/{name}" if directory else name
        for name in ("AGENTS.md", "CLAUDE.md")
        for directory in ordered
    ] + ["CONTRIBUTING.md", "README.md"]
    return tuple(
        RepositoryPath(path) for path in paths if path.casefold() not in excluded
    )


@dataclass(frozen=True, slots=True)
class GuidanceItem:
    path: RepositoryPath
    status: GuidanceStatus
    size_bytes: int | None = None
    digest: ContentDigest | None = None

    def __post_init__(self) -> None:
        if (
            type(self.path) is not RepositoryPath
            or type(self.status) is not GuidanceStatus
        ):
            raise TypeError("typed guidance path and status required")
        if any(part.startswith(".") for part in self.path.value.split("/")):
            raise ValueError("hidden guidance paths are unsupported")
        if self.size_bytes is not None and (
            type(self.size_bytes) is not int or self.size_bytes < 0
        ):
            raise ValueError("nonnegative byte size required")
        if self.digest is not None and type(self.digest) is not ContentDigest:
            raise TypeError("typed content digest required")
        if (self.size_bytes is None) != (self.digest is None):
            raise ValueError("observed size and digest belong together")
        if self.status is GuidanceStatus.INCLUDED and self.size_bytes is None:
            raise ValueError("inclusion requires observed metadata")


@dataclass(frozen=True, slots=True)
class GuidanceInventory:
    items: tuple[GuidanceItem, ...]
    operator_count: int = 0
    operator_bytes: int = 0

    def __post_init__(self) -> None:
        if type(self.items) is not tuple or any(
            type(item) is not GuidanceItem for item in self.items
        ):
            raise TypeError("immutable guidance items required")
        if len({item.path.value.casefold() for item in self.items}) != len(self.items):
            raise ValueError("duplicate guidance paths")
        for value, maximum in (
            (self.operator_count, MAX_REFERENCE_FILES),
            (self.operator_bytes, MAX_REFERENCE_BYTES),
        ):
            if type(value) is not int or not 0 <= value <= maximum:
                raise ValueError("operator context exceeds reference bounds")
        included = [
            item for item in self.items if item.status is GuidanceStatus.INCLUDED
        ]
        if (
            len(included) > MAX_GUIDANCE_FILES
            or len(included) + self.operator_count > MAX_REFERENCE_FILES
            or self.included_bytes > MAX_GUIDANCE_BYTES
            or self.included_bytes + self.operator_bytes > MAX_REFERENCE_BYTES
            or any((item.size_bytes or 0) > MAX_FILE_BYTES for item in included)
            or any(
                item.status is not GuidanceStatus.NOT_CONSIDERED_LIMIT
                for item in self.items[MAX_CANDIDATES:]
            )
        ):
            raise ValueError("guidance selection exceeds bounds")

    @property
    def included_paths(self) -> tuple[RepositoryPath, ...]:
        return tuple(
            item.path for item in self.items if item.status is GuidanceStatus.INCLUDED
        )

    @property
    def included_bytes(self) -> int:
        return sum(
            item.size_bytes or 0
            for item in self.items
            if item.status is GuidanceStatus.INCLUDED
        )

    @property
    def exhausted(self) -> bool:
        return (
            len(self.included_paths) >= MAX_GUIDANCE_FILES
            or len(self.included_paths) + self.operator_count >= MAX_REFERENCE_FILES
            or self.included_bytes >= MAX_GUIDANCE_BYTES
            or self.included_bytes + self.operator_bytes >= MAX_REFERENCE_BYTES
        )


def select(
    items: tuple[GuidanceItem, ...],
    *,
    operator_count: int = 0,
    operator_bytes: int = 0,
) -> GuidanceInventory:
    """Apply whole-file budgets to observations in candidate priority order."""
    GuidanceInventory((), operator_count, operator_bytes)
    count = 0
    size = 0
    selected: list[GuidanceItem] = []
    for index, item in enumerate(items):
        status = item.status
        if index >= MAX_CANDIDATES:
            status = GuidanceStatus.NOT_CONSIDERED_LIMIT
        elif (
            count >= MAX_GUIDANCE_FILES
            or count + operator_count >= MAX_REFERENCE_FILES
            or size >= MAX_GUIDANCE_BYTES
            or size + operator_bytes >= MAX_REFERENCE_BYTES
        ):
            status = GuidanceStatus.EXCLUDED_BUDGET
        elif item.size_bytes is not None and item.size_bytes > MAX_FILE_BYTES:
            status = GuidanceStatus.EXCEEDS_FILE_BOUND
        elif status is GuidanceStatus.INCLUDED and (
            size + (item.size_bytes or 0) > MAX_GUIDANCE_BYTES
            or size + (item.size_bytes or 0) + operator_bytes > MAX_REFERENCE_BYTES
        ):
            status = GuidanceStatus.EXCLUDED_BUDGET
        selected.append(GuidanceItem(item.path, status, item.size_bytes, item.digest))
        if status is GuidanceStatus.INCLUDED:
            count += 1
            size += item.size_bytes or 0
    return GuidanceInventory(tuple(selected), operator_count, operator_bytes)


def guidance_summary(inventory: GuidanceInventory) -> str:
    lines = ["repository guidance: discovered (read-only; confirm below)"]
    for item in inventory.items:
        size = str(item.size_bytes) if item.size_bytes is not None else "unknown"
        digest = item.digest.value if item.digest is not None else "unavailable"
        lines.append(
            f"{item.path.value}: {item.status.value}; bytes={size}; digest={digest}"
        )
    return "\n".join(lines)
