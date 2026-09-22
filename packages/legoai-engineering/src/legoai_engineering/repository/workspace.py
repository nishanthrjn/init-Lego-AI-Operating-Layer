"""Immutable workspace inputs/results, separate from local host configuration."""

from dataclasses import dataclass, field
from enum import Enum

from legoai_engineering.repository.errors import WorkspaceBoundaryError
from legoai_engineering.repository.values import RepositoryText


@dataclass(frozen=True, slots=True)
class RepositoryPath:
    """Portable relative path; a stricter access subset of M1 text labels."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.value) is not str:
            raise TypeError("repository path requires str")
        try:
            RepositoryText(self.value, "")  # Reuse M1 label grammar unchanged.
        except ValueError as error:
            raise WorkspaceBoundaryError() from error
        for part in self.value.split("/"):
            stem = part.split(".", 1)[0].upper()
            device = stem in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
            numbered_device = (
                len(stem) == 4
                and stem[:3] in {"COM", "LPT"}
                and stem[3] in "123456789¹²³"
            )
            if (
                part.endswith((".", " "))
                or any(char in '<>"|?*' for char in part)
                or device
                or numbered_device
            ):
                raise WorkspaceBoundaryError()


@dataclass(frozen=True, slots=True)
class WorkspacePolicy:
    """Finite per-call limits; exclusions apply to listing and direct reading.

    Directory scans count excluded entries too. No recursion is performed.
    Depth counts components in a requested or returned repository path.
    """

    max_read_bytes: int
    max_text_chars: int
    max_entries: int
    max_depth: int
    excluded_names: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, ceiling in (
            (self.max_read_bytes, 262_144),
            (self.max_text_chars, 65_536),
            (self.max_entries, 4_096),
            (self.max_depth, 32),
        ):
            if type(value) is not int:
                raise TypeError("workspace limits require int")
            if not 1 <= value <= ceiling:
                raise ValueError("workspace limit outside supported range")
        if type(self.excluded_names) is not tuple:
            raise TypeError("exclusions require an immutable tuple")
        if len(self.excluded_names) > 32:
            raise ValueError("at most 32 exclusion names are supported")
        for name in self.excluded_names:
            RepositoryPath(name)
            if "/" in name:
                raise ValueError("exclusions must be single components")
        if len({name.casefold() for name in self.excluded_names}) != len(
            self.excluded_names
        ):
            raise ValueError("duplicate case-insensitive exclusions")


class WorkspaceEntryKind(Enum):
    FILE = "file"
    DIRECTORY = "directory"


@dataclass(frozen=True, slots=True)
class WorkspaceEntry:
    path: RepositoryPath
    kind: WorkspaceEntryKind

    def __post_init__(self) -> None:
        if type(self.path) is not RepositoryPath:
            raise TypeError("workspace entry requires RepositoryPath")
        if type(self.kind) is not WorkspaceEntryKind:
            raise TypeError("workspace entry requires WorkspaceEntryKind")
