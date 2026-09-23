"""Inert bounded check requests and exact exit-status interpretation."""

from dataclasses import dataclass, field
from enum import Enum

from legoai_engineering.repository.workspace import RepositoryPath


class CheckKind(Enum):
    PYTEST = "pytest"
    RUFF_CHECK = "ruff_check"
    RUFF_FORMAT_CHECK = "ruff_format_check"
    MYPY = "mypy"


class CheckOutcome(Enum):
    PASSED = "passed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    NO_TESTS = "no_tests"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class CheckRequest:
    kind: CheckKind
    targets: tuple[RepositoryPath, ...]

    def __post_init__(self) -> None:
        if type(self.kind) is not CheckKind:
            raise TypeError("check requires CheckKind")
        if type(self.targets) is not tuple:
            raise TypeError("targets require an immutable tuple of RepositoryPath")
        if not 1 <= len(self.targets) <= 32:
            raise ValueError("check requires 1..32 explicit targets")
        if any(type(target) is not RepositoryPath for target in self.targets):
            raise TypeError("targets require RepositoryPath values")
        names = [target.value.casefold() for target in self.targets]
        if len(set(names)) != len(names):
            raise ValueError("duplicate check targets")
        for target in self.targets:
            try:
                target.value.encode("utf-8", errors="strict")
            except UnicodeEncodeError as error:
                raise ValueError("target must be UTF-8 encodable") from error


@dataclass(frozen=True, slots=True)
class CheckPolicy:
    """Per-call limits, independent for each captured byte stream."""

    timeout_seconds: int = 60
    max_output_bytes: int = 262_144

    def __post_init__(self) -> None:
        for value, maximum in (
            (self.timeout_seconds, 3600),
            (self.max_output_bytes, 1_048_576),
        ):
            if type(value) is not int:
                raise TypeError("check limits require int")
            if not 1 <= value <= maximum:
                raise ValueError("check limit outside supported range")


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Complete bounded raw diagnostics; no lossy decoding or success coercion."""

    kind: CheckKind
    exit_code: int
    stdout: bytes = field(repr=False)
    stderr: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.kind) is not CheckKind or type(self.exit_code) is not int:
            raise TypeError("result requires CheckKind and integer exit code")
        if not -(2**31) <= self.exit_code <= 2**32 - 1:
            raise ValueError("exit code outside native process range")
        for output in (self.stdout, self.stderr):
            if type(output) is not bytes:
                raise TypeError("check output requires bytes")
            if len(output) > 1_048_576:
                raise ValueError("check output exceeds hard limit")

    @property
    def outcome(self) -> CheckOutcome:
        if self.exit_code == 0:
            return CheckOutcome.PASSED
        if self.exit_code == 1:
            return CheckOutcome.FAILED
        if self.kind is CheckKind.PYTEST:
            if self.exit_code == 2:
                return CheckOutcome.INTERRUPTED
            if self.exit_code == 5:
                return CheckOutcome.NO_TESTS
        return CheckOutcome.ERROR
