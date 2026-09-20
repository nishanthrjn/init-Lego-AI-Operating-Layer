"""Opaque nominal identities, not credentials or evidence of authority.

Reference input is exact built-in text of 1–256 Unicode code points. This
local protection bound does not define canonical identity or resource rights.
No whitespace, case, Unicode or UUID normalization is performed.
"""

from dataclasses import dataclass, field


def _validate(value: str) -> None:
    # Reject str subclasses too: retain only an immutable built-in representation.
    if type(value) is not str:
        raise TypeError("identity representation must be text")
    if not 1 <= len(value) <= 256:
        raise ValueError("identity representation must contain 1–256 characters")


@dataclass(frozen=True, slots=True)
class TenantId:
    """An opaque tenant identity; construction does not establish tenant context."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class PrincipalId:
    """An opaque principal identity; construction does not authenticate anyone."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class ApplicationId:
    """Opaque application identity, not a declaration revision."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class OperationId:
    """One logical operation; not an execution attempt or submission."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class RequestId:
    """One submission, distinct from its logical operation."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class CorrelationId:
    """Interaction-group identity, never a deduplication guarantee."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class TraceId:
    """Trace attribution only; no logging or authority is established."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)
