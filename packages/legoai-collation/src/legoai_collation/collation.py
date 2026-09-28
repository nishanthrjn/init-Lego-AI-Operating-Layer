"""Pure single-field precedence collation.

``collate_field`` validates the whole input before computing anything, keeps
every reading as a candidate, and decides the status only from admissible
readings: those that are PRESENT and come from a ranked source. The result is
independent of input order.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

from legoai_collation.errors import (
    DuplicateReadingError,
    IncompatibleRulesError,
    LimitExceededError,
    MixedContextError,
)
from legoai_collation.reading import Reading
from legoai_collation.values import (
    MAX_READINGS,
    Admission,
    ChoiceRule,
    CollationStatus,
    ComparisonContext,
    ObservationState,
    PrecedencePolicy,
    ReasonCode,
    SourceId,
    SourceRef,
    ValueKind,
)

COLLATION_RULE = "legoai.collation.precedence/1"


@dataclasses.dataclass(frozen=True, slots=True)
class Candidate:
    """A retained reading, its rank (None if unranked) and its admission."""

    reading: Reading
    rank: int | None
    admission: Admission


@dataclasses.dataclass(frozen=True, slots=True)
class Reason:
    """A structured reason and the readings it concerns, in candidate order."""

    code: ReasonCode
    refs: tuple[SourceRef, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class Collation:
    """The outcome for one comparison context.

    ``distinct_values`` lists every distinct admissible value in candidate
    order; ``has_disagreement`` is true exactly when there is more than one.
    AGREED means the admissible sources agree, not that the value is
    verified. PRECEDENCE_SELECTED selects the unique best-ranked value and
    keeps every disagreeing alternative. CONFLICT selects nothing.
    """

    context: ComparisonContext
    policy_version: str
    status: CollationStatus
    selected: str | Decimal | None
    has_disagreement: bool
    distinct_values: tuple[str | Decimal, ...]
    candidates: tuple[Candidate, ...]
    reasons: tuple[Reason, ...]
    rule: str = COLLATION_RULE

    def __post_init__(self) -> None:
        if type(self.status) is not CollationStatus:
            raise TypeError("collation requires CollationStatus")
        if self.has_disagreement != (len(self.distinct_values) > 1):
            raise ValueError("has_disagreement must reflect distinct_values")
        selecting = self.status in (
            CollationStatus.AGREED,
            CollationStatus.PRECEDENCE_SELECTED,
        )
        if (self.selected is not None) != selecting:
            raise ValueError("only AGREED and PRECEDENCE_SELECTED select a value")
        disagreeing = self.status in (
            CollationStatus.PRECEDENCE_SELECTED,
            CollationStatus.CONFLICT,
        )
        if self.status is CollationStatus.AGREED and self.has_disagreement:
            raise ValueError("AGREED cannot have disagreement")
        if disagreeing and not self.has_disagreement:
            raise ValueError("PRECEDENCE_SELECTED and CONFLICT require disagreement")


def _value_key(value: str | Decimal) -> object:
    # Values are canonical, so representation equality is value equality.
    return value.as_tuple() if type(value) is Decimal else value


def _check_compatible(readings: tuple[Reading, ...]) -> None:
    first = readings[0]
    for index, reading in enumerate(readings[1:], start=1):
        if reading.kind is not first.kind:
            raise IncompatibleRulesError(
                f"reading {index} produces {reading.kind.value} values, "
                f"not {first.kind.value}"
            )
        if (
            first.kind is ValueKind.CHOICE
            and type(first.rule) is ChoiceRule
            and type(reading.rule) is ChoiceRule
            and reading.rule.vocabulary != first.rule.vocabulary
        ):
            raise IncompatibleRulesError(
                f"reading {index} uses a different choice vocabulary"
            )


def _check_identity(readings: tuple[Reading, ...]) -> None:
    per_source: dict[SourceId, int] = {}
    for reading in readings:
        source = reading.ref.source
        per_source[source] = per_source.get(source, 0) + 1
    seen: dict[tuple[SourceId, str | None], int] = {}
    for index, reading in enumerate(readings):
        identity = (reading.ref.source, reading.ref.locator)
        if identity in seen:
            raise DuplicateReadingError(
                f"readings {seen[identity]} and {index} share source and locator"
            )
        if reading.ref.locator is None and per_source[reading.ref.source] > 1:
            raise DuplicateReadingError(
                f"reading {index} needs a locator: its source supplies several readings"
            )
        seen[identity] = index


def _candidate(reading: Reading, policy: PrecedencePolicy) -> Candidate:
    rank = policy.rank_of(reading.ref.source)
    if rank is None:
        admission = Admission.UNRANKED_SOURCE
    elif reading.state is ObservationState.INVALID:
        admission = Admission.INVALID
    elif reading.state is ObservationState.PRESENT:
        admission = Admission.ADMISSIBLE
    else:
        admission = Admission.NOT_PRESENT
    return Candidate(reading, rank, admission)


def _order(candidate: Candidate) -> tuple[bool, int, str, bool, str]:
    ref = candidate.reading.ref
    rank = candidate.rank
    return (
        rank is None,
        rank if rank is not None else 0,
        ref.source.value,
        ref.locator is not None,
        ref.locator or "",
    )


def _distinct(candidates: list[Candidate]) -> list[str | Decimal]:
    values: list[str | Decimal] = []
    keys: set[object] = set()
    for candidate in candidates:
        value = candidate.reading.value
        if value is not None and _value_key(value) not in keys:
            keys.add(_value_key(value))
            values.append(value)
    return values


def _refs(candidates: list[Candidate]) -> tuple[SourceRef, ...]:
    return tuple(candidate.reading.ref for candidate in candidates)


def collate_field(
    context: ComparisonContext,
    readings: tuple[Reading, ...],
    policy: PrecedencePolicy,
) -> Collation:
    """Collate readings of one field under a precedence policy.

    Raises before any computation: ``TypeError`` for wrong types (``readings``
    must be a tuple), ``LimitExceededError`` above ``MAX_READINGS``,
    ``MixedContextError`` for a different context, ``IncompatibleRulesError``
    for a different value kind or choice vocabulary, and
    ``DuplicateReadingError`` for a repeated ``(source, locator)`` identity or
    a source with several readings where one lacks a locator.
    """
    if type(context) is not ComparisonContext:
        raise TypeError("collation requires ComparisonContext")
    if type(readings) is not tuple:
        raise TypeError("readings must be a tuple")
    if type(policy) is not PrecedencePolicy:
        raise TypeError("collation requires PrecedencePolicy")
    if len(readings) > MAX_READINGS:
        raise LimitExceededError(f"readings exceed {MAX_READINGS}")
    for index, reading in enumerate(readings):
        if type(reading) is not Reading:
            raise TypeError(f"reading {index} is not a Reading")
        if reading.context != context:
            raise MixedContextError(
                f"reading {index} has a different comparison context"
            )
    if readings:
        _check_compatible(readings)
        _check_identity(readings)

    candidates = sorted(
        (_candidate(reading, policy) for reading in readings), key=_order
    )
    admissible = [c for c in candidates if c.admission is Admission.ADMISSIBLE]
    distinct = _distinct(admissible)
    reasons: list[Reason] = []
    selected: str | Decimal | None = None

    if admissible:
        best = min(c.rank for c in admissible if c.rank is not None)
        leaders = [c for c in admissible if c.rank == best]
        leading_values = _distinct(leaders)
        if len(distinct) == 1:
            status = CollationStatus.AGREED
            selected = distinct[0]
            reasons.append(Reason(ReasonCode.AGREEMENT, _refs(admissible)))
        elif len(leading_values) == 1:
            status = CollationStatus.PRECEDENCE_SELECTED
            selected = leading_values[0]
            key = _value_key(selected)
            others = [
                c
                for c in admissible
                if c.reading.value is not None and _value_key(c.reading.value) != key
            ]
            reasons.append(
                Reason(ReasonCode.PRECEDENCE_OVER_DISAGREEMENT, _refs(leaders))
            )
            reasons.append(Reason(ReasonCode.DISAGREEING_ALTERNATIVE, _refs(others)))
        else:
            status = CollationStatus.CONFLICT
            reasons.append(Reason(ReasonCode.EQUAL_RANK_DISAGREEMENT, _refs(leaders)))
    elif any(c.admission is Admission.INVALID for c in candidates):
        status = CollationStatus.INVALID
    else:
        status = CollationStatus.MISSING

    for admission, code in (
        (Admission.INVALID, ReasonCode.INVALID_OBSERVATION),
        (Admission.NOT_PRESENT, ReasonCode.NOT_PRESENT),
        (Admission.UNRANKED_SOURCE, ReasonCode.UNRANKED_SOURCE_EXCLUDED),
    ):
        matching = [c for c in candidates if c.admission is admission]
        if matching:
            reasons.append(Reason(code, _refs(matching)))
    if not readings:
        reasons.append(Reason(ReasonCode.NO_OBSERVATIONS, ()))

    return Collation(
        context=context,
        policy_version=policy.version,
        status=status,
        selected=selected,
        has_disagreement=len(distinct) > 1,
        distinct_values=tuple(distinct),
        candidates=tuple(candidates),
        reasons=tuple(reasons),
    )
