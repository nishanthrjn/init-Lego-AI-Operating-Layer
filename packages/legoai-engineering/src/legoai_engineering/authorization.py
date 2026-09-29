"""Refusal of an authorized engineering effect before it starts (ADR-018 CR-3)."""

from enum import Enum


class EffectAuthorizationFailure(Enum):
    DENIED = "current authorization denied the engineering effect"
    UNAVAILABLE = "current authorization could not be established"


class EffectAuthorizationError(RuntimeError):
    """Raised before the wrapped effect: the inner adapter was never called.

    No write, check process or sandbox execution was started. UNAVAILABLE is a
    governance dependency failure, never a denial or an allow. Retrying cannot
    succeed until the operator's current authority changes.
    """

    def __init__(self, reason: EffectAuthorizationFailure) -> None:
        if type(reason) is not EffectAuthorizationFailure:
            raise TypeError("effect authorization error requires failure reason")
        self.reason = reason
        super().__init__(reason.value)
