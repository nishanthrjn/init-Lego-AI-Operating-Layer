"""Exact decimal normalization: lexical vs numeric rules, bounds and context."""

import decimal
from decimal import Decimal

import pytest

from legoai_collation import (
    MAX_FRACTION_DIGITS,
    MAX_INTEGER_DIGITS,
    DecimalRule,
    ObservationState,
    RawInput,
    canonical_decimal_text,
    normalize_decimal,
)

SIGNED = DecimalRule(allow_negative_sign=True)


def text_of(raw: RawInput, rule: DecimalRule = SIGNED) -> str:
    result = normalize_decimal(raw, rule)
    assert result.state is ObservationState.PRESENT
    assert isinstance(result.value, Decimal)
    return canonical_decimal_text(result.value)


def state_of(raw: RawInput, rule: DecimalRule = SIGNED) -> ObservationState:
    return normalize_decimal(raw, rule).state


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (RawInput.of("4.20"), "4.2"),
        (RawInput.of(Decimal("4.2")), "4.2"),
        (RawInput.of("007"), "7"),
        (RawInput.of("0.000"), "0"),
        (RawInput.of("-0.0"), "0"),
        (RawInput.of(Decimal("-0")), "0"),
        (RawInput.of(Decimal("1E+3")), "1000"),
        (RawInput.of(Decimal("1.50E-2")), "0.015"),
        (RawInput.of(Decimal("1E-7")), "0.0000001"),
        (RawInput.of(120), "120"),
        (RawInput.of(-3), "-3"),
        (RawInput.of("-12.340"), "-12.34"),
    ],
)
def test_canonical_form_is_exact_and_fixed_point(raw: RawInput, expected: str) -> None:
    assert text_of(raw) == expected


def test_canonical_value_has_one_representation() -> None:
    values = [
        normalize_decimal(RawInput.of(raw), SIGNED).value
        for raw in ("4.2", "4.20", "04.200")
    ] + [normalize_decimal(RawInput.of(Decimal("42E-1")), SIGNED).value]
    tuples = {value.as_tuple() for value in values if isinstance(value, Decimal)}
    assert len(tuples) == 1


@pytest.mark.parametrize(
    "text",
    [
        "+1",
        "1e3",
        "1E3",
        " 1",
        "1 ",
        "1,000",
        "1.",
        ".5",
        "--1",
        "0x1",
        "\u0661",
        "NaN",
    ],
)
def test_lexically_invalid_text(text: str) -> None:
    assert state_of(RawInput.of(text)) is ObservationState.INVALID


def test_lexical_rules_apply_only_to_text() -> None:
    whole = DecimalRule(allow_fraction=False)
    assert state_of(RawInput.of("2.0"), whole) is ObservationState.INVALID
    assert text_of(RawInput.of(Decimal("2.0")), whole) == "2"
    unsigned = DecimalRule()
    assert state_of(RawInput.of("-5"), unsigned) is ObservationState.INVALID
    assert text_of(RawInput.of(-5), unsigned) == "-5"
    short = DecimalRule(max_fraction_digits=2)
    assert state_of(RawInput.of("1.234"), short) is ObservationState.INVALID
    assert text_of(RawInput.of("1.20"), short) == "1.2"
    assert text_of(RawInput.of(Decimal("1.234")), short) == "1.234"


def test_numeric_rules_apply_to_every_kind() -> None:
    integral = DecimalRule(integral=True)
    assert text_of(RawInput.of("2.0"), integral) == "2"
    assert state_of(RawInput.of("2.5"), integral) is ObservationState.INVALID
    assert state_of(RawInput.of(Decimal("2.5")), integral) is ObservationState.INVALID
    nonnegative = DecimalRule(allow_negative_sign=True, minimum=Decimal("0"))
    assert state_of(RawInput.of(-5), nonnegative) is ObservationState.INVALID
    assert text_of(RawInput.of("-0"), nonnegative) == "0"


def test_bounds_are_inclusive_and_exact() -> None:
    rule = DecimalRule(minimum=Decimal("0.1"), maximum=Decimal("0.3"))
    assert text_of(RawInput.of("0.1"), rule) == "0.1"
    assert text_of(RawInput.of("0.30"), rule) == "0.3"
    just_below = "0.0" + "9" * (MAX_FRACTION_DIGITS - 2)
    assert state_of(RawInput.of(just_below), rule) is ObservationState.INVALID
    just_above = "0.3" + "0" * (MAX_FRACTION_DIGITS - 2) + "1"
    assert state_of(RawInput.of(just_above), rule) is ObservationState.INVALID


@pytest.mark.parametrize(
    "raw",
    [
        RawInput.of(Decimal("NaN")),
        RawInput.of(Decimal("sNaN")),
        RawInput.of(Decimal("Infinity")),
        RawInput.of(Decimal("-Infinity")),
        RawInput.of(True),
    ],
)
def test_non_finite_and_boolean_are_invalid(raw: RawInput) -> None:
    assert state_of(raw) is ObservationState.INVALID


@pytest.mark.parametrize(
    "value",
    [
        Decimal("1E+999999999"),
        Decimal("1E-999999999"),
        Decimal("-9E+99999999999"),
        Decimal("5E-99999999999"),
        Decimal("1E+65"),
        Decimal("1E-65"),
    ],
)
def test_extreme_exponents_are_rejected_without_expansion(value: Decimal) -> None:
    assert state_of(RawInput.of(value)) is ObservationState.INVALID
    with pytest.raises(ValueError):
        canonical_decimal_text(value)


def test_trailing_zeros_are_stripped_before_bounds() -> None:
    # A 4001-digit coefficient that is exactly 1.
    value = Decimal((0, (1,) + (0,) * 4000, -4000))
    assert text_of(RawInput.of(value)) == "1"


def test_excessive_coefficients_are_invalid() -> None:
    assert (
        state_of(RawInput.of("1" * (MAX_INTEGER_DIGITS + 1)))
        is ObservationState.INVALID
    )
    fraction = "0." + "1" * (MAX_FRACTION_DIGITS + 1)
    assert state_of(RawInput.of(fraction)) is ObservationState.INVALID
    assert state_of(RawInput.of(10**MAX_INTEGER_DIGITS)) is ObservationState.INVALID
    coefficient = Decimal((0, (7,) * 4096, 0))
    assert state_of(RawInput.of(coefficient)) is ObservationState.INVALID


def test_largest_canonical_value_and_output_length() -> None:
    text = "-" + "9" * MAX_INTEGER_DIGITS + "." + "9" * MAX_FRACTION_DIGITS
    rendered = text_of(RawInput.of(text))
    assert rendered == text
    assert len(rendered) == MAX_INTEGER_DIGITS + MAX_FRACTION_DIGITS + 2


CONTEXT_INPUTS = [
    # Below CONTEXT_RULE's minimum: the one expected INVALID result.
    RawInput.of("-" + "9" * MAX_INTEGER_DIGITS + "." + "9" * MAX_FRACTION_DIGITS),
    RawInput.of("123456789.987654321"),
    RawInput.of(Decimal("1.50E-2")),
    RawInput.of(Decimal((0, (1,) + (0,) * 4000, -4000))),
    RawInput.of(10**MAX_INTEGER_DIGITS - 1),
    RawInput.of("0.30000000000000000000000000000000000001"),
]
CONTEXT_RULE = DecimalRule(
    allow_negative_sign=True,
    minimum=Decimal("-" + "9" * MAX_INTEGER_DIGITS),
    maximum=Decimal("9" * MAX_INTEGER_DIGITS),
)


@pytest.mark.parametrize(
    "context",
    [
        decimal.Context(prec=1, rounding=decimal.ROUND_FLOOR),
        decimal.Context(
            prec=3,
            rounding=decimal.ROUND_UP,
            Emax=5,
            Emin=-5,
            traps=[decimal.Inexact, decimal.Rounded, decimal.InvalidOperation],
        ),
    ],
)
def test_results_do_not_depend_on_the_ambient_context(context: decimal.Context) -> None:
    expected = [normalize_decimal(raw, CONTEXT_RULE) for raw in CONTEXT_INPUTS]
    texts = [
        canonical_decimal_text(r.value)
        for r in expected
        if isinstance(r.value, Decimal)
    ]
    with decimal.localcontext(context):
        actual = [normalize_decimal(raw, CONTEXT_RULE) for raw in CONTEXT_INPUTS]
        actual_texts = [
            canonical_decimal_text(r.value)
            for r in actual
            if isinstance(r.value, Decimal)
        ]
        assert DecimalRule(minimum=Decimal("0.125")).minimum == Decimal("0.125")
    assert [(r.state, r.value) for r in actual] == [
        (r.state, r.value) for r in expected
    ]
    assert actual_texts == texts
    assert [r.state for r in expected].count(ObservationState.PRESENT) == len(
        expected
    ) - 1
