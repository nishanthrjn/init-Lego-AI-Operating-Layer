"""Value contracts: exact types, immutable ownership, limits and equality."""

import dataclasses
from decimal import Decimal

import pytest

from legoai_collation import (
    ASCII_WHITESPACE,
    MAX_ALIASES,
    MAX_IDENTIFIER_LENGTH,
    MAX_POLICY_SOURCES,
    MAX_QUALIFIERS,
    MAX_RAW_DECIMAL_DIGITS,
    MAX_RAW_INTEGER_DIGITS,
    MAX_TEXT_LENGTH,
    ChoiceRule,
    ChoiceVocabulary,
    ComparisonContext,
    DecimalRule,
    LimitExceededError,
    Normalized,
    ObservationState,
    PrecedencePolicy,
    RawInput,
    RawKind,
    SourceId,
    SourceRef,
    TextMode,
    TextRule,
    ValueKind,
)

TRIM = TextRule(TextMode.TRIM, ASCII_WHITESPACE)
YES_NO = ChoiceVocabulary("yes-no/1", frozenset({"yes", "no"}))


class TextSubclass(str):
    pass


class DecimalSubclass(Decimal):
    pass


def test_raw_input_kinds_are_exact() -> None:
    assert RawInput.of(True).kind is RawKind.BOOLEAN
    assert RawInput.of(1).kind is RawKind.INTEGER
    assert RawInput.of("1").kind is RawKind.TEXT
    assert RawInput.of(Decimal("1")).kind is RawKind.DECIMAL
    assert RawInput.absent().kind is RawKind.ABSENT
    assert RawInput.null().kind is RawKind.NULL
    assert RawInput.absent() != RawInput.null()


@pytest.mark.parametrize(
    "value", [1.5, TextSubclass("x"), DecimalSubclass("1"), None, b"1", [1]]
)
def test_raw_input_rejects_other_types(value: object) -> None:
    with pytest.raises(TypeError):
        RawInput.of(value)  # type: ignore[arg-type]


def test_float_rejection_explains_the_exact_alternative() -> None:
    with pytest.raises(TypeError, match="text or Decimal"):
        RawInput.of(4.2)  # type: ignore[arg-type]


def test_raw_kind_and_value_must_agree() -> None:
    with pytest.raises(ValueError):
        RawInput(RawKind.NULL, "x")
    with pytest.raises(TypeError):
        RawInput(RawKind.INTEGER, True)
    with pytest.raises(TypeError):
        RawInput(RawKind.TEXT, 1)


def test_raw_equality_is_representation_exact_and_type_aware() -> None:
    assert RawInput.of(Decimal("4.2")) != RawInput.of(Decimal("4.20"))
    assert RawInput.of(Decimal("-0")) != RawInput.of(Decimal("0"))
    assert RawInput.of(True) != RawInput.of(1)
    assert RawInput.of("1") != RawInput.of(1)
    nan = RawInput.of(Decimal("NaN"))
    assert nan == RawInput.of(Decimal("NaN"))
    assert hash(nan) == hash(RawInput.of(Decimal("NaN")))
    assert len({RawInput.of(1), RawInput.of(True), RawInput.of("1")}) == 3


def test_raw_limits_are_enforced_at_construction() -> None:
    RawInput.of("x" * MAX_TEXT_LENGTH)
    with pytest.raises(LimitExceededError):
        RawInput.of("x" * (MAX_TEXT_LENGTH + 1))
    largest = 10**MAX_RAW_INTEGER_DIGITS - 1
    assert RawInput.of(largest).value == largest
    assert RawInput.of(-largest).value == -largest
    with pytest.raises(LimitExceededError):
        RawInput.of(largest + 1)
    RawInput.of(Decimal((0, (1,) * MAX_RAW_DECIMAL_DIGITS, 0)))
    with pytest.raises(LimitExceededError):
        RawInput.of(Decimal((0, (1,) * (MAX_RAW_DECIMAL_DIGITS + 1), 0)))


def test_raw_value_is_hidden_from_repr() -> None:
    assert "sensitive" not in repr(RawInput.of("sensitive"))


def test_identifiers_are_bounded_exact_text() -> None:
    SourceId("s" * MAX_IDENTIFIER_LENGTH)
    for bad in ("", "s" * (MAX_IDENTIFIER_LENGTH + 1)):
        with pytest.raises(ValueError):
            SourceId(bad)
    with pytest.raises(TypeError):
        SourceId(TextSubclass("s"))
    assert SourceId("Feed") != SourceId("feed")


def test_source_ref_digest_is_opaque_metadata() -> None:
    ref = SourceRef(SourceId("s"), "row-1", "any caller supplied text")
    assert ref.content_digest == "any caller supplied text"
    with pytest.raises(TypeError):
        SourceRef("s")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        SourceRef(SourceId("s"), "")


def test_context_qualifiers_are_sorted_unique_tuples() -> None:
    context = ComparisonContext("subject", "field", (("b", "2"), ("a", "1")))
    assert context.qualifiers == (("a", "1"), ("b", "2"))
    assert context == ComparisonContext("subject", "field", (("a", "1"), ("b", "2")))
    with pytest.raises(ValueError):
        ComparisonContext("subject", "field", (("a", "1"), ("a", "2")))
    with pytest.raises(TypeError):
        ComparisonContext("subject", "field", [("a", "1")])  # type: ignore[arg-type]
    too_many = tuple((f"k{i}", "v") for i in range(MAX_QUALIFIERS + 1))
    with pytest.raises(LimitExceededError):
        ComparisonContext("subject", "field", too_many)


def test_values_are_frozen() -> None:
    frozen: list[object] = [
        RawInput.of("x"),
        SourceId("s"),
        SourceRef(SourceId("s")),
        ComparisonContext("subject", "field"),
        TRIM,
        DecimalRule(),
        YES_NO,
        PrecedencePolicy("p/1", ()),
    ]
    for value in frozen:
        field = dataclasses.fields(value)[0].name  # type: ignore[arg-type]
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(value, field, None)


def test_text_rule_validation() -> None:
    with pytest.raises(TypeError):
        TextRule(TextMode.TRIM, {" "})  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        TextRule(TextMode.TRIM, frozenset({"  "}))
    TextRule(TextMode.COLLAPSE, frozenset())


def test_decimal_rule_validation_and_canonical_bounds() -> None:
    rule = DecimalRule(minimum=Decimal("0.50"), maximum=Decimal("1E+1"))
    assert (
        rule.minimum is not None
        and rule.minimum.as_tuple() == Decimal("0.5").as_tuple()
    )
    assert (
        rule.maximum is not None and rule.maximum.as_tuple() == Decimal("10").as_tuple()
    )
    with pytest.raises(ValueError):
        DecimalRule(minimum=Decimal("2"), maximum=Decimal("1"))
    with pytest.raises(ValueError):
        DecimalRule(allow_fraction=False, max_fraction_digits=1)
    with pytest.raises(ValueError):
        DecimalRule(minimum=Decimal("Infinity"))
    with pytest.raises(ValueError):
        DecimalRule(maximum=Decimal("1E+100"))
    with pytest.raises(TypeError):
        DecimalRule(integral=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        DecimalRule(max_fraction_digits=True)


def test_choice_rule_normalizes_text_keys_and_validates_tokens() -> None:
    rule = ChoiceRule(
        YES_NO, TRIM, ((RawInput.of("  Y "), "yes"), (RawInput.of(False), "no"))
    )
    assert rule.token_for(RawInput.of("Y")) == "yes"
    assert rule.token_for(RawInput.of(False)) == "no"
    assert rule.token_for(RawInput.of(0)) is None
    with pytest.raises(ValueError):
        ChoiceRule(YES_NO, TRIM, ((RawInput.of("Y"), "maybe"),))
    with pytest.raises(ValueError):
        ChoiceRule(YES_NO, TRIM, ((RawInput.of("Y"), "yes"), (RawInput.of(" Y"), "no")))
    with pytest.raises(ValueError):
        ChoiceRule(YES_NO, TRIM, ((RawInput.of("   "), "yes"),))
    with pytest.raises(ValueError):
        ChoiceRule(YES_NO, TRIM, ((RawInput.of(Decimal("1")), "yes"),))
    with pytest.raises(ValueError):
        ChoiceRule(YES_NO, TRIM, ((RawInput.null(), "yes"),))
    too_many = tuple((RawInput.of(i), "yes") for i in range(MAX_ALIASES + 1))
    with pytest.raises(LimitExceededError):
        ChoiceRule(YES_NO, TRIM, too_many)


def test_choice_rule_alias_order_is_canonical() -> None:
    forward = ChoiceRule(
        YES_NO, TRIM, ((RawInput.of("b"), "no"), (RawInput.of("a"), "yes"))
    )
    backward = ChoiceRule(
        YES_NO, TRIM, ((RawInput.of("a"), "yes"), (RawInput.of("b"), "no"))
    )
    assert forward == backward


def test_normalized_invariants() -> None:
    with pytest.raises(ValueError):
        Normalized(ObservationState.PRESENT, ValueKind.TEXT)
    with pytest.raises(ValueError):
        Normalized(ObservationState.BLANK, ValueKind.TEXT, "x")
    with pytest.raises(ValueError):
        Normalized(ObservationState.PRESENT, ValueKind.DECIMAL, Decimal("4.20"))
    Normalized(ObservationState.PRESENT, ValueKind.DECIMAL, Decimal("4.2"))


def test_precedence_policy_validation() -> None:
    policy = PrecedencePolicy("p/1", ((SourceId("b"), 1), (SourceId("a"), 0)))
    assert [source.value for source, _ in policy.ranks] == ["a", "b"]
    assert policy.rank_of(SourceId("b")) == 1
    assert policy.rank_of(SourceId("c")) is None
    with pytest.raises(ValueError):
        PrecedencePolicy("p/1", ((SourceId("a"), 0), (SourceId("a"), 1)))
    with pytest.raises(ValueError):
        PrecedencePolicy("p/1", ((SourceId("a"), -1),))
    with pytest.raises(TypeError):
        PrecedencePolicy("p/1", ((SourceId("a"), True),))
    with pytest.raises(TypeError):
        PrecedencePolicy("p/1", {SourceId("a"): 0})  # type: ignore[arg-type]
    too_many = tuple((SourceId(f"s{i}"), 0) for i in range(MAX_POLICY_SOURCES + 1))
    with pytest.raises(LimitExceededError):
        PrecedencePolicy("p/1", too_many)
