"""Narrow Evidence-owned values needed by an owner's F4 source-submission duty.

Not custody: no store, no retention engine, no receipt/acknowledgment, no
hash chain, no export, no sink. This module only describes what evidence a
duty requires -- it never represents evidence actually supplied, since no
custody mechanism exists yet to receive it (ADR-009 custody remains Gate-2
work; see the Gate-1 plan SS10.4).
"""

from dataclasses import dataclass, field

from legoai.kernel.identity import _validate
from legoai.kernel.references import ConfigurationRevisionRef


@dataclass(frozen=True, slots=True)
class EvidenceRequirement:
    """A description of evidence that must eventually be supplied to resolve
    a duty -- not the evidence itself, and not a custody acknowledgment.

    subject pins the exact immutable revision the requirement is about, so
    an owner cannot silently reinterpret which published fact still needs
    evidence as later revisions are published.
    """

    subject: ConfigurationRevisionRef
    description: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.subject) is not ConfigurationRevisionRef:
            raise TypeError("evidence requirement requires ConfigurationRevisionRef")
        _validate(self.description)
