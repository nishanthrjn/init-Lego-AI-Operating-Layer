"""Initial error vocabulary, not exceptions or a complete CTR-011 envelope.

Owner result contracts later supply operation/subject, time, safe diagnostics,
named effects and conditional retry constraints. No retry decision lives here.
"""

from dataclasses import dataclass, field
from enum import Enum

from legoai.kernel.identity import _validate
from legoai.kernel.references import OperationRef


class ErrorCategory(Enum):
    VALIDATION_ERROR = "ValidationError"
    VERSION_MISMATCH = "VersionMismatch"
    TENANT_VIOLATION = "TenantViolation"
    CONFLICT = "Conflict"
    DEPENDENCY_FAILURE = "DependencyFailure"
    # Gate-2 M4: CONTRACTS' Base error table names these as distinct
    # canonical categories from the five above; M4's current-authority
    # evaluation is their first real consumer (mirroring how F4/F5 grew
    # this enum incrementally for their own first real consumers).
    AUTHORIZATION_DENIED = "AuthorizationDenied"
    POLICY_VIOLATION = "PolicyViolation"
    # Gate-2 M10: ADR-015 SS16 names these among the "existing canonical
    # categories" a supervised Coordinator maps known causes onto.
    # DEADLINE_EXCEEDED and EXECUTION_FAILURE did not previously exist
    # because no earlier batch was a genuine consumer; M10's deadline
    # enforcement and unexpected-internal-fault mapping are their first real
    # consumers (mirroring how M4 grew this enum for its own first
    # consumer, above).
    DEADLINE_EXCEEDED = "DeadlineExceeded"
    EXECUTION_FAILURE = "ExecutionFailure"


class Recoverability(Enum):
    TERMINAL = "terminal"
    POTENTIALLY_RETRYABLE = "potentially retryable"
    REQUIRES_INTERVENTION = "requires intervention"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ErrorCause:
    """Safe attributed category and enclosing-record key, never raw traceback."""

    category: ErrorCategory
    operation: OperationRef
    record_key: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.category) is not ErrorCategory:
            raise TypeError("cause requires ErrorCategory")
        if type(self.operation) is not OperationRef:
            raise TypeError("cause requires OperationRef")
        _validate(self.record_key)


@dataclass(frozen=True, slots=True)
class ErrorDetail:
    """Immutable classification/cause component, not an operational error result.

    Callers supply every axis explicitly. Causes retain material secondary
    failures too; their accessibility must be checked by the disclosing owner.
    """

    category: ErrorCategory
    recoverability: Recoverability
    causes: tuple[ErrorCause, ...]

    def __post_init__(self) -> None:
        if type(self.category) is not ErrorCategory:
            raise TypeError("error detail requires ErrorCategory")
        if type(self.recoverability) is not Recoverability:
            raise TypeError("error detail requires Recoverability")
        if type(self.causes) is not tuple or any(
            type(cause) is not ErrorCause for cause in self.causes
        ):
            raise TypeError("causes must be an immutable tuple of ErrorCause")
