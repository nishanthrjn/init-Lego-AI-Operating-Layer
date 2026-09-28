"""The source-linked reading contract."""

from __future__ import annotations

import dataclasses
from decimal import Decimal

from legoai_collation.normalize import normalize
from legoai_collation.values import (
    ChoiceRule,
    ComparisonContext,
    DecimalRule,
    ObservationState,
    RawInput,
    SourceRef,
    TextRule,
    ValueKind,
)


@dataclasses.dataclass(frozen=True, slots=True)
class Reading:
    """One source's value for one comparison context, with its own rule.

    ``state``, ``kind`` and ``value`` are computed from ``raw`` and ``rule``
    at construction, so a reading can never disagree with its rule. The raw
    input keeps the original representation; ``value`` is the canonical
    normalized value. Different sources may use different rules for the same
    context; collation checks that they are compatible.
    """

    ref: SourceRef
    context: ComparisonContext
    raw: RawInput
    rule: TextRule | DecimalRule | ChoiceRule
    state: ObservationState = dataclasses.field(init=False)
    kind: ValueKind = dataclasses.field(init=False)
    value: str | Decimal | None = dataclasses.field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.ref) is not SourceRef:
            raise TypeError("reading requires SourceRef")
        if type(self.context) is not ComparisonContext:
            raise TypeError("reading requires ComparisonContext")
        result = normalize(self.raw, self.rule)
        object.__setattr__(self, "state", result.state)
        object.__setattr__(self, "kind", result.kind)
        object.__setattr__(self, "value", result.value)
