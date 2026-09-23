"""Synchronous mechanism boundary; governance and admission remain external."""

from typing import Protocol

from legoai_engineering.sandbox.values import SandboxRequest, SandboxResult


class CancellationSignal(Protocol):
    """Caller-owned cooperative signal, compatible with threading.Event."""

    def is_set(self) -> bool: ...


class SandboxExecutionPort(Protocol):
    """No implicit retries; cancellation/timeout must include sandbox termination.

    Signal polling cannot guarantee cleanup after host/interpreter termination.
    Unsupported confinement fails closed. Returned content remains untrusted.
    """

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult: ...
