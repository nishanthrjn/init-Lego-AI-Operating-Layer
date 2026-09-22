"""Immutable supplied-data contracts, not filesystem references or authority.

Bounds are local implementation limits, measured in Unicode code points.
Labels are never dereferenced. No canonical Snapshot/Evidence claim is made.
"""

from dataclasses import dataclass, field


def _path_label(value: str) -> None:
    if type(value) is not str:
        raise TypeError("path label must be str")
    if not 1 <= len(value) <= 240:
        raise ValueError("path label length must be within 1..240")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("path label cannot contain control characters")
    if "\\" in value or ":" in value:
        raise ValueError("path label requires portable slash-separated components")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("path label requires nonempty relative components")


def _integer(value: int, maximum: int) -> None:
    if type(value) is not int:
        raise TypeError("bound or coordinate must be int")
    if not 1 <= value <= maximum:
        raise ValueError("bound or coordinate outside supported range")


@dataclass(frozen=True, slots=True)
class RepositoryText:
    """One caller-supplied text file; label is not a host access target."""

    path: str = field(repr=False)
    text: str = field(repr=False)

    def __post_init__(self) -> None:
        _path_label(self.path)
        if type(self.text) is not str:
            raise TypeError("repository text must be str")
        if len(self.text) > 65_536:
            raise ValueError("repository text exceeds 65536 code points")


@dataclass(frozen=True, slots=True)
class InspectionRequest:
    """Closed, bounded supplied input; no implicit acquisition or defaults."""

    files: tuple[RepositoryText, ...] = field(repr=False)
    query: str = field(repr=False)
    max_matches: int

    def __post_init__(self) -> None:
        if type(self.files) is not tuple:
            raise TypeError("files must be an immutable tuple")
        if len(self.files) > 128:
            raise ValueError("at most 128 files are supported")
        if any(type(item) is not RepositoryText for item in self.files):
            raise TypeError("files must contain RepositoryText values")
        if sum(len(item.text) for item in self.files) > 1_048_576:
            raise ValueError("total text exceeds 1048576 code points")
        if len({item.path for item in self.files}) != len(self.files):
            raise ValueError("duplicate path labels are unsupported")
        if type(self.query) is not str:
            raise TypeError("query must be str")
        if not 1 <= len(self.query) <= 256 or "\n" in self.query or "\r" in self.query:
            raise ValueError("query must contain 1..256 code points without CR/LF")
        _integer(self.max_matches, 1_000)


@dataclass(frozen=True, slots=True)
class RepositoryMatch:
    """First match on a line; coordinates are one-based Unicode positions."""

    path: str = field(repr=False)
    line: int
    column: int

    def __post_init__(self) -> None:
        _path_label(self.path)
        _integer(self.line, 65_537)
        _integer(self.column, 65_536)


@dataclass(frozen=True, slots=True)
class InspectionResult:
    """Coordinates only; truncated means at least one matching line was omitted."""

    matches: tuple[RepositoryMatch, ...] = field(repr=False)
    truncated: bool

    def __post_init__(self) -> None:
        if type(self.matches) is not tuple:
            raise TypeError("matches must be an immutable tuple")
        if len(self.matches) > 1_000:
            raise ValueError("at most 1000 matches are supported")
        if any(type(item) is not RepositoryMatch for item in self.matches):
            raise TypeError("matches must contain RepositoryMatch values")
        if type(self.truncated) is not bool:
            raise TypeError("truncated must be bool")
        if self.truncated and not self.matches:
            raise ValueError("truncation requires at least one returned match")
        positions = tuple((item.path, item.line) for item in self.matches)
        if positions != tuple(sorted(set(positions))):
            raise ValueError("matches must have unique ordered path/line coordinates")
