"""Safe failure categories; no rollback, no-effect or retry assertion."""

from enum import Enum


class SandboxFailure(Enum):
    RUNTIME_UNAVAILABLE = "sandbox runtime unavailable"
    ENVIRONMENT_UNAVAILABLE = "pinned sandbox environment unavailable"
    UNSUPPORTED = "required sandbox controls unsupported"
    PREPARATION = "sandbox preparation failed"
    CONTROL = "sandbox control or protocol failed"
    TIMEOUT = "sandbox deadline exceeded"
    CANCELLED = "sandbox cancellation requested"
    RESOURCE_LIMIT = "sandbox memory limit terminated workload"
    OUTPUT_LIMIT = "sandbox capture byte limit exceeded"
    ARTIFACT = "sandbox artifact missing, unsafe or beyond bounds"
    CLEANUP = "sandbox cleanup unconfirmed; operator reconciliation required"


class SandboxError(RuntimeError):
    """Causes are trusted-operator diagnostics, not Agent-facing serialization.

    Recovery IDs are generated resource names, never caller paths or secrets.
    CLEANUP can supersede another failure, retained in the exception chain.
    """

    def __init__(
        self, reason: SandboxFailure, recovery_ids: tuple[str, ...] = ()
    ) -> None:
        if type(reason) is not SandboxFailure:
            raise TypeError("sandbox failure requires SandboxFailure")
        if type(recovery_ids) is not tuple or len(recovery_ids) > 3:
            raise ValueError("invalid recovery identifiers")
        for identity in recovery_ids:
            if (
                type(identity) is not str
                or not identity.startswith("legoai-m6-")
                or len(identity) > 64
                or any(
                    char not in "abcdefghijklmnopqrstuvwxyz0123456789-"
                    for char in identity
                )
            ):
                raise ValueError("invalid recovery identifier")
        self.reason = reason
        self.recovery_ids = recovery_ids
        super().__init__(reason.value)
