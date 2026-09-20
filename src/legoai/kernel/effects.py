"""CTR-009 extent of a named effect, separate from success and retry policy."""

from enum import Enum


class EffectExtent(Enum):
    NONE = "none"
    PARTIAL = "partial"
    COMPLETED = "completed"
    UNKNOWN = "unknown"
