"""Inert Agent identity and accepted-output constraints, not authority."""

from dataclasses import dataclass, field
from enum import Enum

from legoai.kernel.identity import _validate


def _bound(value: int, ceiling: int) -> None:
    if type(value) is not int:
        raise TypeError("bound must be an integer")
    if not 1 <= value <= ceiling:
        raise ValueError("bound outside supported range")


def _text(value: str, maximum: int) -> None:
    if type(value) is not str:
        raise TypeError("Agent text must be built-in str")
    # Reject large text before allocating an encoding; encoded size is at most
    # four times the character ceiling during this validation.
    if not value or len(value) > maximum:
        raise ValueError("Agent text is empty or oversized")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError("Agent text must be valid UTF-8") from exc
    if len(encoded) > maximum or value.isspace():
        raise ValueError("Agent text is blank or oversized")


@dataclass(frozen=True, slots=True)
class AgentId:
    """Definition identity; never an ExecutionId, Role or Principal."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class AgentOutputContract:
    """Nonblank strict UTF-8 text, at most max_bytes (1–65536)."""

    max_bytes: int

    def __post_init__(self) -> None:
        _bound(self.max_bytes, 65536)

    def validate(self, content: str) -> None:
        _text(content, self.max_bytes)


class AgentExecutionStatus(Enum):
    """Per-request outcome; not canonical Agent instance lifecycle states."""

    ROUTING_FAILED = "routing_failed"
    MODEL_FAILED = "model_failed"
    OUTPUT_INVALID = "output_invalid"
    SUCCEEDED = "succeeded"
