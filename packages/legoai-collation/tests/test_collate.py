"""Single-field precedence collation contract."""

import dataclasses
import decimal
import itertools
from decimal import Decimal

import pytest

from legoai_collation import (
    ASCII_WHITESPACE,
    MAX_READINGS,
    Admission,
    ChoiceRule,
    ChoiceVocabulary,
    Collation,
    CollationStatus,
    ComparisonContext,
    DecimalRule,
    DuplicateReadingError,
    IncompatibleRulesError,
    LimitExceededError,
    MixedContextError,
    PrecedencePolicy,
    RawInput,
    Reading,
    ReasonCode,
    SourceId,
    SourceRef,
    TextMode,
    TextRule,
    collate_field,
)

CONTEXT = ComparisonContext("item-7", "length", (("unit", "mm"),))
RULE = DecimalRule()
POLICY = PrecedencePolicy(
    "test/1",
    ((SourceId("north"), 0), (SourceId("east"), 1), (SourceId("west"), 1)),
)
TRIM = TextRule(TextMode.TRIM, ASCII_WHITESPACE)
FLAGS = ChoiceVocabulary("flag/1", frozenset({"on", "off"}))

type Rule = TextRule | DecimalRule | ChoiceRule


def reading(
    source: str,
    raw: str | int | Decimal | bool | RawInput,
    rule: Rule = RULE,
    locator: str | None = None,
    context: ComparisonContext = CONTEXT,
) -> Reading:
    value = raw if isinstance(raw, RawInput) else RawInput.of(raw)
    return Reading(SourceRef(SourceId(source), locator), context, value, rule)


def collate(*readings: Reading, policy: PrecedencePolicy = POLICY) -> Collation:
    return collate_field(CONTEXT, readings, policy)


def reason_map(collation: Collation) -> dict[ReasonCode, list[str]]:
    return {
        reason.code: [
            ref.source.value + (f"#{ref.locator}" if ref.locator else "")
            for ref in reason.refs
        ]
        for reason in collation.reasons
    }


def test_agreement_uses_numeric_equality_across_representations() -> None:
    result = collate(reading("north", "4.20"), reading("east", Decimal("4.2")))
    assert result.status is CollationStatus.AGREED
    assert result.selected == Decimal("4.2")
    assert result.has_disagreement is False
    assert result.distinct_values == (Decimal("4.2"),)
    assert reason_map(result) == {ReasonCode.AGREEMENT: ["north", "east"]}
    # Original representations are kept on the readings.
    assert [c.reading.raw for c in result.candidates] == [
        RawInput.of("4.20"),
        RawInput.of(Decimal("4.2")),
    ]


def test_precedence_selection_keeps_disagreeing_alternatives() -> None:
    result = collate(reading("east", "6"), reading("west", "5"), reading("north", "5"))
    assert result.status is CollationStatus.PRECEDENCE_SELECTED
    assert result.selected == Decimal("5")
    assert result.has_disagreement is True
    assert result.distinct_values == (Decimal("5"), Decimal("6"))
    assert reason_map(result) == {
        ReasonCode.PRECEDENCE_OVER_DISAGREEMENT: ["north"],
        ReasonCode.DISAGREEING_ALTERNATIVE: ["east"],
    }
    assert all(c.admission is Admission.ADMISSIBLE for c in result.candidates)


def test_equal_rank_disagreement_is_a_conflict_without_selection() -> None:
    result = collate(reading("east", "1"), reading("west", "2"), reading("north", "x"))
    assert result.status is CollationStatus.CONFLICT
    assert result.selected is None
    assert result.has_disagreement is True
    assert result.distinct_values == (Decimal("1"), Decimal("2"))
    assert reason_map(result) == {
        ReasonCode.EQUAL_RANK_DISAGREEMENT: ["east", "west"],
        ReasonCode.INVALID_OBSERVATION: ["north"],
    }


def test_invalid_without_admissible_readings() -> None:
    result = collate(reading("north", "x"), reading("east", RawInput.null()))
    assert result.status is CollationStatus.INVALID
    assert (result.selected, result.has_disagreement) == (None, False)
    assert reason_map(result) == {
        ReasonCode.INVALID_OBSERVATION: ["north"],
        ReasonCode.NOT_PRESENT: ["east"],
    }


def test_missing_distinguishes_absent_null_and_blank() -> None:
    result = collate(
        reading("north", RawInput.absent()),
        reading("east", RawInput.null()),
        reading("west", ""),
    )
    assert result.status is CollationStatus.MISSING
    assert [c.reading.state.value for c in result.candidates] == [
        "absent",
        "null",
        "blank",
    ]
    assert reason_map(result) == {ReasonCode.NOT_PRESENT: ["north", "east", "west"]}


def test_empty_input_is_missing() -> None:
    result = collate()
    assert result.status is CollationStatus.MISSING
    assert result.candidates == ()
    assert reason_map(result) == {ReasonCode.NO_OBSERVATIONS: []}
    assert result.policy_version == "test/1"
    assert result.rule == "legoai.collation.precedence/1"


def test_unranked_readings_are_retained_but_never_decide() -> None:
    result = collate(
        reading("north", "5"), reading("guest", "9"), reading("other", "x")
    )
    assert result.status is CollationStatus.AGREED
    assert result.has_disagreement is False
    unranked = [c for c in result.candidates if c.rank is None]
    assert [c.reading.ref.source.value for c in unranked] == ["guest", "other"]
    assert {c.admission for c in unranked} == {Admission.UNRANKED_SOURCE}
    assert reason_map(result)[ReasonCode.UNRANKED_SOURCE_EXCLUDED] == ["guest", "other"]
    only_unranked = collate(reading("guest", "x"))
    assert only_unranked.status is CollationStatus.MISSING


def test_source_specific_decimal_rules_are_preserved() -> None:
    strict = DecimalRule(max_fraction_digits=1)
    loose = DecimalRule(allow_negative_sign=True)
    result = collate(reading("north", "2.5", strict), reading("east", "2.50", loose))
    assert result.status is CollationStatus.AGREED
    assert [c.reading.rule for c in result.candidates] == [strict, loose]


def test_source_specific_choice_aliases_share_one_vocabulary() -> None:
    words = ChoiceRule(FLAGS, TRIM, ((RawInput.of("enabled"), "on"),))
    booleans = ChoiceRule(
        FLAGS, TRIM, ((RawInput.of(True), "on"), (RawInput.of(False), "off"))
    )
    result = collate(
        reading("north", " enabled ", words), reading("east", True, booleans)
    )
    assert result.status is CollationStatus.AGREED
    assert result.selected == "on"
    assert [c.reading.rule for c in result.candidates] == [words, booleans]


def test_different_vocabularies_are_incompatible() -> None:
    other = ChoiceVocabulary("switch/1", frozenset({"on", "off"}))
    first = ChoiceRule(FLAGS, TRIM, ((RawInput.of("on"), "on"),))
    second = ChoiceRule(other, TRIM, ((RawInput.of("on"), "on"),))
    with pytest.raises(IncompatibleRulesError):
        collate(reading("north", "on", first), reading("east", "on", second))


@pytest.mark.parametrize(
    "rule",
    [TRIM, ChoiceRule(FLAGS, TRIM, ((RawInput.of("5"), "on"),))],
)
def test_different_value_kinds_are_incompatible(rule: Rule) -> None:
    with pytest.raises(IncompatibleRulesError):
        collate(reading("north", "5"), reading("east", "5", rule))


def test_text_equality_is_exact() -> None:
    result = collate(reading("north", "Ab", TRIM), reading("east", "ab ", TRIM))
    assert result.status is CollationStatus.PRECEDENCE_SELECTED
    assert result.distinct_values == ("Ab", "ab")


@pytest.mark.parametrize(
    "other",
    [
        ComparisonContext("item-7", "length", (("unit", "cm"),)),
        ComparisonContext("item-7", "width", (("unit", "mm"),)),
        ComparisonContext("item-8", "length", (("unit", "mm"),)),
        ComparisonContext("item-7", "length"),
    ],
)
def test_mixed_contexts_are_rejected(other: ComparisonContext) -> None:
    with pytest.raises(MixedContextError, match="reading 1"):
        collate(reading("north", "1"), reading("east", "1", context=other))


def test_one_source_may_supply_several_located_readings() -> None:
    result = collate(
        reading("north", "3", locator="row-2"),
        reading("north", "3", locator="row-1"),
        reading("east", "4", locator="row-1"),
    )
    assert result.status is CollationStatus.PRECEDENCE_SELECTED
    assert reason_map(result)[ReasonCode.PRECEDENCE_OVER_DISAGREEMENT] == [
        "north#row-1",
        "north#row-2",
    ]


@pytest.mark.parametrize(
    "readings",
    [
        (reading("north", "3"), reading("north", "3")),
        (reading("north", "3"), reading("north", "4", locator="row-1")),
        (reading("north", "3", locator="a"), reading("north", "3", locator="a")),
    ],
)
def test_duplicate_identities_are_rejected_not_merged(
    readings: tuple[Reading, ...],
) -> None:
    with pytest.raises(DuplicateReadingError):
        collate(*readings)


def test_content_digest_is_not_part_of_identity() -> None:
    first = Reading(
        SourceRef(SourceId("north"), "a", "d1"), CONTEXT, RawInput.of("1"), RULE
    )
    second = Reading(
        SourceRef(SourceId("north"), "a", "d2"), CONTEXT, RawInput.of("1"), RULE
    )
    with pytest.raises(DuplicateReadingError):
        collate(first, second)


def test_candidate_order_is_rank_then_source_then_locator_with_unranked_last() -> None:
    result = collate(
        reading("zeta", "1"),
        reading("west", "1"),
        reading("north", "1", locator="b"),
        reading("alpha", "1"),
        reading("east", "1"),
        reading("north", "1", locator="a"),
    )
    order = [
        (c.rank, c.reading.ref.source.value, c.reading.ref.locator)
        for c in result.candidates
    ]
    assert order == [
        (0, "north", "a"),
        (0, "north", "b"),
        (1, "east", None),
        (1, "west", None),
        (None, "alpha", None),
        (None, "zeta", None),
    ]


PERMUTATION_SETS = [
    (
        reading("east", "6"),
        reading("west", "5"),
        reading("north", "5"),
        reading("guest", "1"),
    ),
    (
        reading("east", "1"),
        reading("west", "2"),
        reading("north", ""),
        reading("x", "1"),
    ),
    (
        reading("north", "4.20", locator="r2"),
        reading("north", Decimal("4.2"), locator="r1"),
        reading("east", "4.6"),
        reading("west", RawInput.null()),
        reading("guest", "bad"),
    ),
]


@pytest.mark.parametrize("readings", PERMUTATION_SETS)
def test_result_is_identical_for_every_input_order(
    readings: tuple[Reading, ...],
) -> None:
    expected = collate(*readings)
    for permutation in itertools.permutations(readings):
        assert collate(*permutation) == expected


def test_result_does_not_depend_on_the_ambient_decimal_context() -> None:
    readings = PERMUTATION_SETS[2]
    expected = collate(*readings)
    strict = decimal.Context(
        prec=1, rounding=decimal.ROUND_CEILING, traps=[decimal.Inexact, decimal.Rounded]
    )
    with decimal.localcontext(strict):
        assert collate(*readings) == expected


def test_inputs_are_validated_before_work() -> None:
    with pytest.raises(TypeError):
        collate_field(CONTEXT, [reading("north", "1")], POLICY)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        collate_field(CONTEXT, ("1",), POLICY)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        collate_field(CONTEXT, (), {})  # type: ignore[arg-type]
    too_many = tuple(reading(f"s{i}", "1") for i in range(MAX_READINGS + 1))
    with pytest.raises(LimitExceededError):
        collate_field(CONTEXT, too_many, POLICY)
    collate_field(CONTEXT, too_many[:MAX_READINGS], POLICY)


def test_results_are_immutable_tuples() -> None:
    result = collate(reading("north", "5"), reading("east", "6"))
    assert type(result.candidates) is tuple
    assert type(result.distinct_values) is tuple
    assert all(type(reason.refs) is tuple for reason in result.reasons)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = CollationStatus.CONFLICT  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.candidates[0].reading.value = Decimal("1")  # type: ignore[misc]


def test_reading_values_are_computed_not_supplied() -> None:
    with pytest.raises(TypeError):
        Reading(
            SourceRef(SourceId("n")),
            CONTEXT,
            RawInput.of("1"),
            RULE,
            value=Decimal("9"),
        )  # type: ignore[call-arg]


def test_collation_rejects_contradictory_disagreement_flags() -> None:
    with pytest.raises(ValueError):
        Collation(CONTEXT, "p", CollationStatus.AGREED, "a", True, ("a", "b"), (), ())
    with pytest.raises(ValueError):
        Collation(
            CONTEXT,
            "p",
            CollationStatus.PRECEDENCE_SELECTED,
            "a",
            False,
            ("a",),
            (),
            (),
        )
    with pytest.raises(ValueError):
        Collation(CONTEXT, "p", CollationStatus.CONFLICT, "a", True, ("a", "b"), (), ())
    with pytest.raises(ValueError):
        Collation(CONTEXT, "p", CollationStatus.MISSING, None, True, ("a",), (), ())
