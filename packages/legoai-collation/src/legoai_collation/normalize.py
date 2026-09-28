"""Pure text, decimal and choice normalization.

Every normalizer handles ABSENT and NULL first, identically for all rules:
they yield the ABSENT or NULL state with no value, before any type check.
BLANK means supplied text that is empty after the rule's text handling (a
decimal rule has none, so only ``""`` is BLANK for it). Any other raw kind a
rule does not accept yields INVALID. Normalization never raises for
unacceptable data; it raises only for wrong argument types.
"""

import re
from decimal import Decimal

from legoai_collation import _decimal
from legoai_collation.values import (
    ChoiceRule,
    DecimalRule,
    Normalized,
    ObservationState,
    RawInput,
    RawKind,
    Rule,
    TextRule,
    ValueKind,
    apply_text_rule,
)

# ASCII digits only, one optional leading minus, optional fraction. No plus
# sign, exponent, whitespace, grouping separator or bare decimal point.
_DECIMAL_TEXT = re.compile(r"(-)?([0-9]+)(?:\.([0-9]+))?", re.ASCII)


def _check(raw: object, rule: object, expected: type) -> RawInput:
    if type(raw) is not RawInput:
        raise TypeError("normalization requires RawInput")
    if type(rule) is not expected:
        raise TypeError(f"normalization requires {expected.__name__}")
    return raw


def _early(raw: RawInput, kind: ValueKind) -> Normalized | None:
    if raw.kind is RawKind.ABSENT:
        return Normalized(ObservationState.ABSENT, kind)
    if raw.kind is RawKind.NULL:
        return Normalized(ObservationState.NULL, kind)
    return None


def normalize_text(raw: RawInput, rule: TextRule) -> Normalized:
    """Only text raw input is accepted; there is no implicit conversion."""
    raw = _check(raw, rule, TextRule)
    early = _early(raw, ValueKind.TEXT)
    if early is not None:
        return early
    if type(raw.value) is not str:
        return Normalized(ObservationState.INVALID, ValueKind.TEXT)
    text = apply_text_rule(raw.value, rule)
    if not text:
        return Normalized(ObservationState.BLANK, ValueKind.TEXT)
    return Normalized(ObservationState.PRESENT, ValueKind.TEXT, text)


def _decimal_from_text(text: str, rule: DecimalRule) -> Decimal | None:
    match = _DECIMAL_TEXT.fullmatch(text)
    if match is None:
        return None
    sign, integer, fraction = match.groups()
    if sign is not None and not rule.allow_negative_sign:
        return None
    if fraction is not None:
        if not rule.allow_fraction:
            return None
        if (
            rule.max_fraction_digits is not None
            and len(fraction) > rule.max_fraction_digits
        ):
            return None
    fraction = fraction or ""
    digits = tuple(ord(character) - 48 for character in integer + fraction)
    return _decimal.canonical(1 if sign else 0, digits, -len(fraction))


def normalize_decimal(raw: RawInput, rule: DecimalRule) -> Normalized:
    """Text, integer and finite Decimal raw input; booleans are INVALID.

    Canonicalization is exact and independent of the ambient decimal context.
    A value outside the canonical bounds, non-finite, or failing a lexical or
    numeric restriction is INVALID.
    """
    raw = _check(raw, rule, DecimalRule)
    early = _early(raw, ValueKind.DECIMAL)
    if early is not None:
        return early
    value: Decimal | None = None
    raw_value = raw.value
    if type(raw_value) is str:
        if raw_value == "":
            return Normalized(ObservationState.BLANK, ValueKind.DECIMAL)
        value = _decimal_from_text(raw_value, rule)
    elif type(raw_value) is int:
        digits = tuple(ord(character) - 48 for character in str(abs(raw_value)))
        value = _decimal.canonical(1 if raw_value < 0 else 0, digits, 0)
    elif type(raw_value) is Decimal:
        value = _decimal.canonical_of(raw_value)
    if value is None or not _numeric_ok(value, rule):
        return Normalized(ObservationState.INVALID, ValueKind.DECIMAL)
    return Normalized(ObservationState.PRESENT, ValueKind.DECIMAL, value)


def _numeric_ok(value: Decimal, rule: DecimalRule) -> bool:
    if rule.integral and not _decimal.is_integral(value):
        return False
    scaled = _decimal.scaled(value)
    if rule.minimum is not None and scaled < _decimal.scaled(rule.minimum):
        return False
    return rule.maximum is None or scaled <= _decimal.scaled(rule.maximum)


def normalize_choice(raw: RawInput, rule: ChoiceRule) -> Normalized:
    """Text (after the rule's text handling), integer and boolean keys."""
    raw = _check(raw, rule, ChoiceRule)
    early = _early(raw, ValueKind.CHOICE)
    if early is not None:
        return early
    key: RawInput | None = None
    if type(raw.value) is str:
        text = apply_text_rule(raw.value, rule.text)
        if not text:
            return Normalized(ObservationState.BLANK, ValueKind.CHOICE)
        key = RawInput(RawKind.TEXT, text)
    elif raw.kind in (RawKind.INTEGER, RawKind.BOOLEAN):
        key = raw
    token = rule.token_for(key) if key is not None else None
    if token is None:
        return Normalized(ObservationState.INVALID, ValueKind.CHOICE)
    return Normalized(ObservationState.PRESENT, ValueKind.CHOICE, token)


def normalize(raw: RawInput, rule: Rule) -> Normalized:
    """Dispatch on the rule's type."""
    if type(rule) is TextRule:
        return normalize_text(raw, rule)
    if type(rule) is DecimalRule:
        return normalize_decimal(raw, rule)
    if type(rule) is ChoiceRule:
        return normalize_choice(raw, rule)
    raise TypeError("rule must be TextRule, DecimalRule or ChoiceRule")


def canonical_decimal_text(value: Decimal) -> str:
    """Fixed-point text of a finite in-bounds Decimal, never in exponent form.

    The result has at most ``MAX_INTEGER_DIGITS`` integer digits and
    ``MAX_FRACTION_DIGITS`` fraction digits, plus an optional sign and point.
    """
    if type(value) is not Decimal:
        raise TypeError("canonical decimal text requires Decimal")
    canonical = _decimal.canonical_of(value)
    if canonical is None:
        raise ValueError("value is non-finite or outside canonical bounds")
    return _decimal.text(canonical)
