"""Bounded, display-safe diagnostics for rejected engineering Agent output.

A diagnostic names one closed rejection reason and, where known, a location
built only from the Agent's fixed output schema: field names from the schema
and array indexes, for example `changes[1].operation`. It never carries model
text, keys the model invented, prompts or exception messages, so a caller may
show and keep it. Diagnostics explain a rejection; they never change what is
valid, never repair output and never cause a retry.
"""

from dataclasses import dataclass
from enum import Enum

__all__ = ["OutputDiagnostic", "OutputRejected", "OutputRejection"]
_LOCATION = frozenset("abcdefghijklmnopqrstuvwxyz_.[]0123456789")


class OutputRejection(Enum):
    OUTPUT_CONTRACT = "the Agent output contract rejected the reply (size or text)"
    JSON_DOCUMENT_INVALID = "the reply is not exactly one JSON document"
    DUPLICATE_FIELD = "a JSON object repeats a field name"
    REQUIRED_FIELD_MISSING = "a required field is missing"
    UNKNOWN_FIELD = "an object has a field outside the output schema"
    FIELD_TYPE_INVALID = "a field has the wrong JSON type"
    ARRAY_BOUNDS_EXCEEDED = "an array has more items than allowed"
    ENUM_INVALID = "a field is not one of its allowed values"
    PATH_INVALID = "a proposed path is not a valid repository path"
    PATH_OUT_OF_SCOPE = "a proposed path or operation is outside the requested targets"
    VALUE_INVALID = "a value violates its domain rules (blank, bounds or consistency)"
    FINDING_REFERENCE_INVALID = "a finding cites material that was not supplied"


@dataclass(frozen=True, slots=True)
class OutputDiagnostic:
    rejection: OutputRejection
    location: str | None = None

    def __post_init__(self) -> None:
        if type(self.rejection) is not OutputRejection:
            raise TypeError("output diagnostic requires OutputRejection")
        if self.location is not None and (
            type(self.location) is not str
            or not 1 <= len(self.location) <= 64
            or not set(self.location) <= _LOCATION
        ):
            raise ValueError("diagnostic location must be a schema locator")


class OutputRejected(ValueError):
    """Raised by an Agent parser at the check that rejected its output."""

    def __init__(self, rejection: OutputRejection, location: str | None = None) -> None:
        self.diagnostic = OutputDiagnostic(rejection, location)
        super().__init__(rejection.name)
